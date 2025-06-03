# Tinker - Phase 2.3

In Phase 2.1, we made sure shell commands like grep, echo, curl, ping all works fine.

Now, I want to give it ability to send emails.

I've created a gmail account, and routed it to tinker (at) sprited (dot) app.

For SMTP, I've configured Brevo and the SMTP details are in the .env file.

## Tasks

### 1. Setup Dependencies
- [ ] Add email libraries to `pyproject.toml` 
- [ ] Install packages in Docker container

### 2. Create Email Module
- [ ] Create `src/tinker/email_manager.py`
- [ ] Implement SMTP connection with Brevo
- [ ] Add email sending functionality with error handling

### 3. Integrate with Main System
- [ ] Update `main.py` to detect email tasks
- [ ] Add email processing to task workflow

### 4. Test Implementation
- [ ] Test with sample task `task--1.2--send-mail.md`
- [ ] Verify emails send to kndlt@sprited.app

