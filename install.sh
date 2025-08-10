#!/bin/bash

# Detect OS
OS=$(uname -s)
echo "Detected OS: $OS"

# Install Python and pip
echo "Installing Python and pip..."
case "$OS" in
    Linux)
        sudo apt-get update -y
        sudo apt-get install -y python3 python3-pip
        ;;
    Darwin) # macOS
        brew install python3
        ;;
    *)
        echo "Please install Python 3 and pip manually"
        exit 1
        ;;
esac

# Install dependencies
echo "Installing Python dependencies..."
pip install PyQt5 websockets requests beautifulsoup4 python-magic-bin ipfshttpclient tweepy flask stem Pillow torch transformers

# Install Tor with control port
echo "Installing Tor..."
case "$OS" in
    Linux)
        sudo apt-get install -y tor
        sudo sed -i 's/#ControlPort 9051/ControlPort 9051/' /etc/tor/torrc
        sudo systemctl enable tor
        sudo systemctl start tor
        ;;
    Darwin)
        brew install tor
        brew services start tor
        ;;
    *)
        echo "Please install Tor manually (e.g., Tor Browser for Windows)"
        ;;
esac

# Download LLaMA model
echo "Downloading LLaMA 3.1 model..."
python -c "from transformers import LLaMAForCausalLM, LLaMATokenizer; LLaMAForCausalLM.from_pretrained('meta-llama/Llama-3.1-8B'); LLaMATokenizer.from_pretrained('meta-llama/Llama-3.1-8B')"

# Generate SSL certificates
echo "Generating SSL certificates..."
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/C=US/ST=Anon/L=Anon/O=Anon/OU=Anon/CN=localhost"

# Configure environment
echo "Configuring environment..."
export PATH=$PATH:/usr/local/bin
echo "export PATH=$PATH:/usr/local/bin" >> ~/.bashrc
export TOR_PROXY="socks5://127.0.0.1:9050"
echo "export TOR_PROXY=socks5://127.0.0.1:9050" >> ~/.bashrc

# For Windows users
if [ "$OS" = "CYGWIN"* ] || [ "$OS" = "MINGW"* ]; then
    echo "For Windows, use PowerShell to install dependencies:"
    echo "pip install PyQt5 websockets requests beautifulsoup4 python-magic-bin ipfshttpclient tweepy flask stem Pillow torch transformers"
    echo "Download and install Tor Browser for Tor support."
    echo "Download LLaMA model manually: huggingface.co/meta-llama/Llama-3.1-8B"
fi

# Build Docker image
echo "Building Docker image..."
cat <<EOF > Dockerfile
FROM python:3.9-slim
RUN apt-get update && apt-get install -y tor && \
    echo "ControlPort 9051" >> /etc/tor/torrc && \
    pip install PyQt5 websockets requests beautifulsoup4 python-magic-bin ipfshttpclient tweepy flask stem Pillow torch transformers
RUN python -c "from transformers import LLaMAForCausalLM, LLaMATokenizer; LLaMAForCausalLM.from_pretrained('meta-llama/Llama-3.1-8B'); LLaMATokenizer.from_pretrained('meta-llama/Llama-3.1-8B')"
COPY . /app
WORKDIR /app
CMD ["python", "bunkerbuster.py"]
EOF
docker build -t bunkerbuster .

echo "Setup complete. Run with: python bunkerbuster.py [--admin|--finder|--web|--cli]"
