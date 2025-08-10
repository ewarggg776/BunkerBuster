#!/bin/bash

# Enhanced error handling
set -e  # Exit on any error
set -u  # Exit on undefined variables

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Ensure we're using bash
if [ -z "${BASH_VERSION:-}" ]; then
    log_info "Switching to bash..."
    exec bash "$0" "$@"
fi

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    log_warn "Running as root is not recommended. Consider running as a regular user."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Detect OS with better logic
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "Linux";;
        Darwin*)    echo "macOS";;
        CYGWIN*)    echo "Windows";;
        MINGW*)     echo "Windows";;
        MSYS*)      echo "Windows";;
        *)          echo "Unknown";;
    esac
}

OS=$(detect_os)
log_info "Detected OS: $OS"

# Check for required commands
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is required but not installed."
        return 1
    fi
    return 0
}

# Install Python and pip with error handling
install_python() {
    log_info "Installing Python and pip..."
    
    case "$OS" in
        Linux)
            if command -v apt-get &> /dev/null; then
                sudo apt-get update -y || { log_error "Failed to update package list"; return 1; }
                sudo apt-get install -y python3 python3-pip python3-venv || { log_error "Failed to install Python"; return 1; }
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 python3-pip || { log_error "Failed to install Python"; return 1; }
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip || { log_error "Failed to install Python"; return 1; }
            else
                log_error "No supported package manager found (apt-get, yum, dnf)"
                return 1
            fi
            ;;
        macOS)
            if command -v brew &> /dev/null; then
                brew install python3 || { log_error "Failed to install Python via Homebrew"; return 1; }
            else
                log_error "Homebrew not found. Please install Homebrew first: https://brew.sh/"
                return 1
            fi
            ;;
        Windows)
            log_warn "Windows detected. Please install Python manually from https://python.org"
            log_warn "Make sure to add Python to PATH during installation"
            return 0
            ;;
        *)
            log_error "Unsupported OS: $OS"
            log_error "Please install Python 3 and pip manually"
            return 1
            ;;
    esac
    
    log_info "Python installation completed"
    return 0
}

# Create virtual environment
create_venv() {
    log_info "Creating Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv || { log_error "Failed to create virtual environment"; return 1; }
    fi
    
    # Activate virtual environment
    case "$OS" in
        Windows)
            source venv/Scripts/activate || { log_error "Failed to activate virtual environment"; return 1; }
            ;;
        *)
            source venv/bin/activate || { log_error "Failed to activate virtual environment"; return 1; }
            ;;
    esac
    
    log_info "Virtual environment activated"
    return 0
}

# Install Python dependencies with proper error handling
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    # Upgrade pip first
    pip install --upgrade pip || { log_warn "Failed to upgrade pip, continuing..."; }
    
    # Install dependencies one by one for better error reporting
    local deps=(
        "PyQt5"
        "websockets"
        "requests"
        "beautifulsoup4"
        "python-magic-bin"
        "ipfshttpclient"
        "tweepy"
        "flask"
        "stem"
        "Pillow"
        "torch"
        "transformers"
    )
    
    for dep in "${deps[@]}"; do
        log_info "Installing $dep..."
        pip install "$dep" || { log_error "Failed to install $dep"; return 1; }
    done
    
    log_info "Python dependencies installed successfully"
    return 0
}

# Install Tor with better error handling
install_tor() {
    log_info "Installing Tor..."
    
    case "$OS" in
        Linux)
            if command -v apt-get &> /dev/null; then
                sudo apt-get install -y tor || { log_error "Failed to install Tor"; return 1; }
                
                # Backup original torrc
                if [ -f /etc/tor/torrc ]; then
                    sudo cp /etc/tor/torrc /etc/tor/torrc.backup.$(date +%Y%m%d_%H%M%S)
                fi
                
                # Configure Tor control port
                if ! grep -q "ControlPort 9051" /etc/tor/torrc; then
                    echo "ControlPort 9051" | sudo tee -a /etc/tor/torrc > /dev/null
                fi
                
                sudo systemctl enable tor || log_warn "Failed to enable Tor service"
                sudo systemctl restart tor || log_warn "Failed to start Tor service"
                
            else
                log_error "apt-get not found. Please install Tor manually"
                return 1
            fi
            ;;
        macOS)
            if command -v brew &> /dev/null; then
                brew install tor || { log_error "Failed to install Tor via Homebrew"; return 1; }
                brew services start tor || log_warn "Failed to start Tor service"
            else
                log_error "Homebrew not found. Please install Tor manually"
                return 1
            fi
            ;;
        Windows)
            log_warn "Windows detected. Please download and install Tor Browser manually"
            log_warn "Visit: https://www.torproject.org/download/"
            return 0
            ;;
        *)
            log_error "Please install Tor manually for your OS"
            return 1
            ;;
    esac
    
    log_info "Tor installation completed"
    return 0
}

