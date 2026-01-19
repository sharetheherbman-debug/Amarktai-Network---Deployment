#!/bin/bash
# VPS Deployment Script
# Deploys backend and frontend to VPS according to canonical layout
# Backend: /var/amarktai/app/backend
# Frontend build: /var/amarktai/frontend (nginx root)

set -e  # Exit on error

echo "🚀 Amarktai Network - VPS Deployment Script"
echo "============================================="

# Configuration
APP_DIR="/var/amarktai/app"
FRONTEND_BUILD_DIR="/var/amarktai/frontend"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_SRC_DIR="$APP_DIR/frontend"
VENV_DIR="$APP_DIR/venv"
SYSTEMD_SERVICE="amarktai-api"

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
   echo "❌ This script requires sudo privileges"
   exit 1
fi

# Step 1: Install backend dependencies
echo ""
echo "📦 Step 1: Installing backend dependencies..."
cd "$BACKEND_DIR"

# Create/activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    sudo python3 -m venv "$VENV_DIR"
fi

# Activate venv and install dependencies
source "$VENV_DIR/bin/activate"

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    echo "✅ Backend dependencies installed"
else
    echo "⚠️  requirements.txt not found, skipping pip install"
fi

deactivate

# Step 2: Build frontend
echo ""
echo "🔨 Step 2: Building frontend..."
cd "$FRONTEND_SRC_DIR"

# Check if node_modules exists, install if not
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

# Build frontend
echo "Building React app..."
npm run build

if [ ! -d "build" ]; then
    echo "❌ Frontend build failed - build directory not found"
    exit 1
fi

echo "✅ Frontend built successfully"

# Step 3: Publish frontend build
echo ""
echo "📤 Step 3: Publishing frontend to nginx root..."

# Create frontend directory if it doesn't exist
sudo mkdir -p "$FRONTEND_BUILD_DIR"

# Copy build files
echo "Copying build files to $FRONTEND_BUILD_DIR..."
sudo rm -rf "$FRONTEND_BUILD_DIR"/*
sudo cp -r build/* "$FRONTEND_BUILD_DIR/"

# Set permissions
sudo chown -R www-data:www-data "$FRONTEND_BUILD_DIR"
sudo chmod -R 755 "$FRONTEND_BUILD_DIR"

echo "✅ Frontend published to $FRONTEND_BUILD_DIR"

# Step 4: Restart backend service
echo ""
echo "🔄 Step 4: Restarting backend service..."

# Check if systemd service exists
if systemctl list-units --full -all | grep -q "$SYSTEMD_SERVICE.service"; then
    echo "Restarting $SYSTEMD_SERVICE..."
    sudo systemctl restart "$SYSTEMD_SERVICE"
    
    # Wait a moment and check status
    sleep 2
    
    if systemctl is-active --quiet "$SYSTEMD_SERVICE"; then
        echo "✅ Backend service restarted successfully"
    else
        echo "⚠️  Backend service may have issues, checking status..."
        sudo systemctl status "$SYSTEMD_SERVICE" --no-pager
    fi
else
    echo "⚠️  SystemD service $SYSTEMD_SERVICE not found"
    echo "   You may need to start the backend manually"
fi

# Step 5: Verify deployment
echo ""
echo "✅ Deployment Summary"
echo "===================="
echo "Backend: $BACKEND_DIR"
echo "Frontend source: $FRONTEND_SRC_DIR"
echo "Frontend published: $FRONTEND_BUILD_DIR"
echo "SystemD service: $SYSTEMD_SERVICE"
echo ""
echo "✨ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Run smoke tests: ./scripts/go_live_smoke.sh"
echo "2. Check backend logs: sudo journalctl -u $SYSTEMD_SERVICE -f"
echo "3. Test frontend: curl http://localhost/"
echo "4. Test API: curl http://localhost:8000/api/system/ping"
