import threading
import os
import paramiko
import pandas as pd
import subprocess
from flask import Flask, send_file
from datetime import datetime
from time import sleep

app = Flask(__name__)
app.config['STATIC_FOLDER'] = './static'

def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)

    if directory and not os.path.exists(directory):
        os.makedirs(directory) 

ensure_directory_exists('./static/ssh_status.csv')
ensure_directory_exists('./static/traceroute.csv')

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
            "host": "pwnable.kr",  # Target SSH server
            "port": 2222,          # SSH port 2222
            "username": "col",     # SSH username
            "password": "guest"    # SSH password
        }

        status = check_ssh(server_info["host"], server_info["port"], server_info["username"], server_info["password"])
        ensure_directory_exists('./static/ssh_status.csv')
        data = pd.DataFrame([{"timestamp": timestamp, "host": server_info["host"], "status": status}])
        data.to_csv('./static/ssh_status.csv', mode='a', header=False, index=False)
        cleanup_csv_if_needed('./static/ssh_status.csv')
        sleep(300)  

def perform_traceroute(host):
    try:
        result = subprocess.check_output(['traceroute', host])
        result_str = result.decode('utf-8')
        lines = result_str.splitlines()
        hops = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:  # Ensure valid data
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
        host = "8.8.8.8"  # Replace with the target for traceroute
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
            # Handle failure case
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

thread_ssh = threading.Thread(target=periodic_ssh_check, daemon=True)
thread_traceroute = threading.Thread(target=periodic_traceroute, daemon=True)
thread_ssh.start()
thread_traceroute.start()

@app.route('/')
def index():
    return 'Service is running'

@app.route('/download_ssh_csv')
def download_ssh_csv():
    return send_file('./static/ssh_status.csv', as_attachment=True)

@app.route('/download_traceroute_csv')
def download_traceroute_csv():
    return send_file('./static/traceroute.csv', as_attachment=True)

if __name__ == '__main__':
    ssh_thread = threading.Thread(target=periodic_ssh_check)
    traceroute_thread = threading.Thread(target=periodic_traceroute)
    ssh_thread.daemon = True  # Allow threads to be killed when app exits
    traceroute_thread.daemon = True  # Allow threads to be killed when app exits
    ssh_thread.start()
    traceroute_thread.start()
    app.run(host='0.0.0.0' , port=5000 ,debug=True)
