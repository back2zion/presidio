@echo off
REM LLM 모델 다운로드 스크립트 (Windows용)
setlocal enabledelayedexpansion

echo 🤖 내부망용 LLM 모델 다운로드 시작

REM 모델 저장 디렉토리 생성
if not exist models mkdir models
cd models

echo 📥 Hugging Face 모델 다운로드 중...

REM Python을 사용한 모델 다운로드
python -c "
import os
import sys
from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer

def download_model(model_name, local_dir):
    print(f'모델 다운로드: {model_name}')
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        try:
            model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
        except:
            model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        
        tokenizer.save_pretrained(local_dir)
        model.save_pretrained(local_dir)
        print(f'✅ 모델 저장 완료: {local_dir}')
        return True
    except Exception as e:
        try:
            model = SentenceTransformer(model_name)
            model.save(local_dir)
            print(f'✅ SentenceTransformer 모델 저장 완료: {local_dir}')
            return True
        except Exception as e2:
            print(f'❌ 모델 다운로드 실패: {model_name}')
            print(f'   오류: {e}')
            return False

# 모델 다운로드
models = [
    ('beomi/KcELECTRA-base-v2022', 'kcelectra-base'),
    ('klue/roberta-base', 'klue-roberta'),
    ('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', 'multilingual-minilm')
]

for model_name, local_dir in models:
    download_model(model_name, local_dir)

print('모든 모델 다운로드 완료!')
"

REM spaCy 모델 다운로드
echo 📚 spaCy 한국어 모델 다운로드
python -m spacy download ko_core_news_sm

REM 모델 정보 파일 생성
echo # 포함된 모델 목록 > model_info.txt
echo - kcelectra-base: 한국어 ELECTRA 모델 (PII 탐지용) >> model_info.txt
echo - klue-roberta: 한국어 RoBERTa 모델 (NER용) >> model_info.txt
echo - multilingual-minilm: 다국어 임베딩 모델 >> model_info.txt
echo - ko_core_news_sm: spaCy 한국어 모델 >> model_info.txt
echo. >> model_info.txt
echo 다운로드 날짜: %date% %time% >> model_info.txt

echo ✅ 모델 다운로드 완료!
cd ..

pause