# Download LLaMA model with correct API
download_llama() {
    log_info "Attempting to download LLaMA model..."
    log_warn "Note: This requires Hugging Face account and model access approval"
    
    # Check if transformers is available
    if ! python3 -c "import transformers" 2>/dev/null; then
        log_error "Transformers library not available"
        return 1
    fi
    
    # Use correct transformers API
    python3 -c "
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

try:
    model_name = 'meta-llama/Llama-2-7b-hf'  # Using available model
    print('Downloading tokenizer...')
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    print('Downloading model (this may take a while)...')
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map='auto' if torch.cuda.is_available() else None
    )
    print('Model downloaded successfully!')
except Exception as e:
    print(f'Model download failed: {e}')
    print('You may need to:')
    print('1. Login to Hugging Face: huggingface-cli login')
    print('2. Request access to the model')
    print('3. Use a different model')
    exit(1)
" || {
        log_warn "LLaMA model download failed"
        log_warn "You can continue without the model, but functionality will be limited"
        log_warn "To fix this later:"
        log_warn "1. Install huggingface-cli: pip install huggingface_hub"
        log_warn "2. Login: huggingface-cli login"
        log_warn "3. Request model access from Meta"
        return 1
    }
    
    return 0
}

# Generate SSL certificates with better error handling
generate_ssl_certs() {
    log_info "Generating SSL certificates..."
    
    if ! check_command openssl; then
        log_error "OpenSSL not found. Please install OpenSSL first."
        return 1
    fi
    
    if [ -f "cert.pem" ] && [ -f "key.pem" ]; then
        log_warn "SSL certificates already exist. Skipping generation."
        return 0
    fi
    
    openssl req -x509 -newkey rsa:4096 -nodes \
        -out cert.pem -keyout key.pem -days 365 \
        -subj "/C=US/ST=Anon/L=Anon/O=Anon/OU=Anon/CN=localhost" \
        2>/dev/null || {
        log_error "Failed to generate SSL certificates"
        return 1
    }
    
    log_info "SSL certificates generated successfully"
    return 0
}

# Configure environment
configure_environment() {
    log_info "Configuring environment..."
    
    # Create .env file for local configuration
    cat > .env << EOF
# BunkerBuster Configuration
TOR_PROXY=socks5://127.0.0.1:9050
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
EOF
    
    log_info "Environment configuration created in .env file"
    log_warn "Please edit .env file to add your Twitter API credentials"
    return 0
}

# Build Docker image with proper error handling
build_docker_image() {
    log_info "Building Docker image..."
    
    if ! check_command docker; then
        log_warn "Docker not found. Skipping Docker image build."
        log_warn "Install Docker to use containerized deployment"
        return 0
    fi
    
    # Check if Dockerfile already exists and is different
    if [ -f "Dockerfile" ]; then
        log_warn "Dockerfile already exists. Backing up..."
        cp Dockerfile "Dockerfile.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create optimized Dockerfile
    cat > Dockerfile << 'EOF'
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tor \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Configure Tor
RUN echo "ControlPort 9051" >> /etc/tor/torrc

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Generate SSL certificates
RUN openssl req -x509 -newkey rsa:4096 -nodes \
    -out cert.pem -keyout key.pem -days 365 \
    -subj "/C=US/ST=Anon/L=Anon/O=Anon/OU=Anon/CN=localhost"

# Expose ports
EXPOSE 5000 8765

# Default command
CMD ["python", "bunkerbuster.py"]
EOF

    # Create requirements.txt
    cat > requirements.txt << 'EOF'
PyQt5
websockets
requests
beautifulsoup4
python-magic-bin
ipfshttpclient
tweepy
flask
stem
Pillow
torch
transformers
EOF

    # Build Docker image
    docker build -t bunkerbuster . || {
        log_error "Docker build failed"
        return 1
    }
    
    log_info "Docker image built successfully"
    return 0
}

# Main installation function
main() {
    log_info "Starting BunkerBuster installation..."
    
    # Check for basic requirements
    if [ "$OS" = "Unknown" ]; then
        log_error "Unsupported operating system"
        exit 1
    fi
    
    # Install components
    install_python || { log_error "Python installation failed"; exit 1; }
    create_venv || { log_error "Virtual environment creation failed"; exit 1; }
    install_python_deps || { log_error "Python dependencies installation failed"; exit 1; }
    install_tor || log_warn "Tor installation failed, continuing..."
    download_llama || log_warn "LLaMA model download failed, continuing..."
    generate_ssl_certs || log_warn "SSL certificate generation failed, continuing..."
    configure_environment || log_warn "Environment configuration failed, continuing..."
    build_docker_image || log_warn "Docker image build failed, continuing..."
    
    log_info "Installation completed!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Edit .env file to add your Twitter API credentials"
    log_info "2. Start IPFS daemon: ipfs daemon"
    log_info "3. Run BunkerBuster: python bunkerbuster.py"
    log_info ""
    log_info "Available modes:"
    log_info "  GUI:    python bunkerbuster.py"
    log_info "  CLI:    python bunkerbuster.py --cli"
    log_info "  Web:    python bunkerbuster.py --web"
    log_info "  Docker: docker run -it bunkerbuster"
}

# Run main function
main "$@"