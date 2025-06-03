import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email_validator import validate_email, EmailNotValidError
from pathlib import Path
import logging
from typing import Optional, List, Dict, Any

class EmailManager:
    """Handles email sending functionality using SMTP."""
    
    def __init__(self):
        """Initialize EmailManager with SMTP configuration from environment."""
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'Tinker AI Agent')
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate SMTP configuration."""
        required_vars = ['SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def validate_email_address(self, email: str) -> bool:
        """Validate an email address format."""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    def create_message(self, 
                      to_email: str, 
                      subject: str, 
                      body: str, 
                      body_type: str = 'plain',
                      attachments: Optional[List[str]] = None) -> MIMEMultipart:
        """Create an email message."""
        
        # Validate recipient email
        if not self.validate_email_address(to_email):
            raise ValueError(f"Invalid recipient email address: {to_email}")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body, body_type))
        
        # Add attachments if any
        if attachments:
            for file_path in attachments:
                if Path(file_path).exists():
                    self._attach_file(msg, file_path)
                else:
                    logging.warning(f"Attachment file not found: {file_path}")
        
        return msg
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> None:
        """Attach a file to the email message."""
        with open(file_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {Path(file_path).name}',
        )
        
        msg.attach(part)
    
    def send_email(self, 
                   to_email: str, 
                   subject: str, 
                   body: str, 
                   body_type: str = 'plain',
                   attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            body_type: 'plain' or 'html'
            attachments: List of file paths to attach
            
        Returns:
            Dict with success status and any error messages
        """
        try:
            # Create message
            message = self.create_message(to_email, subject, body, body_type, attachments)
            
            # Create SMTP connection with SSL/TLS
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()  # Can be omitted
                server.starttls(context=context)  # Enable security
                server.ehlo()  # Can be omitted
                server.login(self.smtp_username, self.smtp_password)
                
                # Send email
                text = message.as_string()
                server.sendmail(self.from_email, to_email, text)
            
            return {
                'success': True,
                'message': f'Email sent successfully to {to_email}',
                'to': to_email,
                'subject': subject
            }
            
        except Exception as e:
            error_msg = f"Failed to send email to {to_email}: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'to': to_email,
                'subject': subject
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SMTP connection without sending an email."""
        try:
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
            
            return {
                'success': True,
                'message': 'SMTP connection successful'
            }
            
        except Exception as e:
            error_msg = f"SMTP connection failed: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

def send_email_from_task(task_content: str) -> Dict[str, Any]:
    """
    Parse task content and send email. Helper function for main.py integration.
    
    Expected task format:
    Send email to recipient@example.com:
    
    Subject: Email Subject
    
    Email body content here...
    """
    try:
        lines = task_content.strip().split('\n')
        
        # Parse recipient from first line
        first_line = lines[0].strip()
        if not first_line.lower().startswith('send email to'):
            raise ValueError("Task must start with 'Send email to recipient@example.com:'")
        
        # Extract recipient email
        recipient_part = first_line[len('send email to'):].strip()
        if recipient_part.endswith(':'):
            recipient_part = recipient_part[:-1]
        
        recipient_email = recipient_part.strip()
        
        # Find subject line
        subject = ""
        subject_line_index = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip().lower().startswith('subject:'):
                subject = line[len('subject:'):].strip()
                subject_line_index = i
                break
        
        if not subject:
            raise ValueError("No subject found. Task must include 'Subject: Your Subject Here'")
        
        # Extract body (everything after subject and empty line)
        body_lines = []
        for line in lines[subject_line_index + 1:]:
            if line.strip() or body_lines:  # Include content after we start finding non-empty lines
                body_lines.append(line)
        
        # Remove leading empty lines
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        
        body = '\n'.join(body_lines).strip()
        
        if not body:
            raise ValueError("No email body content found")
        
        # Send email
        email_manager = EmailManager()
        result = email_manager.send_email(recipient_email, subject, body)
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to parse or send email: {str(e)}"
        }
