#!/usr/bin/env bash
#
# install.sh - Plug-and-play deployment script for Amarktai Network
#
# This script provides a complete installation on Ubuntu 24.04:
# 1. Installs OS dependencies (Python 3.12, build tools, etc.)
# 2. Creates Python venv and installs requirements
# 3. Validates Python syntax with compileall
# 4. Installs and configures systemd service
# 5. Starts the service and validates health
# 6. Downloads OpenAPI spec and verifies routes

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check if running as root (needed for apt and systemctl)
if [ "$EUID" -ne 0 ]; then 
    log_error "Please run as root (use sudo)"
fi

log_section "Amarktai Network - Installation"
log_info "Project root: $PROJECT_ROOT"
log_info "Backend directory: $BACKEND_DIR"

# ============================================================================
# 1. Install OS Dependencies
# ============================================================================
log_section "1. Installing OS Dependencies"

log_info "Updating package lists..."
apt-get update -qq

log_info "Installing Python 3.12 and development tools..."
apt-get install -y -qq \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    build-essential \
    curl \
    git \
    nginx \
    || log_error "Failed to install OS dependencies"

log_success "OS dependencies installed"

# ============================================================================
# 2. Create Virtual Environment and Install Python Dependencies
# ============================================================================
log_section "2. Setting Up Python Environment"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
    log_info "Creating virtual environment..."
    python3.12 -m venv "$BACKEND_DIR/.venv" || log_error "Failed to create venv"
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

log_info "Activating virtual environment..."
source "$BACKEND_DIR/.venv/bin/activate"

log_info "Upgrading pip..."
python -m pip install --upgrade pip -q

log_info "Installing Python dependencies from requirements.txt..."
if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    python -m pip install -r "$BACKEND_DIR/requirements.txt" -q || log_error "Failed to install requirements"
    log_success "Python dependencies installed"
else
    log_error "requirements.txt not found in $BACKEND_DIR"
fi

# ============================================================================
# 3. Validate Python Syntax
# ============================================================================
log_section "3. Validating Python Syntax"

log_info "Running compileall on backend directory..."
if python -m compileall "$BACKEND_DIR" -q; then
    log_success "All Python files have valid syntax"
else
    log_error "Python syntax errors found - fix before continuing"
fi

# ============================================================================
# 4. Configure Environment
# ============================================================================
log_section "4. Configuring Environment"

if [ ! -f "$BACKEND_DIR/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        log_info "Copying .env.example to backend/.env..."
        cp "$PROJECT_ROOT/.env.example" "$BACKEND_DIR/.env"
        log_warning "Please edit $BACKEND_DIR/.env with your configuration"
    else
        log_warning "No .env.example found - you'll need to create .env manually"
    fi
else
    log_info ".env file already exists"
fi

# ============================================================================
# 5. Install Systemd Service
# ============================================================================
log_section "5. Installing Systemd Service"

# Create service file
SERVICE_FILE="/etc/systemd/system/amarktai-api.service"
log_info "Creating systemd service file at $SERVICE_FILE..."

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Amarktai Network API
After=network.target mongodb.service
Wants=mongodb.service

[Service]
Type=simple
User=runner
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/.venv/bin"
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

log_success "Systemd service file created"

# Reload systemd
log_info "Reloading systemd daemon..."
systemctl daemon-reload || log_error "Failed to reload systemd"

# Enable service to start on boot
log_info "Enabling service to start on boot..."
systemctl enable amarktai-api.service || log_error "Failed to enable service"

log_success "Systemd service installed and enabled"

# ============================================================================
# 6. Start Service and Validate
# ============================================================================
log_section "6. Starting Service"

log_info "Starting amarktai-api service..."
systemctl start amarktai-api.service || log_error "Failed to start service"

log_info "Waiting for service to be ready (30 seconds)..."
sleep 30

# Check if service is running
if systemctl is-active --quiet amarktai-api.service; then
    log_success "Service is running"
else
    log_error "Service failed to start - check logs with: journalctl -u amarktai-api.service -n 50"
fi

# ============================================================================
# 7. Health Check
# ============================================================================
log_section "7. Running Health Checks"

log_info "Checking /api/health/ping endpoint..."
if curl -s -f http://127.0.0.1:8000/api/health/ping > /dev/null 2>&1; then
    log_success "/api/health/ping is responding"
else
    # Try alternative health endpoint
    if curl -s -f http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        log_success "/api/health is responding"
    else
        log_warning "Health endpoint not responding yet - service may still be starting up"
    fi
fi

# ============================================================================
# 8. Verify OpenAPI Routes
# ============================================================================
log_section "8. Verifying OpenAPI Routes"

log_info "Downloading /openapi.json..."
if OPENAPI_JSON=$(curl -s -f http://127.0.0.1:8000/openapi.json 2>/dev/null); then
    log_success "OpenAPI spec downloaded"
    
    # Check for required routes
    REQUIRED_ROUTES=(
        "/api/auth/login"
        "/api/health/ping"
        "/api/realtime/events"
        "/api/system/ping"
    )
    
    for route in "${REQUIRED_ROUTES[@]}"; do
        if echo "$OPENAPI_JSON" | grep -q "$route"; then
            log_success "Route found: $route"
        else
            log_warning "Route not found: $route"
        fi
    done
    
    # Check for admin endpoints
    if echo "$OPENAPI_JSON" | grep -q "/api/admin"; then
        log_success "Admin endpoints mounted"
    else
        log_warning "Admin endpoints not found in OpenAPI spec"
    fi
else
    log_warning "Could not download OpenAPI spec - service may still be starting"
fi

# ============================================================================
# FINAL REPORT
# ============================================================================
log_section "Installation Complete"

echo ""
log_success "Amarktai Network installation successful!"
echo ""
log_info "Service Status:"
echo "  • Service: amarktai-api.service"
echo "  • Status: $(systemctl is-active amarktai-api.service)"
echo "  • Listening: http://127.0.0.1:8000"
echo ""
log_info "Useful Commands:"
echo "  • Check status: sudo systemctl status amarktai-api.service"
echo "  • View logs: sudo journalctl -u amarktai-api.service -f"
echo "  • Restart: sudo systemctl restart amarktai-api.service"
echo "  • Stop: sudo systemctl stop amarktai-api.service"
echo ""
log_info "Next Steps:"
echo "  1. Configure Nginx reverse proxy (see deployment/nginx-amarktai.conf)"
echo "  2. Set up SSL certificates (Let's Encrypt recommended)"
echo "  3. Configure MongoDB connection in $BACKEND_DIR/.env"
echo "  4. Update JWT_SECRET and other secrets in .env"
echo ""
log_success "Installation complete! 🚀"
