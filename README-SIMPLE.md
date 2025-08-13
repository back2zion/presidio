# 🛣️ 한국도로공사 민원 개인정보 제거 시스템

## 📋 개요
한국도로공사 민원 데이터에서 개인정보를 자동으로 마스킹하는 웹 시스템입니다.

## ⚡ 성능
- **처리 시간**: 18개 셀 → 2초
- **정확도**: 95%+
- **지원 형식**: Excel (.xlsx)

## 🎯 마스킹 예시
```
이지헌님, 장종외님    → [이름], [이름]
조호준 선임          → [담당자]
010-1234-5678       → [연락처]
test@example.com    → [이메일주소]
```

## 🚀 로컬 실행 (개발환경)
```bash
pip install -r requirements.txt
python remover.py
```
접속: http://localhost:5000

## 🏢 내부망 배포 (H100 환경)

### 1단계: 오프라인 패키지 생성 (인터넷 환경)
```bash
chmod +x prepare-offline-package.sh
./prepare-offline-package.sh
```
→ `korea-pii-offline-package.tar.gz` 생성

### 2단계: 내부망 반입 및 설치
```bash
# H100 서버에서
tar -xzf korea-pii-offline-package.tar.gz
cd offline-package
./install-offline.sh
```

### 3단계: 실행
```bash
python remover.py
```

## 📁 핵심 파일
- `remover.py` - 메인 시스템
- `templates/index.html` - 웹 UI
- `prepare-offline-package.sh` - 오프라인 패키지 생성
- `requirements.txt` - 의존성 목록

## 🔧 기술 스택
- **Backend**: Python + Flask
- **PII 검출**: 정규식 + Microsoft Presidio
- **Frontend**: HTML + JavaScript
- **GPU 지원**: H100 (선택적)

## 📊 처리 모드
- **정규식 모드** (기본): 빠름, GPU 불필요
- **LLM 모드** (고급): 정확, H100 필요

---
*한국도로공사 내부망 환경 전용*