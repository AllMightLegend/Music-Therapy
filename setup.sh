#!/bin/bash
# Setup script for Music Therapy App with Hume AI

echo "🎵 Music Therapy Recommender - Setup Script"
echo "============================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
else
    python_cmd="python3"
fi

python_cmd="${python_cmd:-python}"

echo "✓ Python found: $($python_cmd --version)"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ .env created. Please edit it and add your HUME_API_KEY"
        echo "   Get your key from: https://platform.hume.ai/settings/keys"
    else
        echo "❌ .env.example not found!"
        exit 1
    fi
else
    echo "✓ .env file already exists"
fi

echo ""

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    $python_cmd -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

echo ""

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your HUME_API_KEY"
echo "2. Download muse_v3.csv to the project root (if not already present)"
echo "3. Run: streamlit run app.py"
echo ""
