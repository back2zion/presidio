# 한국도로공사 민원 개인정보 제거 시스템 - Rocky Linux 8.1 전용 설치 가이드

## 📋 시스템 요구사항 (Rocky Linux 8.1)

### 하드웨어 요구사항
- **CPU**: 4 Core 이상 (권장: 8 Core)
- **메모리**: 
  - CPU 모드: 8GB 이상
  - GPU 모드: 16GB 이상 (권장: 32GB)
- **GPU**: NVIDIA H100 (7번 GPU 슬롯 사용)
- **디스크**: 50GB 이상 여유 공간
- **네트워크**: 내부망 접속

### 소프트웨어 요구사항
- **OS**: Rocky Linux 8.1
- **Docker**: 20.10.0 이상
- **NVIDIA Driver**: 525.60.13 이상 (H100 지원)
- **NVIDIA Container Toolkit**: 1.14.0 이상

## 🚀 설치 절차

### 사전 준비 (관리자 권한 필요)

#### 1단계: 시스템 업데이트
```bash
sudo dnf update -y
sudo dnf install -y wget curl tar gzip
```

#### 2단계: NVIDIA 드라이버 확인 (H100용)
```bash
# NVIDIA 드라이버 상태 확인
nvidia-smi

# 드라이버가 없거나 버전이 낮은 경우
sudo dnf install -y kernel-devel kernel-headers
wget https://us.download.nvidia.com/tesla/525.60.13/NVIDIA-Linux-x86_64-525.60.13.run
sudo bash NVIDIA-Linux-x86_64-525.60.13.run

# 재부팅 후 확인
sudo reboot
nvidia-smi
```

#### 3단계: Docker 설치 (Rocky Linux 8.1)
```bash
# Docker 저장소 추가
sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo

# Docker 설치
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# Docker 설치 확인
docker --version
```

#### 4단계: NVIDIA Container Toolkit 설치
```bash
# NVIDIA 저장소 추가
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Container Toolkit 설치
sudo dnf install -y nvidia-container-toolkit

# Docker 재시작
sudo systemctl restart docker

# GPU 지원 확인
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
```

### 오프라인 패키지 설치

#### 1단계: 패키지 파일 복사
오프라인 패키지를 내부망 서버로 복사:
```bash
# 예시: USB 마운트 후 복사
sudo mkdir -p /mnt/usb
sudo mount /dev/sdb1 /mnt/usb
cp -r /mnt/usb/korea-pii-remover-offline-v2.0.0 ~/
cd ~/korea-pii-remover-offline-v2.0.0
```

#### 2단계: 자동 설치 실행
```bash
# 설치 스크립트 실행 권한 부여
chmod +x install-offline.sh

# 설치 실행
./install-offline.sh
```

#### 3단계: 수동 설치 (선택사항)
```bash
# GPU 사용 가능한 경우
gunzip korea-pii-remover-gpu-v2.0.0.tar.gz
docker load -i korea-pii-remover-gpu-v2.0.0.tar

# 데이터 디렉토리 생성
mkdir -p ./data

# H100 GPU 지정하여 컨테이너 실행 (7번 GPU)
docker run -d \
  --name korea-pii-remover \
  --gpus '"device=7"' \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  --shm-size=4g \
  -e CUDA_VISIBLE_DEVICES=7 \
  korea-pii-remover-gpu:v2.0.0
```

### GPU 메모리 최적화 (H100 전용)

#### H100 GPU 설정 확인
```bash
# 7번 GPU 상태 확인
nvidia-smi -i 7

# GPU 메모리 사용량 모니터링
watch -n 1 "nvidia-smi -i 7 --query-gpu=memory.used,memory.total,utilization.gpu --format=csv"
```

#### 고급 설정 (선택사항)
```bash
# H100 최적화된 컨테이너 실행
docker run -d \
  --name korea-pii-remover \
  --gpus '"device=7"' \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  --shm-size=8g \
  --memory=32g \
  --cpus=8 \
  -e CUDA_VISIBLE_DEVICES=7 \
  -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048 \
  -e CUDA_MEMORY_FRACTION=0.9 \
  korea-pii-remover-gpu:v2.0.0
```

## 🌐 접속 및 사용

### 웹 인터페이스 접속
```bash
# 서버 IP 확인
hostname -I

# 브라우저 접속
# http://서버IP:5000
```

### 서비스 상태 확인
```bash
# 컨테이너 상태 확인
docker ps -a

# 로그 확인
docker logs -f korea-pii-remover

# GPU 사용량 확인
nvidia-smi -i 7

# 포트 리스닝 확인
sudo netstat -tlnp | grep :5000
```

## 🔧 관리 명령어

### 컨테이너 관리
```bash
# 컨테이너 중지
docker stop korea-pii-remover

# 컨테이너 시작
docker start korea-pii-remover

# 컨테이너 재시작
docker restart korea-pii-remover

# 컨테이너 삭제
docker rm -f korea-pii-remover
```

### 성능 모니터링
```bash
# 실시간 GPU 모니터링
watch -n 1 nvidia-smi -i 7

# 컨테이너 리소스 사용량
docker stats korea-pii-remover

# 시스템 리소스 확인
htop
```

### 로그 관리
```bash
# 실시간 로그 확인
docker logs -f korea-pii-remover

# 로그 파일 크기 제한 설정
docker update --log-opt max-size=100m --log-opt max-file=3 korea-pii-remover
```

## 🆘 문제 해결 (Rocky Linux 8.1)

### Docker 관련 문제

1. **SELinux 문제**
   ```bash
   # SELinux 상태 확인
   sestatus
   
   # 필요시 SELinux 설정 조정
   sudo setsebool -P container_manage_cgroup on
   ```

2. **방화벽 설정**
   ```bash
   # 포트 5000 허용
   sudo firewall-cmd --permanent --add-port=5000/tcp
   sudo firewall-cmd --reload
   ```

3. **cgroup 문제**
   ```bash
   # cgroup v2 확인 및 설정
   sudo grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"
   ```

### GPU 관련 문제

1. **NVIDIA 드라이버 문제**
   ```bash
   # 드라이버 재설치
   sudo dnf remove -y nvidia-*
   sudo bash NVIDIA-Linux-x86_64-525.60.13.run --uninstall
   sudo bash NVIDIA-Linux-x86_64-525.60.13.run
   ```

2. **Container Toolkit 문제**
   ```bash
   # 재설치
   sudo dnf remove -y nvidia-container-toolkit
   sudo dnf install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

3. **H100 GPU 인식 문제**
   ```bash
   # GPU 상태 확인
   lspci | grep NVIDIA
   nvidia-smi -L
   
   # 드라이버 호환성 확인
   nvidia-smi --query-gpu=driver_version --format=csv
   ```

## 📞 기술 지원

### 로그 수집 명령어
```bash
# 시스템 정보 수집
{
    echo "=== 시스템 정보 ==="
    cat /etc/rocky-release
    uname -a
    
    echo -e "\n=== GPU 정보 ==="
    nvidia-smi
    
    echo -e "\n=== Docker 정보 ==="
    docker version
    docker info
    
    echo -e "\n=== 컨테이너 상태 ==="
    docker ps -a
    
    echo -e "\n=== 컨테이너 로그 ==="
    docker logs --tail 100 korea-pii-remover
    
} > system-info-$(date +%Y%m%d_%H%M%S).txt
```

---

**⚠️ Rocky Linux 8.1 주의사항**
- dnf 패키지 매니저 사용 필수
- SELinux 설정 확인 필요
- 방화벽 포트 설정 필수
- H100 GPU는 최신 NVIDIA 드라이버 필요 (525.60.13+)