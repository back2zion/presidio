# 외부망 테스트 및 패키지 준비 가이드

## 📋 테스트 환경별 준비 방법

### 시나리오 1: GPU가 없는 개발 환경 (현재 상황)

#### 1단계: CPU 버전만 먼저 테스트
```bash
# CPU 버전 Docker 이미지만 빌드
docker build -f Dockerfile -t korea-pii-remover-cpu:test .

# CPU 버전 로컬 테스트
docker run -d --name pii-test -p 5000:5000 korea-pii-remover-cpu:test

# 브라우저에서 테스트
# http://localhost:5000

# 테스트 완료 후 정리
docker stop pii-test
docker rm pii-test
```

#### 2단계: GPU 이미지는 빌드만 수행 (실행 불가)
```bash
# GPU 이미지 빌드 (실행은 불가능하지만 이미지는 생성 가능)
docker build -f Dockerfile.gpu -t korea-pii-remover-gpu:v2.0.0 .

# 빌드된 이미지 확인
docker images | grep korea-pii

# 이미지 저장 (내부망 반입용)
docker save -o korea-pii-remover-gpu.tar korea-pii-remover-gpu:v2.0.0
gzip korea-pii-remover-gpu.tar
```

### 시나리오 2: GPU가 있는 외부망 서버 활용

#### 협력 개발자나 GPU 서버가 있는 경우
```bash
# GPU 서버로 코드 복사
scp -r . gpu-server:/home/user/korea-pii-remover/

# GPU 서버에서 실행
ssh gpu-server
cd /home/user/korea-pii-remover

# GPU 버전 빌드 및 테스트
docker build -f Dockerfile.gpu -t korea-pii-remover-gpu:test .
docker run --gpus all -d --name gpu-test -p 5000:5000 korea-pii-remover-gpu:test

# 테스트 수행
curl http://localhost:5000

# 문제 없으면 이미지 저장
docker save -o korea-pii-remover-gpu.tar korea-pii-remover-gpu:test
gzip korea-pii-remover-gpu.tar
```

### 시나리오 3: 클라우드 GPU 인스턴스 임시 활용

#### AWS/GCP/Azure 등에서 GPU 인스턴스 임시 사용
```bash
# AWS EC2 GPU 인스턴스 예시 (p3.2xlarge - V100 GPU)
# 또는 p4d.24xlarge (A100 GPU) - H100과 유사

# 1. GPU 인스턴스 시작 (1시간만 사용)
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type p3.2xlarge \
  --key-name mykey \
  --security-groups default

# 2. 인스턴스 접속 후 Docker 및 NVIDIA 드라이버 설치
ssh -i mykey.pem ubuntu@<instance-ip>
curl -fsSL https://get.docker.com | sh
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 3. 코드 업로드 및 테스트
# (로컬에서) 
scp -r . ubuntu@<instance-ip>:/home/ubuntu/korea-pii/

# 4. GPU 버전 빌드 및 테스트
cd /home/ubuntu/korea-pii
docker build -f Dockerfile.gpu -t korea-pii-gpu:test .
docker run --gpus all -p 5000:5000 korea-pii-gpu:test

# 5. 테스트 완료 후 이미지 저장
docker save -o korea-pii-gpu.tar korea-pii-gpu:test
gzip korea-pii-gpu.tar

# 6. 로컬로 다운로드
scp ubuntu@<instance-ip>:/home/ubuntu/korea-pii/korea-pii-gpu.tar.gz .

# 7. 인스턴스 종료 (비용 절감)
aws ec2 terminate-instances --instance-ids <instance-id>
```

## 🎯 권장 테스트 순서

### Phase 1: CPU 버전 (GPU 없이 가능)
```bash
# 1. CPU 버전 완전 테스트
./test-cpu-version.sh

# 2. 기능 검증
- 웹 UI 동작 확인
- 파일 업로드 테스트
- PII 제거 기능 확인
- 진행률 표시 확인

# 3. CPU 패키지 생성
docker save -o korea-pii-cpu.tar korea-pii-remover-cpu:v2.0.0
gzip korea-pii-cpu.tar
```

### Phase 2: GPU 이미지 빌드만 (GPU 없이 가능)
```bash
# GPU 이미지 빌드 (실행은 불가)
docker build -f Dockerfile.gpu -t korea-pii-gpu:v2.0.0 .

# 이미지 저장
docker save -o korea-pii-gpu.tar korea-pii-gpu:v2.0.0
gzip korea-pii-gpu.tar
```

### Phase 3: 내부망 반입 전 체크리스트
```bash
# 체크리스트 확인 스크립트
./pre-deployment-check.sh
```

## 📦 최소 반입 패키지 (GPU 없이 준비 가능)

```bash
# 최소 패키지 생성 스크립트
cat > create-minimal-package.sh << 'EOF'
#!/bin/bash
# GPU 없이도 실행 가능한 최소 패키지 생성

echo "📦 최소 반입 패키지 생성 (CPU 버전)"

# CPU 이미지 빌드
docker build -f Dockerfile -t korea-pii-cpu:v2.0.0 .

# 이미지 저장
docker save -o korea-pii-cpu.tar korea-pii-cpu:v2.0.0
gzip korea-pii-cpu.tar

# 필수 파일만 패키징
mkdir -p minimal-package
cp korea-pii-cpu.tar.gz minimal-package/
cp install-offline.sh minimal-package/
cp INSTALL_GUIDE_ROCKY.md minimal-package/

# 압축
tar -czf korea-pii-minimal-package.tar.gz minimal-package/

echo "✅ 최소 패키지 생성 완료: korea-pii-minimal-package.tar.gz"
echo "   CPU 버전만 포함 (GPU 버전은 내부망에서 별도 준비 필요)"
EOF

chmod +x create-minimal-package.sh
```

## 🚨 중요 사항

### GPU 없이 준비하는 경우 제한사항:
1. **GPU 버전 테스트 불가**: 이미지는 빌드 가능하나 실행 테스트 불가
2. **LLM 모델 테스트 제한**: GPU 없이는 대형 모델 로딩 불가
3. **성능 검증 불가**: 실제 GPU 성능 측정 불가능

### 해결 방법:
1. **단계적 배포**: CPU 버전 먼저 배포 → 내부망에서 GPU 버전 테스트
2. **협력 개발**: GPU 있는 동료나 서버에서 테스트 요청
3. **클라우드 활용**: 임시로 GPU 인스턴스 사용 (1-2시간)

## 📋 최종 체크리스트

- [ ] CPU 버전 Docker 이미지 빌드 완료
- [ ] CPU 버전 로컬 테스트 완료
- [ ] GPU 버전 Docker 이미지 빌드 완료 (실행 테스트는 선택)
- [ ] 설치 스크립트 준비
- [ ] 문서 준비 (설치 가이드, 사용 매뉴얼)
- [ ] 패키지 압축 완료

## 💡 추천 접근법

**현재 상황(GPU 없음)에서는:**
1. CPU 버전만 완전히 테스트
2. GPU 이미지는 빌드만 수행
3. 내부망에 먼저 CPU 버전 배포
4. 내부망에서 GPU 버전 직접 테스트 및 조정

이렇게 하면 GPU 없이도 대부분의 준비가 가능합니다!