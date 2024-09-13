import ctypes
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

# admin check, we do need admin to run the script
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False



# you could set these emails to one address so you would be emailing yourself
# or you could setup a personal systems email so you have a diff email for each device

def send_email(subject, body):
    sender_email = "test@gmail.com"
    receiver_email = "test@gmail.com"
    password = "testpass"

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

def run_chkdsk():
    print("running chkdsk...")
    output = os.popen("chkdsk C:").read()
    if "corrupt" in output.lower() or "errors" in output.lower():
        print("File coruption detected!")
        send_email("File Corruption Detected", output)
        fix_output = os.popen("chkdsk C: /F").read()
        if "corrected" in fix_output.lower() or "fixed" in fix_output.lower():
            print("corruption fixed.")
            send_email("File Corruption fixed", fix_output)
        else:
            send_email("Attempt to fix file corruption failed", fix_output)
    else:
        print("No corruption detected")

if __name__ == "__main__":
    if not is_admin():
        print("Script is not running as admin. Restarting with admin priv.")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)

    run_chkdsk()