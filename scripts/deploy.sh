#!/bin/bash
###############################################################################
# DEPLOYMENT SCRIPT
# Production deployment script for Amarktai Network
# Builds frontend, syncs to web root, and reloads nginx
###############################################################################

set -e  # Exit on error

echo "=========================================="
echo "🚀 AMARKTAI NETWORK - DEPLOYMENT SCRIPT"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_DIR="./frontend"
BUILD_DIR="$FRONTEND_DIR/build"
WEB_ROOT="${WEB_ROOT:-/var/www/html/amarktai}"
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"

echo "📋 Configuration:"
echo "  Frontend Dir: $FRONTEND_DIR"
echo "  Build Dir: $BUILD_DIR"
echo "  Web Root: $WEB_ROOT"
echo "  Nginx Service: $NGINX_SERVICE"
echo ""

# Step 1: Clean previous build
echo "🧹 Step 1: Cleaning previous build..."
cd "$FRONTEND_DIR"
if [ -d "build" ]; then
    echo "  Removing old build directory..."
    rm -rf build
fi

if [ -d "node_modules" ]; then
    echo "  Removing node_modules for clean install..."
    rm -rf node_modules
fi

# Step 2: Install dependencies
echo ""
echo "📦 Step 2: Installing dependencies..."
npm ci --silent

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ FAIL: npm ci failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 3: Build frontend
echo ""
echo "🔨 Step 3: Building frontend..."
npm run build

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ FAIL: Build failed${NC}"
    exit 1
fi

if [ ! -d "build" ]; then
    echo -e "${RED}✗ FAIL: Build directory not created${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build successful${NC}"

# Step 4: Generate build hash for verification
echo ""
echo "🔐 Step 4: Generating build hash..."
BUILD_HASH=$(find build -type f -name "*.js" -o -name "*.css" | sort | xargs cat | md5sum | cut -d' ' -f1)
echo "$BUILD_HASH" > build/BUILD_HASH.txt
echo "  Build Hash: $BUILD_HASH"
echo -e "${GREEN}✓ Build hash generated${NC}"

# Step 5: Create backup of current deployment (if exists)
cd ..
echo ""
echo "💾 Step 5: Creating backup..."
if [ -d "$WEB_ROOT" ]; then
    BACKUP_DIR="${WEB_ROOT}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "  Creating backup at: $BACKUP_DIR"
    sudo cp -r "$WEB_ROOT" "$BACKUP_DIR"
    echo -e "${GREEN}✓ Backup created${NC}"
else
    echo -e "${YELLOW}⚠ No existing deployment to backup${NC}"
fi

# Step 6: Sync build to web root
echo ""
echo "🚀 Step 6: Deploying to web root..."
if [ ! -d "$WEB_ROOT" ]; then
    echo "  Creating web root directory..."
    sudo mkdir -p "$WEB_ROOT"
fi

echo "  Syncing files..."
sudo rsync -av --delete "$BUILD_DIR/" "$WEB_ROOT/"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ FAIL: rsync failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Files synced to $WEB_ROOT${NC}"

# Step 7: Fix permissions
echo ""
echo "🔒 Step 7: Setting permissions..."
sudo chown -R www-data:www-data "$WEB_ROOT"
sudo chmod -R 755 "$WEB_ROOT"
echo -e "${GREEN}✓ Permissions set${NC}"

# Step 8: Reload nginx
echo ""
echo "🔄 Step 8: Reloading nginx..."
if command -v systemctl &> /dev/null; then
    sudo systemctl reload "$NGINX_SERVICE"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Nginx reloaded${NC}"
    else
        echo -e "${YELLOW}⚠ Nginx reload failed, trying restart...${NC}"
        sudo systemctl restart "$NGINX_SERVICE"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Nginx restarted${NC}"
        else
            echo -e "${RED}✗ FAIL: Could not reload/restart nginx${NC}"
            exit 1
        fi
    fi
else
    sudo service "$NGINX_SERVICE" reload
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Nginx reloaded${NC}"
    else
        echo -e "${RED}✗ FAIL: Could not reload nginx${NC}"
        exit 1
    fi
fi

# Step 9: Verify deployment
echo ""
echo "✅ Step 9: Verifying deployment..."
if [ -f "$WEB_ROOT/BUILD_HASH.txt" ]; then
    DEPLOYED_HASH=$(cat "$WEB_ROOT/BUILD_HASH.txt")
    if [ "$BUILD_HASH" = "$DEPLOYED_HASH" ]; then
        echo -e "${GREEN}✓ Build hash matches: $DEPLOYED_HASH${NC}"
    else
        echo -e "${YELLOW}⚠ Build hash mismatch!${NC}"
        echo "  Expected: $BUILD_HASH"
        echo "  Deployed: $DEPLOYED_HASH"
    fi
else
    echo -e "${YELLOW}⚠ BUILD_HASH.txt not found in deployment${NC}"
fi

# Check if index.html exists
if [ -f "$WEB_ROOT/index.html" ]; then
    echo -e "${GREEN}✓ index.html deployed${NC}"
else
    echo -e "${RED}✗ index.html missing!${NC}"
    exit 1
fi

# List deployed files count
FILE_COUNT=$(find "$WEB_ROOT" -type f | wc -l)
echo -e "${GREEN}✓ Total files deployed: $FILE_COUNT${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ DEPLOYMENT SUCCESSFUL!${NC}"
echo "=========================================="
echo ""
echo "📊 Deployment Summary:"
echo "  Build Hash: $BUILD_HASH"
echo "  Web Root: $WEB_ROOT"
echo "  Files: $FILE_COUNT"
echo "  Timestamp: $(date)"
echo ""
echo "🌐 Your application is now live!"
echo ""
