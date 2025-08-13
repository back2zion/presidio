#!/bin/bash
# H100 GPU 환경 최적화 스크립트 (Rocky Linux 8.1)

set -e

echo "🚀 H100 GPU 환경 최적화 설정 (7번 GPU 슬롯)"

# H100 GPU 확인
check_h100_gpu() {
    echo "🔍 H100 GPU 확인 중..."
    
    if ! command -v nvidia-smi &> /dev/null; then
        echo "❌ nvidia-smi가 설치되지 않았습니다."
        exit 1
    fi
    
    # 7번 GPU 슬롯 확인
    if nvidia-smi -i 7 &> /dev/null; then
        GPU_NAME=$(nvidia-smi -i 7 --query-gpu=name --format=csv,noheader)
        if [[ $GPU_NAME == *"H100"* ]]; then
            echo "✅ H100 GPU (슬롯 7) 감지됨: $GPU_NAME"
            return 0
        else
            echo "⚠️ 슬롯 7에 H100이 아닌 GPU 감지됨: $GPU_NAME"
            echo "   계속 진행합니다."
        fi
    else
        echo "❌ 7번 GPU 슬롯을 찾을 수 없습니다."
        echo "   사용 가능한 GPU 목록:"
        nvidia-smi -L
        exit 1
    fi
}

# GPU 메모리 및 성능 최적화
optimize_gpu_settings() {
    echo "⚙️ GPU 최적화 설정 적용 중..."
    
    # GPU 지속성 모드 활성화 (성능 향상)
    echo "   - GPU 지속성 모드 활성화"
    sudo nvidia-smi -i 7 -pm 1
    
    # GPU 최대 성능 모드 설정
    echo "   - GPU 최대 성능 모드 설정"
    sudo nvidia-smi -i 7 -ac $(nvidia-smi -i 7 --query-gpu=clocks.max.memory,clocks.max.sm --format=csv,noheader,nounits | tr ', ' ',')
    
    # GPU 파워 리밋 최적화 (H100은 700W)
    echo "   - GPU 파워 리밋 설정"
    sudo nvidia-smi -i 7 -pl 700
    
    echo "✅ GPU 최적화 설정 완료"
}

# Docker 컨테이너 GPU 메모리 최적화
optimize_container_settings() {
    echo "🐳 Docker 컨테이너 GPU 설정 최적화..."
    
    # GPU 메모리 정보 확인
    GPU_MEMORY=$(nvidia-smi -i 7 --query-gpu=memory.total --format=csv,noheader,nounits)
    echo "   GPU 총 메모리: ${GPU_MEMORY}MB"
    
    # 메모리 사용량 계산 (90% 사용 권장)
    MEMORY_LIMIT=$((GPU_MEMORY * 90 / 100))
    echo "   권장 메모리 사용량: ${MEMORY_LIMIT}MB"
    
    # 컨테이너별 최적 설정 생성
    cat > gpu-optimized.env << EOF
# H100 GPU 최적화 환경 변수
CUDA_VISIBLE_DEVICES=7
NVIDIA_VISIBLE_DEVICES=7
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048,roundup_power2_divisions:16
CUDA_MEMORY_FRACTION=0.9
TORCH_CUDA_ARCH_LIST=9.0
CUDA_LAUNCH_BLOCKING=1
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
TOKENIZERS_PARALLELISM=true
OMP_NUM_THREADS=8
CUDA_DEVICE_ORDER=PCI_BUS_ID
EOF

    echo "✅ GPU 최적화 환경 파일 생성: gpu-optimized.env"
}

# 시스템 최적화
optimize_system() {
    echo "🔧 시스템 최적화 설정..."
    
    # CPU Governor를 performance로 설정
    echo "   - CPU 성능 모드 설정"
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
    
    # GPU 관련 커널 모듈 로드 확인
    echo "   - NVIDIA 커널 모듈 확인"
    sudo modprobe nvidia
    sudo modprobe nvidia-drm
    sudo modprobe nvidia-uvm
    
    # 스와프 최소화 (GPU 메모리 사용 최적화)
    echo "   - 스와프 사용 최소화"
    echo 10 | sudo tee /proc/sys/vm/swappiness > /dev/null
    
    echo "✅ 시스템 최적화 완료"
}

