#!/bin/bash
# 한국도로공사 민원 개인정보 제거 시스템 배포 스크립트

set -e

echo "🚀 한국도로공사 민원 개인정보 제거 시스템 배포 시작"

# 변수 설정
IMAGE_NAME="korea-expressway-pii-remover"
IMAGE_TAG="v1.0.0"
CONTAINER_NAME="korea-expressway-pii-remover"
EXPORT_FILE="${IMAGE_NAME}-${IMAGE_TAG}.tar"

# 1단계: Docker 이미지 빌드
echo "📦 Docker 이미지 빌드 중..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest

# 2단계: 이미지 압축 및 내보내기
echo "💾 Docker 이미지 내보내기 중..."
docker save -o ${EXPORT_FILE} ${IMAGE_NAME}:${IMAGE_TAG}
gzip ${EXPORT_FILE}

echo "✅ 배포 파일 생성 완료:"
echo "   - 파일명: ${EXPORT_FILE}.gz"
echo "   - 크기: $(du -h ${EXPORT_FILE}.gz | cut -f1)"

# 3단계: 배포 안내
cat << EOF

📋 내부망 배포 절차:
1. ${EXPORT_FILE}.gz 파일을 내부망 서버로 전송
2. 내부망에서 다음 명령어 실행:
   gunzip ${EXPORT_FILE}.gz
   docker load -i ${EXPORT_FILE}
   docker run -d --name ${CONTAINER_NAME} -p 5000:5000 ${IMAGE_NAME}:${IMAGE_TAG}

🌐 접속 URL: http://내부서버IP:5000

EOF

echo "🎉 배포 파일 준비 완료!"
