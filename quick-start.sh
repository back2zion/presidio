#!/bin/bash
# 간단 실행 스크립트 (GPU 없어도 가능)

echo "🚀 한국도로공사 PII 제거 시스템 - 빠른 시작"
echo ""
echo "선택하세요:"
echo "1) CPU 버전 테스트 (지금 바로 가능)"
echo "2) 내부망용 패키지 생성 (Docker만 있으면 가능)"
echo "3) 종료"
echo ""
read -p "선택 [1-3]: " choice

case $choice in
    1)
        echo "🖥️ CPU 버전 테스트 시작..."
        
        # CPU Docker 이미지 빌드
        docker build -f Dockerfile -t korea-pii-cpu:test .
        
        # 실행
        docker run -d --name pii-test -p 5000:5000 korea-pii-cpu:test
        
        echo "✅ 실행 완료!"
        echo "🌐 브라우저에서 접속: http://localhost:5000"
        echo ""
        echo "종료하려면: docker stop pii-test && docker rm pii-test"
        ;;
        
    2)
        echo "📦 내부망용 패키지 생성..."
        
        # CPU 버전 빌드
        docker build -f Dockerfile -t korea-pii-cpu:v2.0.0 .
        
        # GPU 버전 빌드 (실행은 안되지만 이미지는 생성 가능)
        echo "GPU 이미지도 생성하시겠습니까? (y/n)"
        read -p "선택: " gpu_choice
        
        if [ "$gpu_choice" = "y" ]; then
            docker build -f Dockerfile.gpu -t korea-pii-gpu:v2.0.0 .
            docker save -o korea-pii-gpu.tar korea-pii-gpu:v2.0.0
            gzip korea-pii-gpu.tar
            echo "✅ GPU 이미지 생성: korea-pii-gpu.tar.gz"
        fi
        
        # CPU 이미지 저장
        docker save -o korea-pii-cpu.tar korea-pii-cpu:v2.0.0
        gzip korea-pii-cpu.tar
        
        # 간단 설치 스크립트 생성
        cat > install.sh << 'INSTALL'
#!/bin/bash
# 내부망 설치 스크립트

echo "🚀 PII 제거 시스템 설치"

# Docker 이미지 로드
if [ -f "korea-pii-gpu.tar.gz" ] && nvidia-smi &>/dev/null; then
    echo "GPU 버전 설치 중..."
    gunzip korea-pii-gpu.tar.gz
    docker load -i korea-pii-gpu.tar
    docker run -d --name korea-pii --gpus all -p 5000:5000 korea-pii-gpu:v2.0.0
else
    echo "CPU 버전 설치 중..."
    gunzip korea-pii-cpu.tar.gz
    docker load -i korea-pii-cpu.tar
    docker run -d --name korea-pii -p 5000:5000 korea-pii-cpu:v2.0.0
fi

echo "✅ 설치 완료! http://localhost:5000 접속"
INSTALL
        
        chmod +x install.sh
        
        # 패키징
        mkdir -p package
        mv korea-pii-*.tar.gz package/ 2>/dev/null
        mv install.sh package/
        cp remover.py package/
        cp -r templates package/
        cp requirements.txt package/
        
        tar -czf korea-pii-package.tar.gz package/
        rm -rf package
        
        echo ""
        echo "✅ 패키지 생성 완료!"
        echo "📦 파일: korea-pii-package.tar.gz"
        echo "📋 내부망 반입 후 압축 해제하고 install.sh 실행"
        ;;
        
    3)
        echo "종료합니다."
        exit 0
        ;;
        
    *)
        echo "잘못된 선택입니다."
        exit 1
        ;;
esac