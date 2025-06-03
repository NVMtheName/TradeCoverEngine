#!/bin/bash
# Local Development Setup Script

set -e

echo "🔧 Setting up Arbion Trading Platform for local development..."

# Check Python version
if ! python3.11 --version &> /dev/null; then
    echo "❌ Python 3.11 not found. Please install Python 3.11+"
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3.11 install -r requirements.txt

# Create local database (SQLite for development)
echo "Setting up local development database..."
export DATABASE_URL="sqlite:///arbion_dev.db"
export SESSION_SECRET="dev-session-secret-key"
export FLASK_ENV="development"

# Initialize database
python3.11 -c "from app import db; db.create_all()"

echo "✅ Local development setup complete!"
echo "🚀 Start the application with: python3.11 app.py"
echo "🌐 Access at: http://localhost:5000"
echo "👤 Default admin login: admin / admin123"
