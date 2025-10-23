#!/usr/bin/env python3
"""
Standalone email tester for NQ Tenpin
Run this separately to test email without touching app.py
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration - CHANGE THESE
EMAIL_ADDRESS = 'atherton@nqtenpin.com.au'
APP_PASSWORD = 'nmmgfdglmwvjrsdy'
TEST_RECIPIENT = 'atherton@nqtenpin.com.au'

def test_basic_email():
    """Test 1: Most basic email possible"""
    print("Testing basic email...")
    try:
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        
        msg = MIMEText("This is a test email from NQ Tenpin system.")
        msg['Subject'] = 'Test Email'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = TEST_RECIPIENT
        
        server.send_message(msg)
        server.quit()
        
        print("✓ Basic email sent successfully!")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_html_email():
    """Test 2: HTML formatted email like the app will send"""
    print("\nTesting HTML email...")
    try:
        html = """
        <html>
        <body>
            <h2 style='color: #e91e8c;'>NQ Tenpin Test Email</h2>
            <p>This is a test of the HTML email system.</p>
            <p><strong>If you can see this, HTML emails are working!</strong></p>
            <ul>
                <li>Locker reminders will work</li>
                <li>Balance notifications will work</li>
                <li>League announcements will work</li>
            </ul>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'HTML Test - NQ Tenpin'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = TEST_RECIPIENT
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✓ HTML email sent successfully!")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_locker_reminder():
    """Test 3: Sample locker reminder email"""
    print("\nTesting locker reminder email...")
    try:
        html = """
        <html>
        <body style='font-family: Arial, sans-serif;'>
            <div style='background: #2d2d2d; color: white; padding: 20px;'>
                <h1 style='color: #e91e8c;'>NQ Tenpin Atherton</h1>
            </div>
            <div style='padding: 20px;'>
                <h2>Locker Rental Expiring Soon</h2>
                <p>Dear John Smith,</p>
                <p>Your rental for <strong>Locker #42</strong> is expiring on <strong>November 20, 2025</strong>.</p>
                <p>Please visit us to renew your locker rental before it expires.</p>
                <p>Thank you,<br>NQ Tenpin Atherton</p>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Locker #42 Expiring in 7 Days'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = TEST_RECIPIENT
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✓ Locker reminder email sent successfully!")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

if __name__ == '__main__':
    print("="*50)
    print("NQ TENPIN EMAIL TESTER")
    print("="*50)
    
    if APP_PASSWORD == '':
        print("\n⚠ ERROR: You need to set your APP_PASSWORD first!")
        print("Edit this file and put your Microsoft 365 app password in line 13")
    else:
        print(f"\nTesting email from: {EMAIL_ADDRESS}")
        print(f"Sending test emails to: {TEST_RECIPIENT}\n")
        
        # Run all tests
        test_basic_email()
        test_html_email()
        test_locker_reminder()
        
        print("\n" + "="*50)
        print("Testing complete. Check your inbox!")
