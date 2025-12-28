#!/bin/bash
# Amarktai Network - Frontend Setup Script
# For Ubuntu 24.04 LTS with Node.js 20.x
# Run as: sudo bash tools/frontend_setup.sh

set -e  # Exit on error

echo "⚛️  Amarktai Network - Frontend Setup"
echo "====================================="

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
FRONTEND_DIR="$APP_DIR/frontend"
BUILD_DIR="$FRONTEND_DIR/build"

# Install Node.js 20.x if not installed
echo ""
echo "📦 Checking Node.js installation..."
if ! command -v node &> /dev/null || ! node --version | grep -q "v20"; then
    echo "Installing Node.js 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    echo "✅ Node.js installed"
else
    echo "✅ Node.js 20.x already installed ($(node --version))"
fi

# Verify Node and npm versions
echo ""
echo "✅ Node version: $(node --version)"
echo "✅ npm version: $(npm --version)"

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    
    # Remove old node_modules if exists
    if [ -d "node_modules" ]; then
        echo "Removing old node_modules..."
        rm -rf node_modules
    fi
    
    # Install as actual user to avoid permission issues
    echo "Running npm install..."
    su - $ACTUAL_USER -c "cd $FRONTEND_DIR && npm install"
    
    echo "✅ Dependencies installed"
else
    echo -e "${RED}❌ Frontend directory not found: $FRONTEND_DIR${NC}"
    exit 1
fi

# Build frontend
echo ""
echo "🏗️  Building frontend..."
su - $ACTUAL_USER -c "cd $FRONTEND_DIR && npm run build"

if [ -f "$BUILD_DIR/index.html" ]; then
    echo "✅ Build successful"
else
    echo -e "${RED}❌ Build failed - index.html not found${NC}"
    exit 1
fi

# Set proper permissions
echo ""
echo "🔒 Setting permissions..."
chown -R $ACTUAL_USER:$ACTUAL_USER "$FRONTEND_DIR"
echo "✅ Permissions set"

# Summary
echo ""
echo "======================================"
echo -e "${GREEN}✅ Frontend setup complete!${NC}"
echo "======================================"
echo ""
echo "Build output:"
echo "  Location: $BUILD_DIR"
echo "  Files: $(ls -1 $BUILD_DIR | wc -l) files"
echo ""
echo "Next steps:"
echo "1. Configure nginx to serve $BUILD_DIR"
echo "2. Run health check: bash tools/health_check.sh"
echo ""
