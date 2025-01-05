from flask import Flask, send_file

app = Flask(__name__)

@app.route('/download')
def download_file():
    return send_file('ssh_check_results.csv', as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

