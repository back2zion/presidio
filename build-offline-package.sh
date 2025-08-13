#!/bin/bash
# 완전한 오프라인 패키지 생성 스크립트 (내부망 반입용)

set -e

echo "🚀 한국도로공사 PII 제거 시스템 - 완전한 오프라인 패키지 생성"

# 변수 설정
VERSION="v2.0.0"
CPU_IMAGE="korea-pii-remover-cpu"
GPU_IMAGE="korea-pii-remover-gpu"
PACKAGE_NAME="korea-pii-remover-offline-${VERSION}"
BUILD_DIR="build-${VERSION}"

# 빌드 디렉토리 생성
mkdir -p ${BUILD_DIR}
cd ${BUILD_DIR}

echo "📦 1단계: 모델 다운로드"
if [ ! -d "../models" ]; then
    echo "   모델 다운로드 중..."
    cd ..
    chmod +x download-models.sh
    ./download-models.sh
    cd ${BUILD_DIR}
else
    echo "   ✅ 모델이 이미 존재합니다."
fi

echo "🐳 2단계: Docker 이미지 빌드"

# CPU 버전 빌드
echo "   CPU 버전 빌드 중..."
docker build -f ../Dockerfile -t ${CPU_IMAGE}:${VERSION} ..
docker tag ${CPU_IMAGE}:${VERSION} ${CPU_IMAGE}:latest

# GPU 버전 빌드
echo "   GPU 버전 빌드 중..."
docker build -f ../Dockerfile.gpu -t ${GPU_IMAGE}:${VERSION} ..
docker tag ${GPU_IMAGE}:${VERSION} ${GPU_IMAGE}:latest

echo "💾 3단계: Docker 이미지 내보내기"
docker save -o ${CPU_IMAGE}-${VERSION}.tar ${CPU_IMAGE}:${VERSION}
docker save -o ${GPU_IMAGE}-${VERSION}.tar ${GPU_IMAGE}:${VERSION}

echo "🗜️ 4단계: 압축"
gzip ${CPU_IMAGE}-${VERSION}.tar
gzip ${GPU_IMAGE}-${VERSION}.tar

echo "📋 5단계: 설치 파일 준비"
cp ../docker-compose-pii.yml .
cp ../INSTALL_GUIDE.md .
cp ../README_DEPLOYMENT.md .

# 내부망 설치 스크립트 생성 (Rocky Linux 8.1 최적화)
cat > install-offline.sh << 'EOF'
#!/bin/bash
# 내부망 설치 스크립트 (Rocky Linux 8.1 지원)

set -e

VERSION="v2.0.0"
CPU_IMAGE="korea-pii-remover-cpu"
GPU_IMAGE="korea-pii-remover-gpu"

echo "🚀 한국도로공사 PII 제거 시스템 내부망 설치 (Rocky Linux 8.1)"

# Rocky Linux 확인
check_rocky_linux() {
    if [ -f /etc/rocky-release ]; then
        ROCKY_VERSION=$(cat /etc/rocky-release | grep -o '[0-9]\+\.[0-9]\+')
        echo "✅ Rocky Linux ${ROCKY_VERSION} 감지됨"
        return 0
    elif [ -f /etc/redhat-release ]; then
        echo "⚠️ RedHat 계열 OS 감지됨"
        return 0
    else
        echo "⚠️ Rocky Linux가 아닙니다. 계속 진행합니다."
        return 1
    fi
}

