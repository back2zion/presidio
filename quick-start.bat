@echo off
chcp 65001 >nul
REM Simple execution script for Windows

echo Korea Expressway PII Removal System - Quick Start
echo.
echo Select an option:
echo 1) Test CPU version (available now)
echo 2) Create offline package
echo 3) Exit
echo.
set /p choice="Select [1-3]: "

if "%choice%"=="1" goto cpu_test
if "%choice%"=="2" goto create_package
if "%choice%"=="3" goto end
goto invalid

:cpu_test
echo Starting CPU version test...
set DOCKER_BUILDKIT=1
docker build -f Dockerfile -t korea-pii-cpu:test .
docker run -d --name pii-test -p 5000:5000 korea-pii-cpu:test
echo.
echo [DONE] Test running!
echo [WEB] Open browser: http://localhost:5000
echo.
echo To stop: docker stop pii-test ^&^& docker rm pii-test
pause
goto end

:create_package
echo Creating offline package...

REM Build CPU version (with BuildKit)
set DOCKER_BUILDKIT=1
docker build -f Dockerfile -t korea-pii-cpu:v2.0.0 .
docker save -o korea-pii-cpu.tar korea-pii-cpu:v2.0.0

REM Compress using PowerShell
powershell -command "Compress-Archive -Path 'korea-pii-cpu.tar' -DestinationPath 'korea-pii-cpu.zip'"
del korea-pii-cpu.tar

echo.
echo [DONE] Package created!
echo [FILE] korea-pii-cpu.zip
echo [INFO] Extract in internal network and run: docker load -i korea-pii-cpu.tar
pause
goto end

:invalid
echo Invalid selection.
pause

:end
exit /b