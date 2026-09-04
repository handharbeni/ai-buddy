@echo off
cd /d "C:\Users\Administrator\Documents\DBI-DB\backend"
"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause