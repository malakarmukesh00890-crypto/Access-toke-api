#!/bin/bash
echo "========================================"
echo "  EAT-AXIS-JWT - Server Start Ho Raha Hai"
echo "========================================"
echo ""
echo "Libraries install ho rahi hain..."
pip install -r requirements.txt
echo ""
echo "Server start ho raha hai..."
echo ""
echo "Website: http://localhost:8000/website"
echo "API:     http://localhost:8000/"
echo ""
python eat.py
