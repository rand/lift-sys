#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting lift-sys...${NC}"

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo -e "${BLUE}Loading environment variables from .env${NC}"
    set -a
    source .env
    set +a
fi

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd frontend && npm install && cd ..
fi

# Start backend
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
uv run uvicorn lift_sys.api.server:app --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend server on http://localhost:5173${NC}"
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "${BLUE}──────────────────────────────────────────${NC}"
echo -e "${GREEN}✓ Backend:  ${NC}http://localhost:8000"
echo -e "${GREEN}✓ API Docs: ${NC}http://localhost:8000/docs"
echo -e "${GREEN}✓ Frontend: ${NC}http://localhost:5173"
echo -e "${BLUE}──────────────────────────────────────────${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Wait for both processes
wait
