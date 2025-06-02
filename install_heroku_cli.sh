#!/bin/bash

# Heroku CLI Installation Script using Tarballs
# Based on https://devcenter.heroku.com/articles/heroku-cli#tarballs

set -e

echo "Installing Heroku CLI via tarball..."

# Determine architecture and OS
ARCH=$(uname -m)
OS=$(uname -s | tr '[:upper:]' '[:lower:]')

# Map architecture names
case $ARCH in
    x86_64)
        ARCH="x64"
        ;;
    arm64|aarch64)
        ARCH="arm64"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

# Set download URL based on OS and architecture
if [ "$OS" = "linux" ]; then
    TARBALL_URL="https://cli-assets.heroku.com/channels/stable/heroku-linux-$ARCH.tar.xz"
elif [ "$OS" = "darwin" ]; then
    TARBALL_URL="https://cli-assets.heroku.com/channels/stable/heroku-darwin-$ARCH.tar.xz"
else
    echo "Unsupported operating system: $OS"
    exit 1
fi

# Create installation directory
INSTALL_DIR="/usr/local/lib/heroku"
BIN_DIR="/usr/local/bin"

echo "Downloading Heroku CLI from: $TARBALL_URL"

# Download and extract
cd /tmp
curl -L "$TARBALL_URL" | tar -xJ

# Install to system directory
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r heroku/* "$INSTALL_DIR/"

# Create symlink
sudo ln -sf "$INSTALL_DIR/bin/heroku" "$BIN_DIR/heroku"

# Cleanup
rm -rf heroku

# Verify installation
if command -v heroku >/dev/null 2>&1; then
    echo "✅ Heroku CLI installed successfully"
    heroku --version
else
    echo "❌ Installation failed"
    exit 1
fi

echo "🎉 Heroku CLI is ready to use!"
echo "Run 'heroku login' to authenticate"