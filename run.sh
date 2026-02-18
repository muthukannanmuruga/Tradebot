#!/bin/bash

# AI Trading Bot Startup Script

echo "🤖 AI Trading Bot - Starting..."
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "💡 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "💡 Copying .env.example to .env..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys before running!"
    echo "   nano .env"
    exit 1
fi

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Run configuration test
echo ""
echo "🧪 Running configuration tests..."
python test_setup.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Configuration test failed!"
    echo "💡 Please fix the errors above before starting the bot."
    exit 1
fi

# Start the server
echo ""
echo "🚀 Starting FastAPI server..."
echo "📊 API Documentation: http://localhost:8000/docs"
echo "💻 Press Ctrl+C to stop"
echo ""

python main.py
