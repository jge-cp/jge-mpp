#!/bin/bash
#
# Multicam Partner Portal - Development Setup Script
# Usage: ./scripts/setup.sh [--with-test-users]
#
# This script sets up a local development environment:
# - Creates Python virtual environment
# - Installs dependencies
# - Runs database migrations (SQLite)
# - Loads initial data (camouflage types)
# - Optionally creates test users
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
WITH_TEST_USERS=false
for arg in "$@"; do
    case $arg in
        --with-test-users)
            WITH_TEST_USERS=true
            shift
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Multicam Partner Portal Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo -e "${RED}Error: manage.py not found.${NC}"
    echo "Please run this script from the project root directory:"
    echo "  cd /path/to/MCP-3 && ./scripts/setup.sh"
    exit 1
fi

# Check Python version
echo -e "${YELLOW}[1/6] Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}Error: Python is not installed.${NC}"
    echo "Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}Error: Python 3.11+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Create virtual environment
echo -e "${YELLOW}[2/6] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}[3/6] Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run migrations
echo -e "${YELLOW}[4/6] Running database migrations...${NC}"
python manage.py migrate --verbosity=0
echo -e "${GREEN}✓ Database migrations complete (SQLite)${NC}"

# Load initial data
echo -e "${YELLOW}[5/6] Loading initial data...${NC}"
python manage.py load_initial_data
echo -e "${GREEN}✓ Initial data loaded${NC}"

# Optionally create test users
echo -e "${YELLOW}[6/6] Test users...${NC}"
if [ "$WITH_TEST_USERS" = true ]; then
    python manage.py setup_test_users
    echo -e "${GREEN}✓ Test users created${NC}"
else
    echo -e "${BLUE}Skipped (use --with-test-users to create)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate the virtual environment:"
echo -e "     ${BLUE}source venv/bin/activate${NC}"
echo ""
echo "  2. Start the development server:"
echo -e "     ${BLUE}python manage.py runserver${NC}"
echo ""
echo "  3. Visit: http://localhost:8000"
echo ""

if [ "$WITH_TEST_USERS" = true ]; then
    echo "Test login credentials:"
    echo "  - partner / partner123"
    echo "  - primary_inspector / primary_inspector123"
    echo "  - final_inspector / final_inspector123"
    echo "  - staff / staff123"
    echo ""
fi

echo "For more information, see Docs/DEVELOPMENT.md"
echo ""

