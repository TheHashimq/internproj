import threading
import os
import paramiko
import pandas as pd
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, send_file
from datetime import datetime
from time import sleep

app = Flask(__name__)
app.config['STATIC_FOLDER'] = './static'

# Email settings
EMAIL_SENDER = 'hashimq905@gmail.com'  
EMAIL_PASSWORD = ''  
EMAIL_RECIPIENT = 'hashimq905@gmail.com'  
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def send_email_alert(subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        server.quit()
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

ensure_directory_exists('./static/ssh_status.csv')
ensure_directory_exists('./static/traceroute.csv')
ensure_directory_exists('./static/ping_status.csv')

def cleanup_csv_if_needed(file_path, max_lines=10000):
    try:
        if not os.path.exists(file_path):
            return
        df = pd.read_csv(file_path)
        if len(df) > max_lines:
            df = df.iloc[len(df) // 2:]
            df.to_csv(file_path, index=False)
            print(f"Cleaned up the first half of {file_path}, kept the latest data.")
    except Exception as e:
        print(f"Error during CSV cleanup: {e}")

# SSH Check
def check_ssh(host, port, username, password=None):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
        client.close()
        return "Success"
    except Exception:
        return "Failed"

def periodic_ssh_check():
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        server_info = {
            "host": "pwnable.kr",
            "port": 2222,
            "username": "col",
            "password": "guest"
        }
        status = check_ssh(server_info["host"], server_info["port"], server_info["username"], server_info["password"])
        ensure_directory_exists('./static/ssh_status.csv')
        data = pd.DataFrame([{"timestamp": timestamp, "host": server_info["host"], "status": status}])
        data.to_csv('./static/ssh_status.csv', mode='a', header=False, index=False)
        cleanup_csv_if_needed('./static/ssh_status.csv')
        if status == "Failed":
            send_email_alert("SSH Check Failed", f"SSH check failed for {server_info['host']} at {timestamp}.")
        sleep(300)

# Traceroute
def perform_traceroute(host):
    try:
        result = subprocess.check_output(['traceroute', host])
        result_str = result.decode('utf-8')
        lines = result_str.splitlines()
        hops = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                hop_number = parts[0]
                host_ip = parts[1]
                rtt1 = parts[2].replace("ms", "") if len(parts) > 2 else 'N/A'
                rtt2 = parts[3].replace("ms", "") if len(parts) > 3 else 'N/A'
                rtt3 = parts[4].replace("ms", "") if len(parts) > 4 else 'N/A'
                hops.append({
                    "hop_number": hop_number,
                    "host_ip": host_ip,
                    "rtt1": rtt1,
                    "rtt2": rtt2,
                    "rtt3": rtt3
                })
        if hops:
            return "Success", hops
        return "Failed", "N/A"
    except Exception:
        return "Failed", "N/A"

def periodic_traceroute():
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        host = "8.8.8.8"
        status, hops = perform_traceroute(host)
        ensure_directory_exists('./static/traceroute.csv')
        if status == "Success":
            for hop in hops:
                data = pd.DataFrame([{
                    "timestamp": timestamp,
                    "host": host,
                    "status": status,
                    "hop_number": hop["hop_number"],
                    "host_ip": hop["host_ip"],
                    "rtt1": hop["rtt1"],
                    "rtt2": hop["rtt2"],
                    "rtt3": hop["rtt3"]
                }])
                data.to_csv('./static/traceroute.csv', mode='a', header=False, index=False)
        else:
            send_email_alert("Traceroute Check Failed", f"Traceroute failed for {host} at {timestamp}.")
            data = pd.DataFrame([{
                "timestamp": timestamp,
                "host": host,
                "status": status,
                "hop_number": 'N/A',
                "host_ip": 'N/A',
                "rtt1": 'N/A',
                "rtt2": 'N/A',
                "rtt3": 'N/A'
            }])
            data.to_csv('./static/traceroute.csv', mode='a', header=False, index=False)

        cleanup_csv_if_needed('./static/traceroute.csv')
        sleep(300)

# Ping
def perform_ping(host):
    try:
        result = subprocess.check_output(['ping', '-c', '1', host])
        result_str = result.decode('utf-8')
        lines = result_str.splitlines()
        for line in lines:
            if "time=" in line:
                time_part = line.split('time=')[-1]
                rtt = time_part.split()[0]
                return "Success", rtt
        return "Failed", "N/A"
    except Exception:
        return "Failed", "N/A"

def periodic_ping():
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        host = "8.8.8.8"
        status, rtt = perform_ping(host)
        ensure_directory_exists('./static/ping_status.csv')
        if status == "Failed":
            send_email_alert("Ping Check Failed", f"Ping check failed for {host} at {timestamp}.")
        data = pd.DataFrame([{
            "timestamp": timestamp,
            "host": host,
            "status": status,
            "rtt": rtt
        }])
        data.to_csv('./static/ping_status.csv', mode='a', header=False, index=False)
        cleanup_csv_if_needed('./static/ping_status.csv')
        sleep(300)

# Start threads
thread_ssh = threading.Thread(target=periodic_ssh_check, daemon=True)
thread_traceroute = threading.Thread(target=periodic_traceroute, daemon=True)
thread_ping = threading.Thread(target=periodic_ping, daemon=True)
thread_ssh.start()
thread_traceroute.start()
thread_ping.start()

@app.route('/')
def index():
    return 'Service is running'

@app.route('/download_ssh_csv')
def download_ssh_csv():
    return send_file('./static/ssh_status.csv', as_attachment=True)

@app.route('/download_traceroute_csv')
def download_traceroute_csv():
    return send_file('./static/traceroute.csv', as_attachment=True)

@app.route('/download_ping_csv')
def download_ping_csv():
    return send_file('./static/ping_status.csv', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

