@echo off
REM รันแบบ dev: ติดตั้ง dependency (ครั้งแรก) แล้วเปิดแอปถาดระบบ
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% -c "import pystray, PIL, requests" 2>nul || %PY% -m pip install -r requirements.txt
start "" %PY%w -m claude_usage_tray
