#!/bin/bash
#
# AquaBrain V2.0 - PLATINUM Edition
# One-Click Launch Script
#
# This script starts all components of the AquaBrain system:
# 1. Redis Server (message broker)
# 2. Celery Worker (async task processor)
# 3. FastAPI Backend (API server)
# 4. Next.js Frontend (dashboard)
#
# Usage: ./start_aquabrain.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo -e "${CYAN}"
echo "======================================"
echo "   AquaBrain V2.0 - PLATINUM Edition"
echo "   Autonomous Engineering Platform"
echo "======================================"
echo -e "${NC}"

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    if check_port $1; then
        echo -e "${YELLOW}Killing existing process on port $1...${NC}"
        lsof -ti:$1 | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down AquaBrain...${NC}"

    # Kill background processes
    if [ ! -z "$REDIS_PID" ]; then
        kill $REDIS_PID 2>/dev/null || true
    fi
    if [ ! -z "$CELERY_PID" ]; then
        kill $CELERY_PID 2>/dev/null || true
    fi
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    echo -e "${GREEN}AquaBrain stopped.${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# ============================================
# STEP 1: Redis Server
# ============================================
echo -e "\n${BLUE}[1/4] Starting Redis Server...${NC}"

# Check if Redis is installed
if command -v redis-server &> /dev/null; then
    kill_port 6379
    redis-server --daemonize yes --loglevel warning
    REDIS_PID=$(pgrep -f "redis-server")
    echo -e "${GREEN}Redis started (PID: $REDIS_PID)${NC}"
else
    echo -e "${YELLOW}Redis not installed. Using filesystem broker fallback.${NC}"
    echo -e "${YELLOW}Install Redis with: sudo apt install redis-server${NC}"
    mkdir -p "$BACKEND_DIR/broker/out" "$BACKEND_DIR/broker/processed"
fi

# ============================================
# STEP 2: Celery Worker
# ============================================
echo -e "\n${BLUE}[2/4] Starting Celery Worker...${NC}"

cd "$BACKEND_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Start Celery worker in background
if command -v redis-server &> /dev/null; then
    celery -A worker worker --loglevel=info --concurrency=2 &
    CELERY_PID=$!
    echo -e "${GREEN}Celery Worker started (PID: $CELERY_PID)${NC}"
else
    echo -e "${YELLOW}Celery skipped (no Redis). Using thread-based fallback.${NC}"
fi

# ============================================
# STEP 3: FastAPI Backend
# ============================================
echo -e "\n${BLUE}[3/4] Starting FastAPI Backend...${NC}"

kill_port 8000

# Start FastAPI server
python main.py &
BACKEND_PID=$!
echo -e "${GREEN}FastAPI Backend started (PID: $BACKEND_PID)${NC}"
echo -e "${CYAN}API Docs: http://localhost:8000/docs${NC}"

# Wait for backend to be ready
sleep 2
if check_port 8000; then
    echo -e "${GREEN}Backend is ready!${NC}"
else
    echo -e "${RED}Backend failed to start!${NC}"
    exit 1
fi

# ============================================
# STEP 4: Next.js Frontend
# ============================================
echo -e "\n${BLUE}[4/4] Starting Next.js Frontend...${NC}"

cd "$FRONTEND_DIR"

kill_port 3000

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

# Start frontend
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}Next.js Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "${CYAN}Dashboard: http://localhost:3000${NC}"

# ============================================
# System Ready
# ============================================
echo -e "\n${GREEN}"
echo "======================================"
echo "   AquaBrain V2.0 is LIVE!"
echo "======================================"
echo -e "${NC}"
echo -e "${CYAN}Frontend:${NC}  http://localhost:3000"
echo -e "${CYAN}Backend:${NC}   http://localhost:8000"
echo -e "${CYAN}API Docs:${NC}  http://localhost:8000/docs"
echo -e "${CYAN}Health:${NC}    http://localhost:8000/api/health"
echo ""
echo -e "${PURPLE}Architecture:${NC}"
echo "  - Async Engine: Celery + Redis"
echo "  - Database: SQLite (project history)"
echo "  - Frontend: Next.js 15 + React 19"
echo "  - Backend: FastAPI + Pydantic"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running
wait
