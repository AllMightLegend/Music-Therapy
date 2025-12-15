"""
Email service for sending invitation codes to parents/guardians.
Supports Gmail SMTP with app-specific passwords.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import streamlit as st


def get_email_config() -> dict:
    """
    Get email configuration from environment variables or Streamlit secrets.
    
    Required configuration:
    - SMTP_HOST: SMTP server host (e.g., smtp.gmail.com)
    - SMTP_PORT: SMTP server port (e.g., 587 for TLS)
    - SMTP_USER: Email address to send from
    - SMTP_PASSWORD: Email password or app-specific password
    - SENDER_NAME: Display name for sender (optional)
    """
    # Try Streamlit secrets first (for deployment), then environment variables
    config = {}
    
    if hasattr(st, 'secrets') and 'email' in st.secrets:
        secrets = st.secrets['email']
        config = {
            'host': secrets.get('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(secrets.get('SMTP_PORT', 587)),
            'user': secrets.get('SMTP_USER', ''),
            'password': secrets.get('SMTP_PASSWORD', ''),
            'sender_name': secrets.get('SENDER_NAME', 'Music Therapy Team')
        }
    else:
        config = {
            'host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', 587)),
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'sender_name': os.getenv('SENDER_NAME', 'Music Therapy Team')
        }
    
    return config


def is_email_configured() -> bool:
    """Check if email service is properly configured."""
    config = get_email_config()
    return bool(config['user'] and config['password'])


def create_invitation_email(
    parent_email: str,
    child_name: str,
    invitation_code: str,
    therapist_name: str = "Your Therapist"
) -> tuple[str, str]:
    """
    Create HTML and plain text versions of the invitation email.
    
    Returns:
        tuple: (html_content, plain_text_content)
    """
    # Plain text version
    plain_text = f"""
Hello,

{therapist_name} has invited you to collaborate on {child_name}'s music therapy journey!

Music Therapy Recommender is a professional platform where therapists and parents work together 
to support children's emotional growth through personalized music recommendations.

Your Invitation Code: {invitation_code}

Webapp Link: https://music-therapy-aiml-tmsl.streamlit.app/

To get started:
1. Visit https://music-therapy-aiml-tmsl.streamlit.app/
2. Go to the "Parent Invitation" tab
3. Enter your invitation code: {invitation_code}
4. Create your account and password

Once you're signed in, you'll be able to:
✓ View {child_name}'s therapy progress
✓ See playlist recommendations from therapy sessions
✓ Track emotional growth over time
✓ Collaborate with {therapist_name} on the care plan

We're excited to have you join this therapeutic journey!

Best regards,
Music Therapy Team

