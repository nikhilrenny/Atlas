@echo off
title Atlas Launcher

cd /d "D:\Projects\atlas\backend"
start "Atlas Backend" cmd /k "venv\Scripts\activate && uvicorn app.main:app --port 8765"

cd /d "D:\Projects\atlas\frontend"
start "Atlas Frontend" cmd /k "npm run dev"

timeout /t 4 /nobreak >nul
start http://localhost:5173
