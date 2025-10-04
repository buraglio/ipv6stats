#!/bin/bash

###############################################################################
# IPv6 Statistics Dashboard - Startup Script
#
# This script starts the IPv6 Statistics Dashboard with optimized settings
# for production deployment on Linux systems.
#
# Usage:
#   ./start_ipv6stats.sh [options]
#
# Options:
#   --port PORT       Specify port (default: 8501)
#   --host HOST       Specify host (default: ::1)
#   --dev             Run in development mode (auto-reload)
#   --help            Show this help message
###############################################################################

set -e  # Exit on error

# Default configuration
PORT=8501
HOST="::1"  # IPv6 localhost only for security
DEV_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --help)
            echo "IPv6 Statistics Dashboard - Startup Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --port PORT    Specify port (default: 8501)"
            echo "  --host HOST    Specify host (default: ::1)"
            echo "  --dev          Run in development mode"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Print banner
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║         IPv6 Statistics Dashboard                        ║"
echo "║         Optimized for Performance & Efficiency           ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Change to script directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Warning: No virtual environment found${NC}"
    echo "Consider creating one with: python3 -m venv venv"
    echo ""
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment (venv)...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment (.venv)...${NC}"
    source .venv/bin/activate
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}Error: Streamlit is not installed${NC}"
    echo "Install dependencies with: pip install -r requirements.txt"
    exit 1
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}Error: app.py not found${NC}"
    exit 1
fi

# Display configuration
echo -e "${GREEN}Configuration:${NC}"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Mode: $([ "$DEV_MODE" = true ] && echo "Development" || echo "Production")"
echo "  Directory: $SCRIPT_DIR"
echo ""

# Set environment variables for optimization
export STREAMLIT_SERVER_PORT=$PORT
export STREAMLIT_SERVER_ADDRESS=$HOST
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_ENABLE_CORS=false
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_THEME_BASE="light"

# Additional Python optimizations
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Memory optimization for production
if [ "$DEV_MODE" = false ]; then
    export STREAMLIT_SERVER_MAX_UPLOAD_SIZE=5
    export STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true
fi

echo -e "${GREEN}Starting IPv6 Statistics Dashboard...${NC}"
echo ""
echo -e "${YELLOW}Dashboard will be available at:${NC}"
echo -e "${GREEN}  http://localhost:$PORT${NC}"
if [ "$HOST" = "0.0.0.0" ]; then
    echo -e "${GREEN}  http://$(hostname -I | awk '{print $1}'):$PORT${NC}"
fi
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start Streamlit
if [ "$DEV_MODE" = true ]; then
    # Development mode with auto-reload
    streamlit run app.py \
        --server.port=$PORT \
        --server.address=$HOST \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        --server.fileWatcherType=auto
else
    # Production mode
    streamlit run app.py \
        --server.port=$PORT \
        --server.address=$HOST \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        --server.fileWatcherType=none \
        --server.runOnSave=false
fi
