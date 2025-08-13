# 한국도로공사 민원 개인정보 제거 시스템 내부망 설치 가이드

## 📋 시스템 요구사항

### 하드웨어 요구사항
- **CPU**: 2 Core 이상 (권장: 4 Core)
- **메모리**: 4GB 이상 (권장: 8GB)
- **디스크**: 10GB 이상 여유 공간
- **네트워크**: 내부망 접속 가능한 서버

### 소프트웨어 요구사항
- **OS**: Linux (Ubuntu 20.04+ 권장) 또는 Windows Server 2019+
- **Docker**: 20.10.0 이상
- **브라우저**: Chrome, Firefox, Edge 최신 버전

## 🚀 설치 절차

### 1단계: Docker 설치 (Linux)
```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
```

### 2단계: 배포 파일 전송
- 외부망에서 생성된 `korea-expressway-pii-remover-v1.0.0.tar.gz` 파일을 내부망 서버로 전송
- USB, CD/DVD, 또는 승인된 파일 전송 방법 사용

### 3단계: Docker 이미지 로드
```bash
# 압축 해제
gunzip korea-expressway-pii-remover-v1.0.0.tar.gz

# Docker 이미지 로드
docker load -i korea-expressway-pii-remover-v1.0.0.tar

# 이미지 확인
docker images | grep korea-expressway-pii-remover
```

### 4단계: 컨테이너 실행
```bash
# 기본 실행
docker run -d \
  --name korea-expressway-pii-remover \
  -p 5000:5000 \
  --restart unless-stopped \
  korea-expressway-pii-remover:v1.0.0

# 데이터 볼륨 마운트 실행 (권장)
mkdir -p /data/pii-remover
docker run -d \
  --name korea-expressway-pii-remover \
  -p 5000:5000 \
  -v /data/pii-remover:/app/data \
  --restart unless-stopped \
  korea-expressway-pii-remover:v1.0.0
```

### 5단계: 서비스 확인
```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker logs korea-expressway-pii-remover

# 헬스체크 확인
docker exec korea-expressway-pii-remover curl -f http://localhost:5000/
```

## 🌐 접속 및 사용

### 웹 인터페이스 접속
- **URL**: `http://서버IP:5000`
- **예시**: `http://192.168.1.100:5000`

### 사용 방법
1. 웹 브라우저에서 시스템 접속
2. 민원 엑셀 파일을 드래그앤드롭 또는 파일 선택
3. 자동 개인정보 제거 처리
4. 처리된 파일 다운로드

## 🔧 관리 명령어

### 컨테이너 관리
```bash
# 컨테이너 중지
docker stop korea-expressway-pii-remover

# 컨테이너 시작
docker start korea-expressway-pii-remover

# 컨테이너 재시작
docker restart korea-expressway-pii-remover

# 컨테이너 삭제
docker rm -f korea-expressway-pii-remover
```

### 로그 관리
```bash
# 실시간 로그 확인
docker logs -f korea-expressway-pii-remover

# 최근 100줄 로그 확인
docker logs --tail 100 korea-expressway-pii-remover
```

### 업데이트
```bash
# 기존 컨테이너 중지 및 삭제
docker stop korea-expressway-pii-remover
docker rm korea-expressway-pii-remover

# 새 이미지 로드 및 실행
docker load -i 새로운이미지파일.tar
docker run -d --name korea-expressway-pii-remover -p 5000:5000 korea-expressway-pii-remover:새버전
```

## 🔒 보안 고려사항

### 네트워크 보안
- 방화벽에서 5000 포트 허용 설정
- 필요시 HTTPS 적용 (Nginx 리버스 프록시 사용)
- 내부망에서만 접근 가능하도록 설정

### 데이터 보안
- 처리된 파일은 자동으로 서버에서 삭제됨
- 임시 파일 저장 경로: `/tmp` (메모리 마운트 권장)
- 정기적인 로그 정리 필요

## 🆘 문제 해결

### 자주 발생하는 문제

1. **포트 충돌**
   ```bash
   # 다른 포트 사용
   docker run -d --name korea-expressway-pii-remover -p 8080:5000 korea-expressway-pii-remover:v1.0.0
   ```

2. **메모리 부족**
   ```bash
   # 메모리 제한 설정
   docker run -d --name korea-expressway-pii-remover -p 5000:5000 --memory=4g korea-expressway-pii-remover:v1.0.0
   ```

3. **파일 권한 문제**
   ```bash
   # 데이터 디렉토리 권한 설정
   sudo chown -R 1000:1000 /data/pii-remover
   ```

## 📞 기술 지원

- **시스템 문의**: IT 보안팀
- **기능 문의**: 정보보호팀
- **장애 신고**: 시스템 관리팀

---

**⚠️ 주의사항**
- 본 시스템은 내부망에서만 사용해야 합니다
- 처리 전 원본 파일은 별도 백업 보관하시기 바랍니다
- 정기적인 시스템 점검 및 업데이트가 필요합니다
