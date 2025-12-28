#!/bin/bash
# Amarktai Network - Backend Setup Script
# For Ubuntu 24.04 LTS with Python 3.12
# Run as: sudo bash tools/backend_setup.sh

set -e  # Exit on error

echo "🐍 Amarktai Network - Backend Setup"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root or with sudo${NC}"
    exit 1
fi

# Get actual user (when using sudo)
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "✅ Running as root, actual user: $ACTUAL_USER"

# Configuration
APP_DIR="/var/amarktai/app"
BACKEND_DIR="$APP_DIR/backend"
VENV_DIR="/var/amarktai/venv"
LOG_DIR="/var/amarktai/logs"

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
apt-get update -qq
apt-get install -y python3.12 python3.12-venv python3.12-dev \
    build-essential pkg-config libssl-dev \
    curl git ca-certificates

echo "✅ System dependencies installed"

# Create directory structure
echo ""
echo "📁 Creating directory structure..."
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$(dirname $VENV_DIR)"

echo "✅ Directories created"

# Create Python virtual environment
echo ""
echo "🐍 Creating Python virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Venv already exists, recreating...${NC}"
    rm -rf "$VENV_DIR"
fi

python3.12 -m venv "$VENV_DIR"
echo "✅ Virtual environment created"

# Activate venv and upgrade pip
echo ""
echo "📦 Upgrading pip and setuptools..."
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip setuptools wheel
echo "✅ Pip upgraded"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if [ -f "$BACKEND_DIR/requirements/base.txt" ]; then
    echo "Installing base requirements (core API)..."
    pip install --quiet -r "$BACKEND_DIR/requirements/base.txt"
    echo "✅ Base dependencies installed"
    
    # Optional: Install trading dependencies
    if [ -f "$BACKEND_DIR/requirements/trading.txt" ]; then
        read -p "Install trading features (CCXT)? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "Installing trading dependencies..."
            pip install --quiet -r "$BACKEND_DIR/requirements/trading.txt"
            echo "✅ Trading dependencies installed"
        fi
    fi
    
    # Optional: Install AI dependencies
    if [ -f "$BACKEND_DIR/requirements/ai.txt" ]; then
        read -p "Install AI features (ML, transformers, LangChain)? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping AI dependencies (can install later)"
        else
            echo "Installing AI dependencies (this may take 2-3 minutes)..."
            pip install --quiet -r "$BACKEND_DIR/requirements/ai.txt"
            echo "✅ AI dependencies installed"
        fi
    fi
    
    # Optional: Install agent dependencies (conflicts with AI)
    if [ -f "$BACKEND_DIR/requirements/agents.txt" ]; then
        read -p "Install Fetch.ai agent features (conflicts with AI)? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "⚠️  Warning: Agents conflict with AI features (protobuf version)"
            echo "Installing agent dependencies..."
            pip install --quiet -r "$BACKEND_DIR/requirements/agents.txt"
            echo "✅ Agent dependencies installed"
        fi
    fi
    
    # Legacy support: Install from old requirements.txt if new structure doesn't exist
elif [ -f "$BACKEND_DIR/requirements.txt" ]; then
    echo "⚠️  Using legacy requirements.txt (consider migrating to modular structure)"
    echo "Installing from requirements.txt..."
    pip install --quiet -r "$BACKEND_DIR/requirements.txt"
    echo "✅ Dependencies installed"
    
    # Optional: Install AI dependencies if user wants them
    if [ -f "$BACKEND_DIR/requirements-ai.txt" ]; then
        read -p "Install optional AI dependencies (uagents, cosmpy)? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Installing optional AI dependencies..."
            pip install --quiet -r "$BACKEND_DIR/requirements-ai.txt"
            echo "✅ AI dependencies installed"
        fi
    fi
else
    echo -e "${RED}❌ No requirements files found in $BACKEND_DIR${NC}"
    exit 1
fi

# Verify installation
echo ""
echo "✅ Verifying installation..."
python3 -c "import fastapi, uvicorn, motor; print('Core packages: OK')" || {
    echo -e "${RED}❌ Core package verification failed${NC}"
    exit 1
}

# Check optional packages
if pip list | grep -q "ccxt"; then
    python3 -c "import ccxt; print('Trading packages: OK')" || echo "⚠️  CCXT import failed"
fi

if pip list | grep -q "numpy"; then
    python3 -c "import numpy, scipy, pandas; print('AI/ML packages: OK')" || echo "⚠️  AI package import failed"
fi

# Compile Python files to check for syntax errors
echo ""
echo "🔍 Checking for syntax errors..."
python3 -m compileall "$BACKEND_DIR" -q || {
    echo -e "${RED}❌ Syntax errors found!${NC}"
    exit 1
}
echo "✅ No syntax errors"

# Set proper permissions
echo ""
echo "🔒 Setting permissions..."
chown -R $ACTUAL_USER:$ACTUAL_USER "$APP_DIR"
chown -R $ACTUAL_USER:$ACTUAL_USER "$VENV_DIR"
chown -R $ACTUAL_USER:$ACTUAL_USER "$LOG_DIR"
echo "✅ Permissions set"

# Check if .env exists
echo ""
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found${NC}"
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        echo "Creating .env from .env.example..."
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
        echo -e "${YELLOW}⚠️  IMPORTANT: Edit $BACKEND_DIR/.env with your configuration${NC}"
        echo "   Required: JWT_SECRET, MONGO_URL, OPENAI_API_KEY"
    fi
else
    echo "✅ .env file exists"
fi

# Summary
echo ""
echo "======================================"
echo -e "${GREEN}✅ Backend setup complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file: sudo nano $BACKEND_DIR/.env"
echo "   - Set JWT_SECRET (run: openssl rand -hex 32)"
echo "   - Set MONGO_URL"
echo "   - Set OPENAI_API_KEY (if AI features installed)"
echo "   - Set feature flags:"
echo "     ENABLE_TRADING=true (if trading.txt installed)"
echo "     ENABLE_AI=true (if ai.txt installed)"
echo "     ENABLE_AGENTS=true (if agents.txt installed)"
echo ""
echo "2. Install additional features:"
echo "   Trading: pip install -r $BACKEND_DIR/requirements/trading.txt"
echo "   AI: pip install -r $BACKEND_DIR/requirements/ai.txt"
echo "   Dev tools: pip install -r $BACKEND_DIR/requirements/dev.txt"
echo ""
echo "3. Install systemd service: sudo bash tools/systemd_install.sh"
echo ""
echo "3. Start service: sudo systemctl start amarktai-api"
echo ""
echo "Directory structure:"
echo "  App: $APP_DIR"
echo "  Venv: $VENV_DIR"
echo "  Logs: $LOG_DIR"
echo ""
