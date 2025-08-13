@echo off
REM 간단 실행 스크립트 (Windows용)

echo 🚀 한국도로공사 PII 제거 시스템 - 빠른 시작
echo.
echo 선택하세요:
echo 1) CPU 버전 테스트 (지금 바로 가능)
echo 2) 내부망용 패키지 생성
echo 3) 종료
echo.
set /p choice="선택 [1-3]: "

if "%choice%"=="1" goto cpu_test
if "%choice%"=="2" goto create_package
if "%choice%"=="3" goto end
goto invalid

:cpu_test
echo 🖥️ CPU 버전 테스트 시작...
docker build -f Dockerfile -t korea-pii-cpu:test .
docker run -d --name pii-test -p 5000:5000 korea-pii-cpu:test
echo.
echo ✅ 실행 완료!
echo 🌐 브라우저에서 접속: http://localhost:5000
echo.
echo 종료하려면: docker stop pii-test ^&^& docker rm pii-test
pause
goto end

:create_package
echo 📦 내부망용 패키지 생성...

REM CPU 버전 빌드
docker build -f Dockerfile -t korea-pii-cpu:v2.0.0 .
docker save -o korea-pii-cpu.tar korea-pii-cpu:v2.0.0

REM 압축 (PowerShell 사용)
powershell -command "Compress-Archive -Path 'korea-pii-cpu.tar' -DestinationPath 'korea-pii-cpu.zip'"
del korea-pii-cpu.tar

echo.
echo ✅ 패키지 생성 완료!
echo 📦 파일: korea-pii-cpu.zip
echo 📋 내부망에서 압축 해제 후 docker load -i korea-pii-cpu.tar
pause
goto end

:invalid
echo 잘못된 선택입니다.
pause

:end
exit /b