# 모니터링 스크립트 생성
create_monitoring_script() {
    echo "📊 모니터링 스크립트 생성..."
    
    cat > monitor-h100.sh << 'EOF'
#!/bin/bash
# H100 GPU 실시간 모니터링 스크립트

echo "🖥️ H100 GPU (슬롯 7) 실시간 모니터링"
echo "   종료하려면 Ctrl+C를 누르세요"
echo ""

while true; do
    clear
    echo "=== H100 GPU 상태 ($(date)) ==="
    
    # GPU 기본 정보
    nvidia-smi -i 7 --query-gpu=name,temperature.gpu,power.draw,memory.used,memory.total,utilization.gpu,utilization.memory --format=csv
    
    echo ""
    echo "=== 컨테이너 상태 ==="
    docker stats --no-stream korea-pii-remover 2>/dev/null || echo "컨테이너가 실행중이지 않습니다."
    
    echo ""
    echo "=== 시스템 리소스 ==="
    echo "CPU 사용률: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')"
    echo "메모리 사용률: $(free | grep Mem | awk '{printf("%.1f%%"), $3/$2 * 100.0}')"
    
    sleep 2
done
EOF
    
    chmod +x monitor-h100.sh
    echo "✅ 모니터링 스크립트 생성: ./monitor-h100.sh"
}

# 벤치마크 스크립트 생성
create_benchmark_script() {
    echo "🏃 벤치마크 스크립트 생성..."
    
    cat > benchmark-h100.sh << 'EOF'
#!/bin/bash
# H100 GPU 성능 테스트 스크립트

echo "🧪 H100 GPU 성능 테스트 시작"

echo "1. GPU 메모리 테스트"
docker run --rm --gpus '"device=7"' nvidia/cuda:12.1-devel-ubuntu22.04 nvidia-smi -i 0

echo "2. CUDA 성능 테스트"
docker run --rm --gpus '"device=7"' nvidia/cuda:12.1-devel-ubuntu22.04 /usr/local/cuda/extras/demo_suite/deviceQuery

echo "3. 간단한 행렬 연산 테스트"
docker run --rm --gpus '"device=7"' nvidia/cuda:12.1-devel-ubuntu22.04 bash -c "
cd /usr/local/cuda/samples/1_Utilities/deviceQuery && make && ./deviceQuery
"

echo "✅ 성능 테스트 완료"
EOF
    
    chmod +x benchmark-h100.sh
    echo "✅ 벤치마크 스크립트 생성: ./benchmark-h100.sh"
}

# 메인 실행
main() {
    echo "🚀 H100 GPU 최적화 시작..."
    
    # Root 권한 확인
    if [[ $EUID -ne 0 ]]; then
        echo "⚠️ 일부 최적화는 sudo 권한이 필요합니다."
    fi
    
    check_h100_gpu
    optimize_gpu_settings
    optimize_container_settings
    optimize_system
    create_monitoring_script
    create_benchmark_script
    
    echo ""
    echo "🎉 H100 GPU 최적화 완료!"
    echo ""
    echo "📋 생성된 파일:"
    echo "   - gpu-optimized.env: 컨테이너 환경 변수"
    echo "   - monitor-h100.sh: GPU 모니터링 스크립트"
    echo "   - benchmark-h100.sh: 성능 테스트 스크립트"
    echo ""
    echo "🚀 컨테이너 실행 예시:"
    echo "   docker run -d --name korea-pii-remover --gpus '\"device=7\"' --env-file gpu-optimized.env -p 5000:5000 korea-pii-remover-gpu:v2.0.0"
    echo ""
    echo "📊 모니터링 시작:"
    echo "   ./monitor-h100.sh"
}

# 스크립트 실행
main "$@"