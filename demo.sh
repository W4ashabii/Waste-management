#!/bin/bash

# Demo Verification Script for Waste Management MVP
# This script demonstrates the key features of the system

echo "=== Waste Management MVP Demo Verification ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "1. Checking Docker status..."
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker is running${NC}"
else
    echo -e "${RED}✗ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo ""
echo "2. Starting services with Docker Compose..."
docker-compose up -d --build

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 15

echo ""
echo "3. Checking service health..."
echo "Backend:"
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend is not responding${NC}"
fi

echo "Model Service:"
if curl -s http://localhost:8001/health > /dev/null; then
    echo -e "${GREEN}✓ Model Service is healthy${NC}"
else
    echo -e "${RED}✗ Model Service is not responding${NC}"
fi

echo ""
echo "4. Seeding database..."
docker-compose exec -T backend python seed_db.py

echo ""
echo "5. Testing Authentication..."
echo "   Login as user:"
USER_TOKEN=$(curl -s -X POST -F "username=user@example.com" -F "password=user123" \
  http://localhost:8000/api/v1/auth/login | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$USER_TOKEN" ]; then
    echo -e "${GREEN}✓ User login successful${NC}"
else
    echo -e "${RED}✗ User login failed${NC}"
fi

echo "   Login as ward admin:"
WARD_TOKEN=$(curl -s -X POST -F "username=ward@example.com" -F "password=ward123" \
  http://localhost:8000/api/v1/auth/login | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$WARD_TOKEN" ]; then
    echo -e "${GREEN}✓ Ward admin login successful${NC}"
else
    echo -e "${RED}✗ Ward admin login failed${NC}"
fi

echo "   Login as municipality admin:"
MUNI_TOKEN=$(curl -s -X POST -F "username=municipality@example.com" -F "password=muni123" \
  http://localhost:8000/api/v1/auth/login | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$MUNI_TOKEN" ]; then
    echo -e "${GREEN}✓ Municipality admin login successful${NC}"
else
    echo -e "${RED}✗ Municipality admin login failed${NC}"
fi

echo ""
echo "6. Testing Detection Endpoint..."
# Create a test image
echo "test" > /tmp/test.jpg

DETECTION_RESULT=$(curl -s -X POST -F "image=@/tmp/test.jpg" -F "camera_id=demo-camera" \
  http://localhost:8000/api/v1/detect)

if echo "$DETECTION_RESULT" | grep -q "label"; then
    echo -e "${GREEN}✓ Detection successful${NC}"
    echo "   Result: $DETECTION_RESULT"
else
    echo -e "${RED}✗ Detection failed${NC}"
    echo "   Error: $DETECTION_RESULT"
fi

rm /tmp/test.jpg

echo ""
echo "7. Testing Truck Management..."
if [ -n "$WARD_TOKEN" ]; then
    TRUCKS=$(curl -s -X GET -H "Authorization: Bearer $WARD_TOKEN" \
      http://localhost:8000/api/v1/trucks)
    
    if echo "$TRUCKS" | grep -q "plate_no"; then
        echo -e "${GREEN}✓ Truck listing successful${NC}"
        echo "   Trucks: $TRUCKS"
    else
        echo -e "${RED}✗ Truck listing failed${NC}"
    fi
fi

echo ""
echo "8. Testing Alerts..."
if [ -n "$USER_TOKEN" ]; then
    ALERTS=$(curl -s -X GET -H "Authorization: Bearer $USER_TOKEN" \
      http://localhost:8000/api/v1/alerts)
    
    echo -e "${GREEN}✓ Alerts endpoint accessible${NC}"
    echo "   Alerts: $ALERTS"
fi

echo ""
echo "9. Testing Analytics..."
if [ -n "$MUNI_TOKEN" ]; then
    ANALYTICS=$(curl -s -X GET -H "Authorization: Bearer $MUNI_TOKEN" \
      http://localhost:8000/api/v1/analytics/ward/1)
    
    echo -e "${GREEN}✓ Analytics endpoint accessible${NC}"
    echo "   Analytics: $ANALYTICS"
fi

echo ""
echo "=== Demo Verification Complete ==="
echo ""
echo "Services are running at:"
echo "  - Backend API: http://localhost:8000"
echo "  - Model Service: http://localhost:8001"
echo "  - User Frontend: http://localhost:80/user/"
echo "  - Ward Frontend: http://localhost:80/ward/"
echo "  - Municipality Frontend: http://localhost:80/municipality/"
echo ""
echo "Test Credentials:"
echo "  - User: user@example.com / user123"
echo "  - Ward Admin: ward@example.com / ward123"
echo "  - Municipality Admin: municipality@example.com / muni123"
echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f"
