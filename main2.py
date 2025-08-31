import os
import asyncio
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from rich.console import Console
from agents import Agent, handoff, Runner, ModelSettings, function_tool

# Load environment variables
load_dotenv()
console = Console()

# Email sending tool with proper decorator
@function_tool
def send_email_tool(recipient: str, subject: str, body: str) -> str:
    """Send an email using SMTP to the specified recipient.
    
    Args:
        recipient: Email address of the recipient  
        subject: Subject line of the email
        body: Main content/message of the email
        
    Returns:
        Success or error message
    """
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not sender:
        return "❌ EMAIL_ADDRESS not set in .env file"
    
    if not password:
        return "❌ EMAIL_PASSWORD not set in .env file. Please set your Gmail App Password!"
    
    # Validate email format
    if "@" not in recipient or "." not in recipient:
        return f"❌ Invalid email format: {recipient}"
    
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        
        # Try to send email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        
        return f"✅ Email sent successfully!\nTo: {recipient}\nSubject: {subject}"
        
    except smtplib.SMTPAuthenticationError:
        return "❌ Authentication failed! Please check your Gmail App Password in .env file"
    except smtplib.SMTPRecipientsRefused:
        return f"❌ Invalid recipient email: {recipient}"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"

# Core Chat Agent
chat_agent = Agent(
    name="Core Chat Agent",
    instructions=(
        "You are a friendly assistant. Keep answers short, clear, and helpful. "
        "Answer general questions and provide helpful information."
    ),
    model="gpt-4",
    model_settings=ModelSettings(temperature=0.2),
)

# Email Drafting Agent
email_draft_agent = Agent(
    name="Email Drafting Agent",
    instructions=(
        "You are an assistant that writes email drafts. "
        "When asked, generate a clear subject line and professional email body. "
        "Ask for recipient, purpose, and any specific details needed. "
        "Keep emails polite, professional, and concise."
    ),
    model="gpt-4",
    model_settings=ModelSettings(temperature=0.3),
)

# Email Sending Agent (without Tool wrapper)
email_send_agent = Agent(
    name="Email Sending Agent",
    instructions=(
        "You are responsible for sending emails. "
        "Ask user for recipient, subject, and body if not provided. "
        "Once you have all details, use the send_email_tool to send the email. "
        "Confirm with user before sending."
    ),
    tools=[send_email_tool],  # Direct function reference
    model="gpt-4",
    model_settings=ModelSettings(temperature=0.2),
)

# Main Triage Agent
triage_agent = Agent(
    name="Email Bot Triage",
    instructions=(
        "You are the main email bot assistant. Direct conversations appropriately:\n\n"
        "- For general chat and questions → respond normally\n"
        "- If user wants to write/draft an email → handoff to Email Draft Agent\n"
        "- If user says 'send' or wants to actually send an email → IMMEDIATELY handoff to Email Send Agent\n"
        "- Keywords for sending: 'send', 'email to', 'send this', 'send it', 'actually send'\n\n"
        "When user says 'send this to [email]' or similar - handoff to Email Send Agent right away!\n"
        "Be friendly and helpful!"
    ),
    handoffs=[
        handoff(agent=email_draft_agent),
        handoff(agent=email_send_agent),
    ],
    model="gpt-4",
    model_settings=ModelSettings(temperature=0.1),
)

# CLI Interface
async def run_cli():
    """Run the command line interface"""
    console.print("[bold green]🤖 Email Bot - CLI Mode[/bold green]")
    console.print("[dim]Type 'exit' or 'quit' to stop[/dim]\n")
    
    # Simple in-memory conversation history for CLI
    conversation_history = []
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in {"exit", "quit", "bye"}:
                console.print("[yellow]👋 Goodbye![/yellow]")
                break
                
            if not user_input:
                continue
            
            # Build context from conversation history
            if conversation_history:
                context_lines = ["Previous conversation:"]
                for msg in conversation_history[-6:]:  # Last 6 messages
                    context_lines.append(f"{msg['role'].title()}: {msg['content']}")
                context_lines.append("---")
                context = "\n".join(context_lines)
                contextual_input = f"{context}\n\nCurrent message: {user_input}"
            else:
                contextual_input = user_input
            
            # Add user message to history
            conversation_history.append({"role": "user", "content": user_input})
                
            # Run the triage agent
            result = await Runner.run(triage_agent, contextual_input)
            bot_reply = result.final_output
            
            # Add bot response to history
            conversation_history.append({"role": "assistant", "content": bot_reply})
            
            console.print(f"[bold cyan]🤖 Bot:[/bold cyan] {bot_reply}")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")

# Main function
async def main():
    """Main entry point"""
    # Check environment variables
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]❌ OPENAI_API_KEY not found in .env file[/red]")
        return
    
    if not os.getenv("EMAIL_ADDRESS"):
        console.print("[yellow]⚠️  EMAIL_ADDRESS not set - email sending will not work[/yellow]")
    
    # Run CLI
    await run_cli()

if __name__ == "__main__":
    asyncio.run(main())