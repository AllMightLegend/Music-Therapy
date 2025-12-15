"""
Test script to verify email configuration.
Run this script to check if your SMTP settings are correct.
"""

import sys
from email_service import is_email_configured, send_test_email, get_email_config


def main():
    print("=" * 70)
    print("EMAIL CONFIGURATION TEST")
    print("=" * 70)
    
    # Check if email is configured
    print("\n1. Checking configuration...")
    if not is_email_configured():
        print("   ❌ Email service is NOT configured")
        print("\n   To configure email:")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your SMTP credentials")
        print("   3. See EMAIL_SETUP.md for detailed instructions")
        sys.exit(1)
    
    print("   ✅ Email configuration found")
    
    # Show config (without password)
    config = get_email_config()
    print("\n2. Configuration details:")
    print(f"   SMTP Host: {config['host']}")
    print(f"   SMTP Port: {config['port']}")
    print(f"   SMTP User: {config['user']}")
    print(f"   Sender Name: {config['sender_name']}")
    print(f"   Password: {'*' * 16} (hidden)")
    
    # Ask for test email
    print("\n3. Send test email")
    test_email = input("   Enter email address to send test email to: ").strip()
    
    if not test_email:
        print("   ❌ No email address provided")
        sys.exit(1)
    
    print(f"\n   Sending test email to {test_email}...")
    
    success, message = send_test_email(test_email)
    
    if success:
        print(f"   ✅ {message}")
        print("\n" + "=" * 70)
        print("EMAIL CONFIGURATION TEST PASSED!")
        print("=" * 70)
        print("\nYou can now use automatic invitation emails in the app.")
    else:
        print(f"   ❌ {message}")
        print("\n" + "=" * 70)
        print("EMAIL CONFIGURATION TEST FAILED")
        print("=" * 70)
        print("\nPlease check:")
        print("1. Your SMTP credentials are correct")
        print("2. For Gmail, you're using an app password (not regular password)")
        print("3. Your firewall isn't blocking SMTP ports")
        print("4. See EMAIL_SETUP.md for troubleshooting")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
