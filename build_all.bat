@echo off
REM สร้าง .exe แล้วห่อเป็น installer wizard ในคำสั่งเดียว
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)

echo [1/3] ติดตั้ง dependency...
%PY% -m pip install -q -r requirements.txt pyinstaller || goto :err

echo [2/3] build .exe ด้วย PyInstaller...
%PY% build.py || goto :err

echo [3/3] สร้าง installer ด้วย Inno Setup...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo   ** ไม่พบ Inno Setup — ได้เฉพาะ dist\ClaudeUsageTray.exe
  echo   ** ดาวน์โหลด: https://jrsoftware.org/isdl.php แล้วรัน build_all.bat ใหม่
  goto :done
)
%ISCC% installer.iss || goto :err
echo.
echo เสร็จ! installer อยู่ที่: dist_installer\ClaudeUsageTray-Setup.exe

:done
echo.
echo ไฟล์พร้อมแจก:
echo   - แบบ portable : dist\ClaudeUsageTray.exe
echo   - แบบ installer: dist_installer\ClaudeUsageTray-Setup.exe
pause
exit /b 0

:err
echo.
echo เกิดข้อผิดพลาด ดู log ด้านบน
pause
exit /b 1
