# BunkerBuster 🔍💥 <a name="top"></a>

**BunkerBuster** is a *simple, anonymous* tool for finding software vulnerabilities and sharing exploits securely. It runs on **any device**—Windows, Linux, macOS, phones—via a one-click GUI, CLI, web app, or Docker. With **Tor** for privacy and **IPFS** for decentralized sharing, it’s built for researchers.

> [!NOTE]  
> BunkerBuster is designed for **ethical research only**. Ensure you have permission before testing systems.

## Features <a name="features"></a>

- **One-Click Simplicity**: Just press `Start`—no tech skills needed! :+1:
- **Anonymous**: Hides your tracks with **Tor** and **IPFS**. :lock:
- **Cross-Platform**: Works on laptops, phones, servers. :computer::iphone:
- **Auto-Sharing**: Exploits sent to **IPFS** and **Twitter** automatically. :rocket:
- **Clear Logs**: Shows tasks like `Checking code for weaknesses`. :memo:

## Quick Start <a name="quick-start"></a>

> [!TIP]  
> Run the setup script once, then use any interface with a single command or click!

### 1. Setup <a name="setup"></a>

Complete these tasks to get started:

- [x] Install dependencies with one command:
  ```bash
  chmod +x install.sh && ./install.sh
  ```
- [ ] Run **IPFS** in a new terminal:
  ```bash
  ipfs daemon
  ```
- [ ] *Optional*: Set Twitter keys for sharing:
  ```bash
  export TWITTER_API_KEY="your_key"
  export TWITTER_API_SECRET="your_secret"
  export TWITTER_ACCESS_TOKEN="your_token"
  export TWITTER_ACCESS_TOKEN_SECRET="your_token_secret"
  ```

### 2. Run <a name="run"></a>

Choose an interface:

- **GUI**: `python bunkerbuster.py [--admin]`  
  Click `Start`. Admin analyzes; Worker helps. :desktop_computer:
- **CLI**: `python bunkerbuster.py --cli [--admin]`  
  Press <kbd>Enter</kbd> to go. :keyboard:
- **Web**: `python bunkerbuster.py --web`  
  Visit `http://localhost:5000`, click `Start`. :globe_with_meridians:
- **Docker**: `docker run -it bunkerbuster [--admin]`  
  Same as GUI, but containerized. :package:

### 3. How It Works <a name="how-it-works"></a>

> [!IMPORTANT]  
> BunkerBuster automates vulnerability analysis and sharing, keeping you anonymous via **Tor**.

1. Grabs test code from a URL.
2. Checks for flaws, tests crashes, builds bypasses.
3. Shares results on **IPFS** and **Twitter**.
4. Logs progress (e.g., `Exploit created: <IPFS link>`).

## Files <a name="files"></a>

- `bunkerbuster.py`: Core app logic.
- `install.sh`: One-command setup script.
- `Dockerfile`: Docker configuration.
- `README.md`: This guide.

## Stay Anonymous <a name="stay-anonymous"></a>

> [!WARNING]  
> Always use a **burner device** or VM to avoid traceability.

- **Tor**: Hides all connections with `socks5://127.0.0.1:9050`. :shield:
- **IPFS**: Stores files securely, no central server. :link:
- **Tips**:
  - Test on **fake targets** only to stay legal. :balance_scale:
  - Upload to GitHub via **Tor Browser**. :globe_with_meridians:

## Legal Notice <a name="legal"></a>

> [!CAUTION]  
> For **research only**. Do not use on systems without explicit permission. Developers are not liable for misuse.

## Resources <a name="resources"></a>

- [Tor Project](https://www.torproject.org/) for anonymous networking.
- [IPFS Docs](https://docs.ipfs.io/) for decentralized storage.
- [Twitter API](https://developer.twitter.com/) for sharing setup.

## Contribute <a name="contribute"></a>

Fork the repo, make improvements, and submit a pull request. Keep it anonymous and cross-platform! :handshake:

---

**BunkerBuster**: Break barriers, stay hidden, keep it simple! :sunglasses:  
[Back to top](#top)