# Docker 설치 확인 및 설치 (Rocky Linux 8.1용)
install_docker_rocky() {
    if ! command -v docker &> /dev/null; then
        echo "📦 Docker 설치 중 (Rocky Linux 8.1)..."
        
        # Docker 저장소 추가
        sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
        
        # Docker 설치
        sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Docker 서비스 시작
        sudo systemctl start docker
        sudo systemctl enable docker
        
        # 현재 사용자를 docker 그룹에 추가
        sudo usermod -aG docker $USER
        
        echo "⚠️ Docker 그룹 적용을 위해 재로그인이 필요할 수 있습니다."
        echo "   또는 'newgrp docker' 명령어를 실행하세요."
        
        # Docker 서비스 상태 확인
        if ! sudo systemctl is-active --quiet docker; then
            echo "❌ Docker 서비스 시작 실패"
            exit 1
        fi
        
        echo "✅ Docker 설치 완료"
    else
        echo "✅ Docker가 이미 설치되어 있습니다."
    fi
}

# NVIDIA Container Toolkit 설치 (Rocky Linux 8.1용)
install_nvidia_toolkit() {
    if nvidia-smi &> /dev/null; then
        echo "🖥️ NVIDIA Container Toolkit 설치 중..."
        
        # NVIDIA 저장소 추가
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
        sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
        
        # NVIDIA Container Toolkit 설치
        sudo dnf install -y nvidia-container-toolkit
        
        # Docker 재시작
        sudo systemctl restart docker
        
        echo "✅ NVIDIA Container Toolkit 설치 완료"
        return 0
    else
        echo "ℹ️ NVIDIA GPU가 없거나 드라이버가 설치되지 않았습니다."
        return 1
    fi
}

# GPU 지원 확인
check_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            echo "✅ NVIDIA GPU 감지됨"
            return 0
        fi
    fi
    echo "ℹ️ GPU를 사용할 수 없음. CPU 모드로 설치합니다."
    return 1
}

# Docker 이미지 로드
echo "📦 Docker 이미지 로드 중..."

if check_gpu; then
    echo "   GPU 버전 로드 중..."
    gunzip ${GPU_IMAGE}-${VERSION}.tar.gz
    docker load -i ${GPU_IMAGE}-${VERSION}.tar
    IMAGE_NAME=${GPU_IMAGE}
    USE_GPU=true
else
    echo "   CPU 버전 로드 중..."
    gunzip ${CPU_IMAGE}-${VERSION}.tar.gz
    docker load -i ${CPU_IMAGE}-${VERSION}.tar
    IMAGE_NAME=${CPU_IMAGE}
    USE_GPU=false
fi

# 컨테이너 실행
echo "🏃 컨테이너 실행 중..."

# 기존 컨테이너 중지/삭제
docker stop korea-pii-remover 2>/dev/null || true
docker rm korea-pii-remover 2>/dev/null || true

# 데이터 디렉토리 생성
mkdir -p ./data

if [ "$USE_GPU" = true ]; then
    # GPU 버전 실행
    docker run -d \
        --name korea-pii-remover \
        --gpus all \
        -p 5000:5000 \
        -v $(pwd)/data:/app/data \
        --restart unless-stopped \
        --shm-size=2g \
        ${IMAGE_NAME}:${VERSION}
else
    # CPU 버전 실행
    docker run -d \
        --name korea-pii-remover \
        -p 5000:5000 \
        -v $(pwd)/data:/app/data \
        --restart unless-stopped \
        ${IMAGE_NAME}:${VERSION}
fi

echo "✅ 설치 완료!"
echo ""
echo "🌐 접속 정보:"
echo "   URL: http://$(hostname -I | awk '{print $1}'):5000"
echo "   또는: http://localhost:5000"
echo ""
echo "📊 상태 확인:"
echo "   docker logs korea-pii-remover"
echo "   docker ps"
EOF

# Windows 설치 배치 파일
cat > install-offline.bat << 'EOF'
@echo off
setlocal enabledelayedexpansion

set VERSION=v2.0.0
set CPU_IMAGE=korea-pii-remover-cpu
set GPU_IMAGE=korea-pii-remover-gpu

echo 🚀 한국도로공사 PII 제거 시스템 내부망 설치

