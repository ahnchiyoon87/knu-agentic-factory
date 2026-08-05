@echo off
chcp 65001 > nul
title K-정밀 팩토리 시뮬레이터
cd /d "%~dp0"

echo ==========================================================
echo   K-정밀 팩토리 시뮬레이터
echo   이 창을 닫으면 시뮬레이터가 꺼집니다. 켜 두십시오.
echo ==========================================================
echo.

rem 이미 떠 있으면 브라우저만 연다
curl -s -m 2 http://127.0.0.1:8000/api/v1/health > nul 2>&1
if %errorlevel%==0 (
    echo 서버가 이미 떠 있습니다. 화면만 엽니다.
    goto :open
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
start "" /b cmd /c "python -m uvicorn server.app.main:app --host 0.0.0.0 --port 8000 --workers 1"

echo 서버를 켜는 중...
:wait
timeout /t 2 /nobreak > nul
curl -s -m 2 http://127.0.0.1:8000/api/v1/health > nul 2>&1
if not %errorlevel%==0 goto :wait

:open
echo.
echo 준비 완료. 브라우저를 엽니다.
echo    강사 콘솔   http://127.0.0.1:8000/console
echo    2D 공장 뷰  http://127.0.0.1:8000/view?tenant=S01
echo.
echo 학생에게 알려줄 주소는 이 PC 의 IP 입니다:
ipconfig | findstr /c:"IPv4"
echo.
start "" http://127.0.0.1:8000/console
start "" "http://127.0.0.1:8000/view?tenant=S01"

echo 이 창은 서버 로그입니다. 닫지 마십시오.
pause > nul
