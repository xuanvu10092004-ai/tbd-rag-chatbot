@echo off
title TBD RAG Chatbot - Backend
echo Dang khoi dong Backend (FastAPI)...
cd backend
call venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8001
pause
