# Korea Expressway PII Removal System - Quick Start (PowerShell)
# Set UTF-8 encoding
$OutputEncoding = [Console]::OutputEncoding = [Console]::InputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Korea Expressway PII Removal System - Quick Start" -ForegroundColor Cyan
Write-Host ""
Write-Host "Select an option:" -ForegroundColor Yellow
Write-Host "1) Test CPU version (available now)"
Write-Host "2) Create offline package"
Write-Host "3) Exit"
Write-Host ""

$choice = Read-Host "Select [1-3]"

switch ($choice) {
    1 {
        Write-Host "`n[CPU] Starting CPU version test..." -ForegroundColor Green
        
        # Docker 이미지 빌드 (BuildKit 사용)
        $env:DOCKER_BUILDKIT=1
        docker build -f Dockerfile -t korea-pii-cpu:test .
        
        # 기존 컨테이너 정리
        docker stop pii-test 2>$null
        docker rm pii-test 2>$null
        
        # 컨테이너 실행
        docker run -d --name pii-test -p 5000:5000 korea-pii-cpu:test
        
        Write-Host "`n[DONE] Test running!" -ForegroundColor Green
        Write-Host "[WEB] Open browser: " -NoNewline
        Write-Host "http://localhost:5000" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To stop: " -NoNewline -ForegroundColor Yellow
        Write-Host "docker stop pii-test; docker rm pii-test"
        
        # Auto open browser (optional)
        $openBrowser = Read-Host "`nOpen browser automatically? (y/n)"
        if ($openBrowser -eq 'y') {
            Start-Process "http://localhost:5000"
        }
    }
    
    2 {
        Write-Host "`n[PACKAGE] Creating offline package..." -ForegroundColor Green
        
        # Build CPU version (with BuildKit)
        Write-Host "Building CPU version Docker image..." -ForegroundColor Yellow
        $env:DOCKER_BUILDKIT=1
        docker build -f Dockerfile -t korea-pii-cpu:v2.0.0 .
        
        # GPU version option
        $buildGpu = Read-Host "`nBuild GPU version too? (y/n)"
        
        if ($buildGpu -eq 'y') {
            Write-Host "Building GPU version Docker image..." -ForegroundColor Yellow
            $env:DOCKER_BUILDKIT=1
            docker build -f Dockerfile.gpu -t korea-pii-gpu:v2.0.0 .
            
            Write-Host "Saving GPU image..." -ForegroundColor Yellow
            docker save -o korea-pii-gpu.tar korea-pii-gpu:v2.0.0
            Compress-Archive -Path "korea-pii-gpu.tar" -DestinationPath "korea-pii-gpu.zip" -Force
            Remove-Item "korea-pii-gpu.tar"
            Write-Host "[DONE] GPU image created: korea-pii-gpu.zip" -ForegroundColor Green
        }
        
        # Save CPU image
        Write-Host "Saving CPU image..." -ForegroundColor Yellow
        docker save -o korea-pii-cpu.tar korea-pii-cpu:v2.0.0
        Compress-Archive -Path "korea-pii-cpu.tar" -DestinationPath "korea-pii-cpu.zip" -Force
        Remove-Item "korea-pii-cpu.tar"
        
        # 설치 스크립트 생성
        @"
@echo off
echo Korea Expressway PII Removal System - Installation
echo.

REM Extract and load Docker image
powershell -command "Expand-Archive -Path 'korea-pii-cpu.zip' -DestinationPath '.' -Force"
docker load -i korea-pii-cpu.tar

REM Run container
docker run -d --name korea-pii -p 5000:5000 korea-pii-cpu:v2.0.0

echo.
echo [DONE] Installation complete!
echo [WEB] Access: http://localhost:5000
pause
"@ | Out-File -FilePath "install.bat" -Encoding UTF8
        
        # Create package
        Write-Host "`nOrganizing package files..." -ForegroundColor Yellow
        
        $packageFiles = @(
            "korea-pii-cpu.zip",
            "install.bat",
            "requirements.txt",
            "remover.py"
        )
        
        # 최종 패키지 압축
        Compress-Archive -Path $packageFiles -DestinationPath "korea-pii-package.zip" -Force
        
        Write-Host "`n[DONE] Package created!" -ForegroundColor Green
        Write-Host "[FILE] " -NoNewline
        Write-Host "korea-pii-package.zip" -ForegroundColor Cyan
        Write-Host "[INFO] Extract in internal network and run install.bat" -ForegroundColor Yellow
        
        # Show file size
        $fileInfo = Get-Item "korea-pii-package.zip"
        $sizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
        Write-Host "[SIZE] $sizeMB MB" -ForegroundColor Gray
    }
    
    3 {
        Write-Host "Exiting..." -ForegroundColor Gray
        exit
    }
    
    default {
        Write-Host "Invalid selection." -ForegroundColor Red
    }
}

Write-Host "`nPress any key to continue..." -ForegroundColor Gray
Read-Host