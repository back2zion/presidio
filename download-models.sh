#!/bin/bash
# LLM 모델 다운로드 스크립트 (내부망 반입용)

set -e

echo "🤖 내부망용 LLM 모델 다운로드 시작"

# 모델 저장 디렉토리 생성
mkdir -p models
cd models

# Hugging Face 모델 다운로드 함수
download_hf_model() {
    local model_name=$1
    local local_dir=$2
    
    echo "📥 다운로드 중: $model_name -> $local_dir"
    
    python3 -c "
import os
from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer

model_name = '$model_name'
local_dir = '$local_dir'

print(f'모델 다운로드: {model_name}')

try:
    # Causal LM 모델 시도
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
    
    tokenizer.save_pretrained(local_dir)
    model.save_pretrained(local_dir)
    print(f'✅ CausalLM 모델 저장 완료: {local_dir}')
    
except Exception as e1:
    try:
        # 일반 모델 시도
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        
        tokenizer.save_pretrained(local_dir)
        model.save_pretrained(local_dir)
        print(f'✅ 일반 모델 저장 완료: {local_dir}')
        
    except Exception as e2:
        try:
            # Sentence Transformer 시도
            model = SentenceTransformer(model_name)
            model.save(local_dir)
            print(f'✅ SentenceTransformer 모델 저장 완료: {local_dir}')
            
        except Exception as e3:
            print(f'❌ 모델 다운로드 실패: {model_name}')
            print(f'   CausalLM 오류: {e1}')
            print(f'   일반 모델 오류: {e2}')
            print(f'   SentenceTransformer 오류: {e3}')
"
}

# 1. 한국어 특화 경량 모델 (필수)
download_hf_model "beomi/KcELECTRA-base-v2022" "kcelectra-base"
download_hf_model "klue/roberta-base" "klue-roberta"

# 2. 다국어 임베딩 모델
download_hf_model "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" "multilingual-minilm"

# 3. 경량 생성 모델 (선택사항 - 용량 고려)
echo "⚠️  대용량 모델 다운로드 시작 (선택사항)"
echo "   스킵하려면 Ctrl+C를 누르세요 (10초 대기)"
sleep 10

download_hf_model "microsoft/DialoGPT-medium" "dialogpt-medium"

# 4. spaCy 한국어 모델 다운로드
echo "📚 spaCy 한국어 모델 다운로드"
python3 -m spacy download ko_core_news_sm
python3 -m spacy download ko_core_news_md

# 모델 정보 파일 생성
cat > model_info.txt << EOF
# 포함된 모델 목록
- kcelectra-base: 한국어 ELECTRA 모델 (PII 탐지용)
- klue-roberta: 한국어 RoBERTa 모델 (NER용)
- multilingual-minilm: 다국어 임베딩 모델
- dialogpt-medium: 대화 생성 모델 (선택사항)
- ko_core_news_sm: spaCy 한국어 소형 모델
- ko_core_news_md: spaCy 한국어 중형 모델

다운로드 날짜: $(date)
전체 용량: $(du -sh . | cut -f1)
EOF

echo "✅ 모델 다운로드 완료!"
echo "📁 모델 저장 위치: $(pwd)"
echo "📊 전체 용량: $(du -sh . | cut -f1)"

cd ..