import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# you could set these emails to one address so you would be emailing yourself
# or you could setup a personal systems email so you have a diff email for each device

def send_email(subject, body):
    sender_email = "example@gmail.com"
    receiver_email = "recieve@gmail.com"
    password = "email_pass"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls() # network prot
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email sent.")
    except Exception as e:
        print(f"Failed to send: {e}")

