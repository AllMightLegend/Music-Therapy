# Quick Start: Email Automation

## What's New?

Parents now receive **automatic invitation emails** when therapists create child profiles! 📧

## 5-Minute Setup

### 1. Create Gmail App Password
```
1. Go to: https://myaccount.google.com/security
2. Enable "2-Step Verification"
3. Click "App passwords"
4. Select "Mail" → "Other" → Name it "Music Therapy"
5. Copy the 16-character password
```

### 2. Configure App
```bash
# Copy example file
cp .env.example .env

# Edit .env and add:
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

### 3. Test It
```bash
python test_email_config.py
# Enter your email to receive test message
```

### 4. Use It!
- Create child profile with parent email
- Email sends automatically! ✨

## Without Setup

No email configured? No problem!
- Invitation code still displays on screen
- Share manually with parents
- Everything works as before

## Files Added

- `email_service.py` - Email functionality
- `EMAIL_SETUP.md` - Detailed guide
- `EMAIL_AUTOMATION.md` - Full documentation  
- `test_email_config.py` - Testing tool
- `.env.example` - Configuration template

## How It Works

```
Therapist creates profile
         ↓
Enters parent email
         ↓
     If email configured:
     ├─ Sends beautiful HTML email
     └─ Shows "✅ Email sent"
     
     If NOT configured:
     ├─ Shows code on screen
     └─ Shows tip about email setup
```

## Email Preview

**Subject**: 🎵 Music Therapy Invitation for [Child Name]

**Content**:
- Welcome message from therapist
- Invitation code (large, clear display)
- Step-by-step instructions
- Benefits of the platform
- Professional design

## Support

- 📖 See **EMAIL_SETUP.md** for detailed setup
- 📖 See **EMAIL_AUTOMATION.md** for full documentation
- 🧪 Run `python test_email_config.py` to test
- ❓ Check troubleshooting sections in docs

---

**That's it!** 🎉 Email automation is ready to use.
