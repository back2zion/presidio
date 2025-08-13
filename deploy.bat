@echo off
REM 한국도로공사 민원 개인정보 제거 시스템 배포 스크립트 (Windows)

echo 🚀 한국도로공사 민원 개인정보 제거 시스템 배포 시작

REM 변수 설정
set IMAGE_NAME=korea-expressway-pii-remover
set IMAGE_TAG=v1.0.0
set CONTAINER_NAME=korea-expressway-pii-remover
set EXPORT_FILE=%IMAGE_NAME%-%IMAGE_TAG%.tar

REM 1단계: Docker 이미지 빌드
echo 📦 Docker 이미지 빌드 중...
docker build -t %IMAGE_NAME%:%IMAGE_TAG% .
docker tag %IMAGE_NAME%:%IMAGE_TAG% %IMAGE_NAME%:latest

REM 2단계: 이미지 압축 및 내보내기
echo 💾 Docker 이미지 내보내기 중...
docker save -o %EXPORT_FILE% %IMAGE_NAME%:%IMAGE_TAG%

REM 3단계: 압축
powershell "Compress-Archive -Path '%EXPORT_FILE%' -DestinationPath '%EXPORT_FILE%.zip' -Force"
del %EXPORT_FILE%

echo ✅ 배포 파일 생성 완료:
echo    - 파일명: %EXPORT_FILE%.zip

echo.
echo 📋 내부망 배포 절차:
echo 1. %EXPORT_FILE%.zip 파일을 내부망 서버로 전송
echo 2. 압축 해제 후 다음 명령어 실행:
echo    docker load -i %EXPORT_FILE%
echo    docker run -d --name %CONTAINER_NAME% -p 5000:5000 %IMAGE_NAME%:%IMAGE_TAG%
echo.
echo 🌐 접속 URL: http://내부서버IP:5000
echo.
echo 🎉 배포 파일 준비 완료!

pause
