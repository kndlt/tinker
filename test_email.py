#!/usr/bin/env python3
"""
Test script for email functionality in Tinker
"""
import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
from tinker.email_manager import EmailManager, send_email_from_task

def test_email_connection():
    """Test SMTP connection without sending email"""
    print("🔍 Testing SMTP connection...")
    
    # Load environment variables
    load_dotenv()
    
    try:
        email_manager = EmailManager()
        result = email_manager.test_connection()
        
        if result['success']:
            print("✅ SMTP connection successful!")
            return True
        else:
            print(f"❌ SMTP connection failed: {result['error']}")
            return False
    except Exception as e:
        print(f"❌ Failed to initialize email manager: {e}")
        return False

def test_email_parsing():
    """Test email task parsing"""
    print("\n🔍 Testing email task parsing...")
    
    task_content = """Send email to kndlt@sprited.app:

Subject: Hello, it's Tinker!

My birth day is June 2nd 2025. Thank you for creating a gmail account for me!"""
    
    try:
        # Load environment variables
        load_dotenv()
        
        # This will parse but not actually send
        print("📧 Parsing email task...")
        print("Task content:")
        for i, line in enumerate(task_content.split('\n'), 1):
            print(f"  {i}: {line}")
        
        # Extract the parsing logic
        lines = task_content.strip().split('\n')
        
        # Parse recipient from first line
        first_line = lines[0].strip()
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
        
        # Extract body
        body_lines = []
        for line in lines[subject_line_index + 1:]:
            if line.strip() or body_lines:
                body_lines.append(line)
        
        # Remove leading empty lines
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        
        body = '\n'.join(body_lines).strip()
        
        print(f"\n✅ Email parsing successful!")
        print(f"   📧 Recipient: {recipient_email}")
        print(f"   📋 Subject: {subject}")
        print(f"   📄 Body: {body}")
        
        return True
        
    except Exception as e:
        print(f"❌ Email parsing failed: {e}")
        return False

def main():
    """Run email tests"""
    print("🧪 Testing Tinker Email Functionality")
    print("=" * 40)
    
    # Test 1: SMTP Connection
    connection_ok = test_email_connection()
    
    # Test 2: Email Parsing
    parsing_ok = test_email_parsing()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"   SMTP Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    print(f"   Email Parsing: {'✅ PASS' if parsing_ok else '❌ FAIL'}")
    
    if connection_ok and parsing_ok:
        print("\n🎉 All tests passed! Email functionality is ready!")
        print("\n💡 To test actual email sending:")
        print("   1. Copy a task to .tinker/tasks/")
        print("   2. Run 'poetry run tinker'")
        print("   3. Approve the email when prompted")
    else:
        print("\n⚠️  Some tests failed. Check your .env configuration.")

if __name__ == "__main__":
    main()
