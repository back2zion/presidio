# 한국도로공사 민원 개인정보 제거 시스템 배포 패키지

## 📦 배포 패키지 구성

```
korea-expressway-pii-deployment/
├── korea_expressway_pii_remover.py    # 메인 애플리케이션
├── 한국도로공사_민원_테스트데이터.xlsx    # 테스트 데이터
├── Dockerfile                          # Docker 이미지 빌드 파일
├── requirements.txt                    # Python 의존성
├── docker-compose-pii.yml             # Docker Compose 설정
├── deploy.sh                          # Linux 배포 스크립트
├── deploy.bat                         # Windows 배포 스크립트
├── INSTALL_GUIDE.md                   # 설치 가이드
└── README_DEPLOYMENT.md               # 이 파일
```

## 🚀 내부망 반입 절차

### 1단계: 외부망에서 Docker 이미지 생성
```bash
# Linux/Mac
chmod +x deploy.sh
./deploy.sh

# Windows
deploy.bat
```

### 2단계: 생성된 파일들을 내부망으로 전송
- `korea-expressway-pii-remover-v1.0.0.tar.gz` (또는 .zip)
- `INSTALL_GUIDE.md`

### 3단계: 내부망에서 설치
`INSTALL_GUIDE.md` 파일의 지침을 따라 설치

## 📋 보안 검토 체크리스트

### 코드 보안
- ✅ 외부 인터넷 연결 불필요
- ✅ 로컬 파일 처리만 수행
- ✅ 개인정보는 메모리에서만 처리
- ✅ 처리 후 임시 파일 자동 삭제
- ✅ 오픈소스 라이브러리만 사용

### 네트워크 보안
- ✅ 내부망에서만 접근 가능
- ✅ HTTPS 설정 가능
- ✅ 방화벽 설정으로 접근 제어

### 데이터 보안
- ✅ 업로드된 파일 자동 삭제
- ✅ 개인정보 로깅 없음
- ✅ 처리 결과만 다운로드 제공

## 🔧 시스템 요구사항

### 최소 사양
- CPU: 2 Core
- Memory: 4GB
- Disk: 10GB
- OS: Linux or Windows Server

### 권장 사양
- CPU: 4 Core
- Memory: 8GB
- Disk: 20GB
- OS: Ubuntu 20.04+ or Windows Server 2019+

## 📞 지원 연락처

기술적 문의사항이 있으시면 시스템 담당자에게 연락하시기 바랍니다.

---
**생성일**: 2025-08-13
**버전**: 1.0.0
**담당**: IT보안팀