REM GPU 확인
nvidia-smi >nul 2>&1
if !errorlevel! == 0 (
    echo ✅ NVIDIA GPU 감지됨
    set USE_GPU=true
    set IMAGE_NAME=!GPU_IMAGE!
) else (
    echo ℹ️ GPU를 사용할 수 없음. CPU 모드로 설치합니다.
    set USE_GPU=false
    set IMAGE_NAME=!CPU_IMAGE!
)

echo 📦 Docker 이미지 로드 중...

if !USE_GPU! == true (
    echo    GPU 버전 로드 중...
    powershell -command "Expand-Archive -Path '!GPU_IMAGE!-!VERSION!.tar.gz' -DestinationPath '.'"
    docker load -i !GPU_IMAGE!-!VERSION!.tar
) else (
    echo    CPU 버전 로드 중...
    powershell -command "Expand-Archive -Path '!CPU_IMAGE!-!VERSION!.tar.gz' -DestinationPath '.'"
    docker load -i !CPU_IMAGE!-!VERSION!.tar
)

echo 🏃 컨테이너 실행 중...

REM 기존 컨테이너 정리
docker stop korea-pii-remover 2>nul
docker rm korea-pii-remover 2>nul

REM 데이터 디렉토리 생성
if not exist data mkdir data

REM 컨테이너 실행
if !USE_GPU! == true (
    docker run -d --name korea-pii-remover --gpus all -p 5000:5000 -v %cd%/data:/app/data --restart unless-stopped !IMAGE_NAME!:!VERSION!
) else (
    docker run -d --name korea-pii-remover -p 5000:5000 -v %cd%/data:/app/data --restart unless-stopped !IMAGE_NAME!:!VERSION!
)

echo ✅ 설치 완료!
echo.
echo 🌐 접속: http://localhost:5000
echo 📊 상태 확인: docker logs korea-pii-remover

pause
EOF

chmod +x install-offline.sh

# 패키지 정보 파일 생성
cat > package-info.txt << EOF
# 한국도로공사 민원 개인정보 제거 시스템 ${VERSION}

## 포함 파일
- ${CPU_IMAGE}-${VERSION}.tar.gz: CPU 버전 Docker 이미지
- ${GPU_IMAGE}-${VERSION}.tar.gz: GPU 버전 Docker 이미지 (H100 최적화)
- install-offline.sh: Linux/Mac 설치 스크립트
- install-offline.bat: Windows 설치 스크립트
- docker-compose-pii.yml: Docker Compose 설정
- INSTALL_GUIDE.md: 상세 설치 가이드
- README_DEPLOYMENT.md: 배포 매뉴얼

## 시스템 요구사항
- Docker 20.10+
- CPU 버전: 4GB RAM, 2 CPU Core
- GPU 버전: 8GB GPU VRAM (H100 권장), 8GB RAM, 4 CPU Core

## 설치 방법
1. 전체 패키지를 내부망 서버로 복사
2. Linux/Mac: ./install-offline.sh 실행
   Windows: install-offline.bat 실행
3. 브라우저에서 http://서버IP:5000 접속

패키지 생성일: $(date)
전체 크기: $(du -sh . | cut -f1)
EOF

echo "📊 6단계: 패키지 정보"
echo "✅ 오프라인 패키지 생성 완료!"
echo ""
echo "📁 패키지 위치: $(pwd)"
echo "📦 CPU 이미지: ${CPU_IMAGE}-${VERSION}.tar.gz ($(du -sh ${CPU_IMAGE}-${VERSION}.tar.gz | cut -f1))"
echo "🖥️ GPU 이미지: ${GPU_IMAGE}-${VERSION}.tar.gz ($(du -sh ${GPU_IMAGE}-${VERSION}.tar.gz | cut -f1))"
echo "📄 설치 파일: install-offline.sh, install-offline.bat"
echo "📋 총 크기: $(du -sh . | cut -f1)"
echo ""
echo "🚚 내부망 반입 준비 완료!"

cd ..