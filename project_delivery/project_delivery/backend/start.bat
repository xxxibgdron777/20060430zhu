@echo off
cd /d "%~dp0"
echo Starting server...
python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=80)"
pause
