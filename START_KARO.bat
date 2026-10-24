@echo off
echo ========================================
echo   EAT-AXIS-JWT - Server Start Ho Raha Hai
echo ========================================
echo.
echo Step 1: Libraries install ho rahi hain...
pip install -r requirements.txt
echo.
echo Step 2: Server start ho raha hai...
echo.
echo Website: http://localhost:8000/website
echo API:     http://localhost:8000/
echo.
echo Band karne ke liye Ctrl+C dabao
echo ========================================
python eat.py
pause