---
This is an automated message. Please do not reply to this email.
If you have questions, please contact {therapist_name} directly.
"""

    # HTML version
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            background: #ffffff;
            padding: 30px;
            border: 1px solid #e0e0e0;
            border-top: none;
        }}
        .invitation-code {{
            background: #f8f9fa;
            border: 2px dashed #667eea;
            padding: 20px;
            margin: 25px 0;
            text-align: center;
            border-radius: 8px;
        }}
        .code {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            letter-spacing: 2px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
        }}
        .steps {{
            background: #f8f9fa;
            padding: 20px;
            border-left: 4px solid #667eea;
            margin: 20px 0;
        }}
        .steps h3 {{
            margin-top: 0;
            color: #667eea;
        }}
        .steps ol {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .steps li {{
            margin: 8px 0;
        }}
        .benefits {{
            margin: 20px 0;
        }}
        .benefit-item {{
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }}
        .benefit-item:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #4caf50;
            font-weight: bold;
            font-size: 18px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-radius: 0 0 8px 8px;
            border: 1px solid #e0e0e0;
            border-top: none;
        }}
        .button {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 5px;
            margin: 15px 0;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎵 Music Therapy Invitation</h1>
    </div>
    
    <div class="content">
        <p>Hello,</p>
        
        <p><strong>{therapist_name}</strong> has invited you to collaborate on <strong>{child_name}'s</strong> music therapy journey!</p>
        
        <p>Music Therapy Recommender is a professional platform where therapists and parents work together to support children's emotional growth through personalized music recommendations.</p>
        
        <div class="invitation-code">
            <p style="margin: 0; color: #666; font-size: 14px;">Your Invitation Code</p>
            <div class="code">{invitation_code}</div>
            <p style="margin: 5px 0 0 0; color: #666; font-size: 12px;">Keep this code secure</p>
        </div>
        
        <div class="steps">
            <h3>🚀 Getting Started</h3>
            <ol>
                <li>Visit the <strong>Music Therapy Recommender</strong> app at:<br>
                    <a href="https://music-therapy-aiml-tmsl.streamlit.app/" class="button" style="color: white; text-decoration: none; display: inline-block; margin-top: 10px;">Open Music Therapy App</a></li>
                <li>Go to the <strong>"Parent Invitation"</strong> tab</li>
                <li>Enter your invitation code: <strong>{invitation_code}</strong></li>
                <li>Create your account and password</li>
            </ol>
        </div>
        
        <div class="benefits">
            <h3 style="color: #667eea;">What You'll Be Able To Do:</h3>
            <div class="benefit-item">View {child_name}'s therapy progress</div>
            <div class="benefit-item">See playlist recommendations from therapy sessions</div>
            <div class="benefit-item">Track emotional growth over time</div>
            <div class="benefit-item">Collaborate with {therapist_name} on the care plan</div>
        </div>
        
        <p style="margin-top: 30px;">We're excited to have you join this therapeutic journey!</p>
        
        <p>Best regards,<br>
        <strong>Music Therapy Team</strong></p>
    </div>
    
    <div class="footer">
        <p>This is an automated message. Please do not reply to this email.</p>
        <p>If you have questions, please contact {therapist_name} directly.</p>
    </div>
</body>
</html>
"""
    
    return html, plain_text


def send_invitation_email(
    parent_email: str,
    child_name: str,
    invitation_code: str,
    therapist_name: str = "Your Therapist"
) -> tuple[bool, str]:
    """
    Send invitation email to parent/guardian.
    
    Args:
        parent_email: Recipient email address
        child_name: Name of the child
        invitation_code: Unique invitation code
        therapist_name: Name of the therapist sending the invitation
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Check if email is configured
    if not is_email_configured():
        return False, "Email service not configured. Please set up SMTP credentials."
    
    config = get_email_config()
    
    try:
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎵 Music Therapy Invitation for {child_name}"
        msg['From'] = f"{config['sender_name']} <{config['user']}>"
        msg['To'] = parent_email
        
        # Create both plain text and HTML versions
        html_content, plain_content = create_invitation_email(
            parent_email, child_name, invitation_code, therapist_name
        )
        
        # Attach both versions
        part1 = MIMEText(plain_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(config['host'], config['port']) as server:
            server.starttls()
            server.login(config['user'], config['password'])
            server.send_message(msg)
        
        return True, f"Invitation email sent successfully to {parent_email}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "Email authentication failed. Check your SMTP credentials."
    except smtplib.SMTPException as e:
        return False, f"Failed to send email: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def send_test_email(recipient_email: str) -> tuple[bool, str]:
    """
    Send a test email to verify configuration.
    
    Args:
        recipient_email: Email address to send test to
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not is_email_configured():
        return False, "Email service not configured"
    
    config = get_email_config()
    
    try:
        msg = MIMEText("This is a test email from Music Therapy Recommender. Your email configuration is working correctly!")
        msg['Subject'] = "Test Email - Music Therapy Recommender"
        msg['From'] = f"{config['sender_name']} <{config['user']}>"
        msg['To'] = recipient_email
        
        with smtplib.SMTP(config['host'], config['port']) as server:
            server.starttls()
            server.login(config['user'], config['password'])
            server.send_message(msg)
        
        return True, f"Test email sent successfully to {recipient_email}"
        
    except Exception as e:
        return False, f"Failed to send test email: {str(e)}"
