@echo off
REM Run backend with uvicorn (Windows)
uvicorn app.main:app --host 0.0.0.0 --port 8000
