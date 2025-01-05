import os
import paramiko
import pandas as pd
import subprocess
import threading
from flask import Flask, send_file
from datetime import datetime
from time import sleep

app = Flask(__name__)

# SSH Check function
# SSH Check function (with simplified status)

def cleanup_csv_if_needed(file_path, max_lines=10000):
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check if the file has more than 'max_lines' lines
        if len(df) > max_lines:
            # Remove the first half of the data (keeping the second half)
            df = df.iloc[len(df) // 2:]
            df.to_csv(file_path, index=False)  # Write back the cleaned-up data
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

# Background Task to check SSH and update CSV
def periodic_ssh_check():
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # SSH check with the provided login details
        server_info = {
            "host": "pwnable.kr",  # Target SSH server
            "port": 2222,          # SSH port 2222
            "username": "col",     # SSH username
            "password": "guest"    # SSH password
        }

        # Perform SSH login check
        status = check_ssh(server_info["host"], server_info["port"], server_info["username"], server_info["password"])

        # Append result to SSH CSV file (important columns: timestamp, host, status)
        data = pd.DataFrame([{"timestamp": timestamp, "host": server_info["host"], "status": status}])
        data.to_csv('ssh_status.csv', mode='a', header=False, index=False)
        cleanup_csv_if_needed('ssh_status.csv')
        sleep(60)  # Wait for 60 seconds before the next check

def perform_traceroute(host):
    try:
        result = subprocess.check_output(['traceroute', host])
        result_str = result.decode('utf-8')

        # Split the result into lines and parse each hop
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
                # Store hop number, host/IP and RTTs
                hops.append({
                    "hop_number": hop_number,
                    "host_ip": host_ip,
                    "rtt1": rtt1,
                    "rtt2": rtt2,
                    "rtt3": rtt3
                })
        # If we were able to capture any hops
        if hops:
            return "Success", hops

        return "Failed", "N/A"  # If no hops were found

    except Exception:
        return "Failed", "N/A"
# Background Task to perform traceroute and update CSV
def periodic_traceroute():
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        host = "8.8.8.8"  # Replace with the target for traceroute
        status, hops = perform_traceroute(host)

        # If traceroute was successful, write hops to CSV
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
                data.to_csv('traceroute_status.csv', mode='a', header=False, index=False)
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
            data.to_csv('traceroute_status.csv', mode='a', header=False, index=False)
        cleanup_csv_if_needed('ssh_status.csv')
        sleep(60) 

@app.route('/')
def index():
    return "Web App is running! Check /download_ssh_csv or /download_traceroute_csv for CSV files."

@app.route('/download_ssh_csv')
def download_ssh_csv():
    try:
        return send_file('ssh_status.csv', as_attachment=True)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/download_traceroute_csv')
def download_traceroute_csv():
    try:
        return send_file('traceroute_status.csv', as_attachment=True)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    # Start background threads for SSH and Traceroute checks
    ssh_thread = threading.Thread(target=periodic_ssh_check)
    traceroute_thread = threading.Thread(target=periodic_traceroute)
    ssh_thread.daemon = True  # Allow threads to be killed when app exits
    traceroute_thread.daemon = True  # Allow threads to be killed when app exits
    ssh_thread.start()
    traceroute_thread.start()
    app.run(debug=True)

