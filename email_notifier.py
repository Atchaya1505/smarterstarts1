import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SENDER_EMAIL = os.getenv("ALERT_EMAIL")
SENDER_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD")
RECEIVER_EMAIL = os.getenv("ALERT_RECEIVER")

def send_email_alert(session):
    """Send a styled HTML email when a new SmarterStarts consultation is created."""

    user = session.get("user", {})
    name = user.get("name", "N/A")
    email = user.get("email", "N/A")
    company_size = user.get("company_size", "N/A")
    problem = session.get("problem", "N/A")
    created_at = session.get("createdAt", "N/A")

    # Extract document ID if available
    doc_id = session.get("id", None)
    if doc_id:
        firebase_link = f"https://console.firebase.google.com/project/smarterstarts1/firestore/data/~2Fsmarterstarts_sessions~2F{doc_id}"
    else:
        firebase_link = "https://console.firebase.google.com/project/smarterstarts1/firestore/data/~2Fsmarterstarts_sessions"

    # Format selected tools as bullet list
    selected_tools = session.get("selected_tools", [])
    if isinstance(selected_tools, list) and selected_tools:
        tools_html = "".join([f"<li>{tool}</li>" for tool in selected_tools])
    elif isinstance(selected_tools, str):
        tools_html = f"<li>{selected_tools}</li>"
    else:
        tools_html = "<li>No tools selected</li>"

    subject = f"🚀 New SmarterStarts Consultation – {name}"

    # Build clean HTML body
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #2E86C1;">🌱 New SmarterStarts Consultation Alert 🚀</h2>

        <p><b>👤 Name:</b> {name}</p>
        <p><b>📧 Email:</b> <a href="mailto:{email}" style="color:#1a73e8;">{email}</a></p>
        <p><b>🏢 Company Size:</b> {company_size}</p>
        <p><b>💡 Problem:</b> {problem}</p>

        <p><b>🧰 Selected Tools:</b></p>
        <ul style="margin-top: 0;">{tools_html}</ul>

        <p><b>🗓️ Created At:</b> {created_at}</p>

        <br>
        <p>🔗 <a href="{firebase_link}" style="color:#0b8043; text-decoration:none;">View this session in Firebase →</a></p>
        <hr>
        <p style="font-size: 12px; color: #777;">
          SmarterStarts AI | Automated Consultation Notification
        </p>
      </body>
    </html>
    """

    # Create and send email
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print("📨 Admin alert sent successfully.")
    except Exception as e:
        print(f"⚠️ Failed to send admin alert: {e}")