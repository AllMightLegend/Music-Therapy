# Email Automation for Parent Invitations

## Overview

The Music Therapy Recommender now automatically sends professional invitation emails to parents when therapists create child profiles and provide a parent email address.

## Features

### ✅ Automated Email Delivery
- **Instant Notifications**: Parents receive invitation codes immediately via email
- **Professional Templates**: Beautiful HTML emails with clear branding
- **Fallback Support**: Manual code display if email service is unavailable

### ✅ Email Content Includes
- 🎵 Welcoming header with Music Therapy branding
- 📧 Unique invitation code prominently displayed
- 📋 Step-by-step instructions for account activation
- ✓ Benefits of the platform
- 👤 Personalized with child's name and therapist's name
- 📱 Mobile-responsive design

### ✅ Security & Privacy
- Secure SMTP with TLS encryption
- App-specific password support
- No credentials stored in code
- Professional sender identity

## User Experience Flow

### For Therapists

1. **Create Child Profile**
   - Fill in child's name, date of birth, target mood
   - Enter parent's email address (optional)
   - Click "Create Child Profile"

2. **Automatic Email Sending**
   - If email is configured: Email sent automatically ✅
   - If email not configured: Code displayed for manual sharing 📋

3. **Confirmation**
   - Success message shows email was sent
   - Parent can now check their inbox

### For Parents

1. **Receive Email**
   - Professional invitation email arrives in inbox
   - Subject: "🎵 Music Therapy Invitation for [Child Name]"
   - Clear invitation code displayed

2. **Follow Instructions**
   - Open the app
   - Go to "Parent Invitation" tab
   - Enter the code from email
   - Create account and password

3. **Access Granted**
   - View child's therapy progress
   - See playlist recommendations
   - Collaborate with therapist

## Email Template Preview

```
┌────────────────────────────────────────┐
│  🎵 Music Therapy Invitation           │
├────────────────────────────────────────┤
│                                        │
│  Hello,                                │
│                                        │
│  [Therapist Name] has invited you to  │
│  collaborate on [Child Name]'s music  │
│  therapy journey!                      │
│                                        │
│  ╔══════════════════════════════════╗ │
│  ║  Your Invitation Code            ║ │
│  ║  ABC123DEF456                    ║ │
│  ║  Keep this code secure           ║ │
│  ╚══════════════════════════════════╝ │
│                                        │
│  🚀 Getting Started                    │
│  1. Visit Music Therapy Recommender   │
│  2. Go to "Parent Invitation" tab     │
│  3. Enter code: ABC123DEF456          │
│  4. Create account and password       │
│                                        │
│  What You'll Be Able To Do:           │
│  ✓ View therapy progress              │
│  ✓ See playlist recommendations       │
│  ✓ Track emotional growth             │
│  ✓ Collaborate on care plan           │
│                                        │
└────────────────────────────────────────┘
```

## Setup Instructions

### Quick Start (5 minutes)

1. **Get a Gmail Account**
   - Use a dedicated account: `musictherapy.noreply@gmail.com`

2. **Create App Password**
   - Google Account → Security → 2-Step Verification
   - App Passwords → Mail → "Music Therapy"
   - Copy 16-character password

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Test Configuration**
   ```bash
   python test_email_config.py
   ```

5. **Done!**
   - Emails now send automatically

See [EMAIL_SETUP.md](EMAIL_SETUP.md) for detailed instructions.

## Configuration

### Environment Variables

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_NAME=Music Therapy Team
```

### Streamlit Cloud Deployment

Add to `.streamlit/secrets.toml`:

```toml
[email]
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
SENDER_NAME = "Music Therapy Team"
```

## Testing

### Test Email Configuration

```bash
python test_email_config.py
```

This will:
1. Check if email is configured
2. Show configuration details (password hidden)
3. Send a test email to verify setup

### Manual Testing in App

1. Create therapist account
2. Create child profile with your email
3. Check inbox for invitation email
4. Verify email formatting and links

## Fallback Behavior

If email service is **not configured**:
- ✅ App works normally
- 📋 Invitation code displayed on screen
- 💡 Tip shown to configure email
- 👥 Therapist can manually share code

If email **sending fails**:
- ⚠️ Warning message displayed
- 📋 Invitation code shown as fallback
- 🔄 Therapist can retry or share manually

## Troubleshooting

### Email Not Received

**Check spam folder**
- Invitation emails may be filtered as spam initially

**Verify email address**
- Ensure parent email is correct
- Check for typos

**Check sending limits**
- Gmail: 500 emails/day for free accounts
- Office 365: varies by plan

### Authentication Failed

**Gmail users**
- Must use app password (not regular password)
- Enable 2-step verification first
- Generate new app password if expired

**Other providers**
- Check username/password are correct
- Verify SMTP settings match provider docs

### Connection Issues

**Firewall blocking**
- Port 587 (STARTTLS) or 465 (SSL) must be open
- Check corporate firewall settings

**Network restrictions**
- Some networks block SMTP ports
- Try different network or VPN

See [EMAIL_SETUP.md](EMAIL_SETUP.md) for more troubleshooting.

## Email Service Files

### Core Files
- `email_service.py` - Email sending logic and templates
- `EMAIL_SETUP.md` - Detailed setup guide
- `test_email_config.py` - Configuration testing tool
- `.env.example` - Template for environment variables

### Modified Files
- `app.py` - Integrated email sending on profile creation

## Benefits

### For Therapists
- ⏱️ **Time Saving**: No manual code sharing needed
- 📧 **Professional**: Branded, polished communication
- 🔄 **Automated**: Set up once, works forever
- 📊 **Tracking**: Know when invitations are sent

### For Parents
- 📬 **Convenient**: Receive code directly in email
- 📋 **Clear**: Step-by-step instructions included
- 🔐 **Secure**: Code delivered privately
- 📱 **Accessible**: Check email anytime, anywhere

### For the Organization
- 🏢 **Professional Image**: Polished communication
- 🤝 **Better Engagement**: Parents receive timely invitations
- 📈 **Improved Onboarding**: Clear process reduces confusion
- ✅ **Reliability**: Automated process reduces errors

## Security Considerations

### Credentials
- Never commit `.env` to version control
- Use app-specific passwords, not account passwords
- Rotate passwords periodically
- Use dedicated email account for the app

### Email Content
- Invitation codes are unique and single-use
- No sensitive health information in emails
- Professional sender identity
- Clear attribution to therapist

### Data Privacy
- Email addresses stored securely in database
- SMTP uses TLS encryption
- Compliant with email privacy best practices

## Future Enhancements

Potential improvements:
- 📊 Email delivery tracking
- 🔔 Reminder emails for pending invitations
- 📧 Session completion notifications
- 📈 Progress report emails
- 🔄 Email template customization
- 🌐 Multi-language email support

## Support

For issues or questions:
1. Check [EMAIL_SETUP.md](EMAIL_SETUP.md) for setup help
2. Run `python test_email_config.py` to test configuration
3. Review logs for detailed error messages
4. Check email provider's SMTP documentation

---

**Status**: ✅ Feature Complete & Production Ready

**Last Updated**: December 15, 2025
