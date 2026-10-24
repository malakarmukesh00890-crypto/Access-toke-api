========================================
  EAT-AXIS-JWT - Complete Setup Guide
========================================

FOLDER STRUCTURE:
-----------------
EAT-AXIS-FULL/
├── eat.py              ← Backend Flask API
├── my_pb2.py           ← Protobuf file
├── output_pb2.py       ← Protobuf file
├── requirements.txt    ← Libraries list
├── vercel.json         ← Vercel deploy config
├── START_KARO.bat      ← Windows start script
├── start.sh            ← Linux/Mac start script
└── static/
    └── index.html      ← Website (UI)

KAISE CHALAYEIN (Windows):
--------------------------
1. Python install hona chahiye (python.org se)
2. "START_KARO.bat" pe double click karo
3. Browser mein yeh URL kholo:
   http://localhost:8000/website

KAISE CHALAYEIN (Linux/Mac):
-----------------------------
1. Terminal mein folder open karo
2. ./start.sh run karo
3. Browser mein yeh URL kholo:
   http://localhost:8000/website

LOGIN KEY:
----------
FF-AXIS-2025

(Login screen pe bhi dikhai deti hai)

ENDPOINTS:
----------
/eat-to-access  → EAT se Access Token
/eat-to-jwt     → EAT se JWT Token
/platforms      → Platforms list
/check-expiry   → Timestamp expiry check
/               → API Status

Credits: @btcXbitcoin | @mukeshhhhhk
