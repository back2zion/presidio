# 🚀 한국도로공사 PII 제거 시스템 - 빠른 시작 가이드

## 지금 바로 시작하기 (GPU 없어도 가능!)

### Windows
```cmd
quick-start.bat
```

### Linux/Mac
```bash
chmod +x quick-start.sh
./quick-start.sh
```

메뉴에서 **1번**을 선택하면 바로 테스트 가능합니다.

---

## 📦 내부망 반입 절차 (간단 버전)

### 1단계: 패키지 생성 (외부망)
```bash
# quick-start.sh 실행 후 2번 선택
# 또는 직접 실행:
docker build -f Dockerfile -t korea-pii:v2 .
docker save -o korea-pii.tar korea-pii:v2
gzip korea-pii.tar
```

### 2단계: 파일 반입
- `korea-pii.tar.gz` 파일을 USB/CD로 내부망 복사

### 3단계: 내부망 설치 (Rocky Linux 8.1)
```bash
# 압축 해제
gunzip korea-pii.tar.gz

# Docker 이미지 로드
docker load -i korea-pii.tar

# 실행
docker run -d --name korea-pii -p 5000:5000 korea-pii:v2

# H100 GPU 사용시 (7번 슬롯)
docker run -d --name korea-pii --gpus '"device=7"' -p 5000:5000 korea-pii:v2
```

### 4단계: 접속
브라우저에서 `http://서버IP:5000` 접속

---

## 🎯 핵심 파일만

꼭 필요한 파일들:
- `remover.py` - 메인 애플리케이션
- `Dockerfile` - CPU 버전 이미지
- `Dockerfile.gpu` - GPU 버전 이미지 (선택)
- `requirements.txt` - Python 패키지
- `templates/index.html` - 웹 UI
- `quick-start.sh` - 빠른 실행 스크립트

---

## ❓ 자주 묻는 질문

**Q: GPU가 없는데 테스트 가능한가요?**
> CPU 버전으로 모든 기능 테스트 가능합니다. quick-start.sh 실행 후 1번 선택.

**Q: 내부망에 인터넷이 없는데 설치 가능한가요?**
> Docker 이미지에 모든 의존성이 포함되어 있어 인터넷 없이 설치 가능합니다.

**Q: Rocky Linux 8.1이 아닌 다른 OS도 가능한가요?**
> Docker만 설치되어 있으면 어떤 Linux도 가능합니다.

**Q: H100 GPU가 꼭 필요한가요?**
> CPU 버전도 제공되므로 GPU 없이도 사용 가능합니다. GPU는 성능 향상용입니다.

---

## 🆘 문제 해결

### Docker 명령어가 안 될 때
```bash
# Docker 설치 (Rocky Linux 8.1)
sudo dnf install -y docker-ce
sudo systemctl start docker
```

### 포트 5000이 사용 중일 때
```bash
# 다른 포트 사용
docker run -d --name korea-pii -p 8080:5000 korea-pii:v2
# http://localhost:8080 접속
```

### 메모리 부족 에러
```bash
# 메모리 제한 설정
docker run -d --name korea-pii -p 5000:5000 --memory=4g korea-pii:v2
```

---

**간단히 요약: `quick-start.sh` 실행하면 끝!**