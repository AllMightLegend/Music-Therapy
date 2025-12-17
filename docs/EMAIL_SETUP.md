# Email Configuration Guide

## Setting Up Email Service for Invitation Codes

The Music Therapy Recommender can automatically send invitation codes to parents via email when therapists create child profiles.

### Configuration Methods

You can configure email settings in two ways:

#### Option 1: Environment Variables (Local Development)

Create a `.env` file in the project root with:

```env
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_NAME=Music Therapy Team
```

#### Option 2: Streamlit Secrets (Deployment)

For Streamlit Cloud deployment, add to `.streamlit/secrets.toml`:

```toml
[email]
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
SENDER_NAME = "Music Therapy Team"
```

### Gmail Setup (Recommended)

1. **Use a Gmail Account**
   - Use a dedicated Gmail account for sending emails (not your personal account)
   - Example: `musictherapy.noreply@gmail.com`

2. **Enable 2-Step Verification**
   - Go to Google Account → Security
   - Enable 2-Step Verification

3. **Generate App Password**
   - Go to Google Account → Security → 2-Step Verification → App Passwords
   - Select "Mail" and "Other (Custom name)"
   - Enter "Music Therapy App"
   - Copy the 16-character password
   - Use this as `SMTP_PASSWORD` (remove spaces)

4. **Configure Settings**
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=abcd efgh ijkl mnop  # 16-character app password (remove spaces)
   SENDER_NAME=Music Therapy Team
   ```

### Other Email Providers

#### Outlook/Office 365
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail
```env
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

#### Custom SMTP Server
```env
SMTP_HOST=smtp.yourserver.com
SMTP_PORT=587  # or 465 for SSL
SMTP_USER=your-email@yourserver.com
SMTP_PASSWORD=your-password
```

### Testing Email Configuration

After configuration, test the email service:

1. Start the app: `streamlit run app.py`
2. Create a therapist account
3. Create a child profile with your own email as parent email
4. Check if you receive the invitation email

### Security Best Practices

1. **Never commit credentials to Git**
   - Add `.env` to `.gitignore`
   - Keep `.streamlit/secrets.toml` out of version control

2. **Use App-Specific Passwords**
   - Don't use your main account password
   - Use app-specific passwords where available

3. **Dedicated Email Account**
   - Create a separate email account just for the app
   - Don't use personal or production email accounts

4. **Rotate Credentials**
   - Change passwords periodically
   - Revoke old app passwords when no longer needed

### Fallback Behavior

If email is not configured:
- The app will still work normally
- Invitation codes will be displayed on screen
- Therapists can manually share codes with parents
- A tip will suggest configuring email for automation

### Email Template Features

The invitation email includes:
- ✅ Professional HTML design with branding
- ✅ Clear invitation code display
- ✅ Step-by-step instructions
- ✅ Benefits of the platform
- ✅ Child's name personalization
- ✅ Therapist name attribution
- ✅ Plain text fallback for older email clients

### Troubleshooting

**"Email authentication failed"**
- Check username and password are correct
- For Gmail, ensure you're using an app password, not your regular password
- Verify 2-step verification is enabled

**"Connection refused"**
- Check SMTP_HOST and SMTP_PORT are correct
- Verify firewall isn't blocking port 587 or 465
- Try using a different network

**"Email not received"**
- Check spam/junk folder
- Verify recipient email address is correct
- Check email provider's sending limits
- Gmail free accounts: 500 emails/day
- Office 365: varies by plan

**"SSL/TLS errors"**
- Port 587 uses STARTTLS (recommended)
- Port 465 uses SSL (alternative)
- Try switching ports if one doesn't work

### Example .env File

```env
# Core App Settings
HUME_API_KEY=your_hume_api_key_here

# Email Settings (Optional - enables automatic invitation emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=musictherapy.noreply@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SENDER_NAME=Music Therapy Team
```

### Support

For issues with email configuration:
1. Check the logs for detailed error messages
2. Test with the test email function first
3. Verify credentials with your email provider
4. Check email provider's SMTP documentation
