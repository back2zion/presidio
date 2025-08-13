#!/bin/bash

# 한국도로공사 PII 제거 시스템 - 오프라인 패키지 준비 스크립트
# 인터넷 연결된 환경에서 실행하여 모든 의존성 다운로드

echo "📦 오프라인 패키지 준비 중..."
echo "=================================="

# 작업 디렉토리 생성
mkdir -p offline-package
cd offline-package

# 1. Python 패키지 다운로드 (wheel 파일)
echo "🐍 Python 패키지 다운로드..."
mkdir -p wheels
pip download --dest wheels --no-deps \
    Flask==2.3.3 \
    pandas==2.0.3 \
    openpyxl==3.1.2 \
    presidio-analyzer==2.2.354 \
    presidio-anonymizer==2.2.354 \
    spacy==3.6.1 \
    requests==2.31.0 \
    Werkzeug==2.3.7 \
    Jinja2==3.1.2 \
    click==8.1.7 \
    itsdangerous==2.1.2 \
    MarkupSafe==2.1.3 \
    numpy==1.24.3 \
    pytz==2023.3 \
    python-dateutil==2.8.2 \
    six==1.16.0 \
    et-xmlfile==1.1.0 \
    urllib3==2.0.4 \
    charset-normalizer==3.2.0 \
    idna==3.4 \
    certifi==2023.7.22

# 2. spaCy 언어 모델 다운로드
echo "🌍 spaCy 한국어 모델 다운로드..."
mkdir -p models
python -m spacy download ko_core_news_sm --user
cp -r ~/.local/lib/python*/site-packages/ko_core_news_sm* models/

# 3. Presidio 모델 파일 다운로드
echo "🔍 Presidio 모델 다운로드..."
mkdir -p presidio-models
python -c "
import spacy
from presidio_analyzer.nlp_engine import NlpEngineProvider

# spaCy 모델 다운로드 및 캐시
nlp_configuration = {
    'nlp_engine_name': 'spacy',
    'models': [{'lang_code': 'ko', 'model_name': 'ko_core_news_sm'}]
}
provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
nlp_engine = provider.create_engine()
print('Presidio 모델 준비 완료')
"

# 4. VLLM 및 PyTorch 패키지 (GPU 환경용)
echo "🎮 VLLM 및 GPU 패키지 다운로드..."
mkdir -p gpu-wheels
pip download --dest gpu-wheels --no-deps \
    torch==2.1.0 \
    torchvision==0.16.0 \
    transformers==4.35.0 \
    accelerate==0.24.0 \
    safetensors==0.4.0 \
    tokenizers==0.14.1 \
    huggingface-hub==0.17.3 \
    pyyaml==6.0.1 \
    regex==2023.10.3 \
    tqdm==4.66.1 \
    packaging==23.2

# VLLM (크기가 클 수 있음)
pip download --dest gpu-wheels vllm>=0.2.2

# 5. Qwen 모델 다운로드 (HuggingFace)
echo "🤖 Qwen 모델 다운로드..."
mkdir -p huggingface-models
python -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
import os

model_name = 'Qwen/Qwen2.5-7B-Instruct'
cache_dir = './huggingface-models'

try:
    print(f'모델 다운로드 시작: {model_name}')
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
    # 모델은 용량이 크므로 토크나이저만 먼저 다운로드
    print('토크나이저 다운로드 완료')
    
    # 모델은 선택적으로 다운로드 (용량 14GB+)
    # model = AutoModelForCausalLM.from_pretrained(model_name, cache_dir=cache_dir)
    print('모델 다운로드를 원하면 주석을 해제하세요')
except Exception as e:
    print(f'모델 다운로드 실패: {e}')
    print('내부망에서 별도로 준비하세요')
"

# 6. 소스 코드 복사
echo "📁 소스 코드 패키징..."
cp ../remover.py .
cp -r ../templates .
cp ../README-H100-DEPLOYMENT.md .

# 7. 오프라인 설치 스크립트 생성
cat > install-offline.sh << 'EOF'
#!/bin/bash
echo "🚀 오프라인 설치 시작..."

# Python 패키지 설치
echo "📦 Python 패키지 설치..."
pip install --no-index --find-links wheels wheels/*.whl

# GPU 패키지 설치 (H100 환경)
echo "🎮 GPU 패키지 설치..."
pip install --no-index --find-links gpu-wheels gpu-wheels/*.whl

# spaCy 모델 설치
echo "🌍 spaCy 모델 설치..."
pip install models/ko_core_news_sm*

# HuggingFace 캐시 설정
export HF_HOME="./huggingface-models"
export TRANSFORMERS_CACHE="./huggingface-models"

echo "✅ 오프라인 설치 완료"
echo "실행: python remover.py"
EOF

chmod +x install-offline.sh

# 8. 전체 패키지 압축
echo "📦 패키지 압축 중..."
cd ..
tar -czf korea-pii-offline-package.tar.gz offline-package/

echo "✅ 오프라인 패키지 준비 완료!"
echo "파일: korea-pii-offline-package.tar.gz"
echo "크기: $(du -h korea-pii-offline-package.tar.gz | cut -f1)"
echo ""
echo "내부망 배포:"
echo "1. korea-pii-offline-package.tar.gz를 내부망으로 반입"
echo "2. tar -xzf korea-pii-offline-package.tar.gz"
echo "3. cd offline-package && ./install-offline.sh"
echo "4. python remover.py"