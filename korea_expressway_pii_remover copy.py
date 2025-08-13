#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국도로공사 민원 개인정보 제거 시스템 (올인원 버전)
- 웹 UI 포함
- 엑셀 파일 처리
- 강화된 한국어 PII 패턴 (순서 무관 처리)
"""

import os
import re
import pandas as pd
import tempfile
import time
import uuid
import base64
import gc
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine, OperatorConfig


class ProgressTracker:
    """진행률 추적 클래스"""

    def __init__(self):
        self.total_rows = 0
        self.processed_rows = 0
        self.current_column = ""
        self.start_time = None
        self.current_file = ""

    def start(self, total_rows, filename):
        self.total_rows = total_rows
        self.processed_rows = 0
        self.start_time = time.time()
        self.current_file = filename

    def update(self, processed_rows, column_name=""):
        self.processed_rows = processed_rows
        self.current_column = column_name

    def get_progress(self):
        if self.total_rows == 0:
            return {
                "percentage": 0,
                "processed": 0,
                "total": 0,
                "eta": "계산 중...",
                "speed": "0 건/초",
                "column": "",
                "filename": "",
            }

        percentage = min(100, (self.processed_rows / self.total_rows) * 100)
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        if elapsed_time > 0 and self.processed_rows > 0:
            speed_num = self.processed_rows / elapsed_time
            remaining_rows = self.total_rows - self.processed_rows
            eta_seconds = remaining_rows / speed_num if speed_num > 0 else 0

            if eta_seconds < 60:
                eta = f"{int(eta_seconds)}초"
            elif eta_seconds < 3600:
                eta = f"{int(eta_seconds // 60)}분 {int(eta_seconds % 60)}초"
            else:
                hours = int(eta_seconds // 3600)
                minutes = int((eta_seconds % 3600) // 60)
                eta = f"{hours}시간 {minutes}분"
            
            speed_text = f"{speed_num:.1f} 건/초"
        else:
            eta = "계산 중..."
            speed_text = "0.0 건/초"

        return {
            "percentage": round(percentage, 1),
            "processed": int(self.processed_rows),
            "total": int(self.total_rows),
            "eta": eta,
            "speed": speed_text,
            "column": self.current_column,
            "filename": os.path.basename(self.current_file),
        }

    def get_final_stats(self):
        """최종 처리 통계 반환"""
        return {
            "total_rows": self.total_rows,
            "processed_rows": self.processed_rows,
            "total_pii_removed": getattr(self, "pii_removed_count", 0),
            "processing_time": time.time() - self.start_time if self.start_time else 0,
        }

    def add_pii_removed(self, count=1):
        """제거된 PII 개수 추가"""
        if not hasattr(self, "pii_removed_count"):
            self.pii_removed_count = 0
        self.pii_removed_count += count


# 전역 진행률 추적기
progress_tracker = ProgressTracker()


class KoreaExpresswayPIIRemover:
    """한국도로공사 민원 데이터 개인정보 제거 엔진 (정규식 + LLM 하이브리드)"""

    def __init__(self, use_llm=True, llm_model="qwen3:8b"):
        """PII 제거 엔진 초기화"""
        print("[초기화] 한국도로공사 PII 제거 엔진 초기화 중...")
        
        self.use_llm = use_llm
        
        # Presidio 엔진 초기화 (폴백용)
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # 한국어 커스텀 인식기 추가
        self._setup_korean_recognizers()

        # 익명화 연산자 설정
        self.operators = {
            "DEFAULT": OperatorConfig("replace", {"new_value": "[개인정보]"}),
            "PERSON": OperatorConfig("replace", {"new_value": "[이름]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[연락처]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[이메일주소]"}),
            "KOREAN_NAME": OperatorConfig("replace", {"new_value": "[이름]"}),
            "KOREAN_CONTACT": OperatorConfig("replace", {"new_value": "[연락처]"}),
            "ORGANIZATION_INFO": OperatorConfig("replace", {"new_value": "[기관정보]"}),
        }
        
        # LLM 엔진 초기화
        if self.use_llm:
            try:
                # LLM 기능을 내장으로 통합
                self.llm_remover = self._create_llm_engine(llm_model)
                print("[성공] LLM 엔진 통합 완료")
            except Exception as e:
                print(f"[경고] LLM 엔진 초기화 실패, 정규식 모드로 전환: {e}")
                self.use_llm = False
                self.llm_remover = None
        else:
            self.llm_remover = None

        print("[완료] PII 제거 엔진 초기화 완료")

    def _create_llm_engine(self, model_name):
        """내장 LLM 엔진 생성"""
        import requests
        import json
        from dataclasses import dataclass
        from typing import List, Tuple
        
        @dataclass
        class PIIEntity:
            entity_type: str
            original_text: str
            replacement: str
            confidence: float
        
        class SimpleLLMEngine:
            def __init__(self, model_name):
                self.model_name = model_name
                self.base_url = "http://localhost:11434"
                self.api_url = f"{self.base_url}/api/generate"
                self.replacement_map = {
                    "PERSON": "[이름]",
                    "PHONE": "[전화번호]",
                    "EMAIL": "[이메일]",
                    "VEHICLE": "[차량번호]",
                    "EMPLOYEE": "[담당자]",
                }
                self._check_connection()
            
            def _check_connection(self):
                try:
                    response = requests.get(f"{self.base_url}/api/tags", timeout=10)
                    if response.status_code != 200:
                        raise ConnectionError("Ollama 서버 연결 실패")
                except:
                    raise ConnectionError("Ollama가 실행되지 않았습니다")
            
            def process_text(self, text):
                # 텍스트가 너무 짧으면 처리하지 않음
                if len(str(text).strip()) < 5:
                    return text, []
                    
                # 텍스트가 너무 길면 일부만 처리
                if len(text) > 1000:
                    text = text[:1000] + "..."
                
                prompt = f"""개인정보 찾기. JSON 응답만.

텍스트: {text}

찾기: 이름, 전화번호, 이메일
제외: 지명, 부서명

JSON: {{"entities":[{{"type":"PERSON","text":"이름"}}]}}"""

                try:
                    response = requests.post(
                        self.api_url,
                        json={
                            "model": self.model_name,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.1,
                                "num_predict": 200,  # 응답 길이 제한을 더 짧게
                                "top_p": 0.9,
                                "top_k": 40
                            }
                        },
                        timeout=120  # 타임아웃 120초로 증가
                    )
                    
                    if response.status_code == 200:
                        llm_response = response.json()['response']
                        entities = self._parse_response(llm_response)
                        if entities:  # 엔티티를 찾았으면
                            return self._anonymize_text(text, entities), entities
                except Exception as e:
                    print(f"LLM 처리 실패 (정규식 폴백): {e}")
                
                # LLM 실패 시 정규식 폴백
                return self._regex_fallback(text)
            
            def _regex_fallback(self, text):
                """정규식 폴백 처리"""
                entities = []
                result = text
                
                # 전화번호
                phone_matches = re.findall(r'0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}', text)
                for match in phone_matches:
                    entities.append(PIIEntity("PHONE", match, "[전화번호]", 0.9))
                    result = result.replace(match, "[전화번호]")
                
                # 이메일
                email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                for match in email_matches:
                    entities.append(PIIEntity("EMAIL", match, "[이메일]", 0.9))
                    result = result.replace(match, "[이메일]")
                
                # 이름 + 직급
                name_matches = re.findall(r'([가-힣]{2,4})\s+(대리|과장|차장|부장|팀장)', text)
                for name, title in name_matches:
                    full_match = f"{name} {title}"
                    entities.append(PIIEntity("EMPLOYEE", full_match, "[담당자]", 0.8))
                    result = result.replace(full_match, "[담당자]")
                
                return result, entities
            
            def _parse_response(self, response):
                entities = []
                try:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        for entity in data.get('entities', []):
                            entities.append(PIIEntity(
                                entity_type=entity['type'],
                                original_text=entity['text'],
                                replacement=self.replacement_map.get(entity['type'], '[개인정보]'),
                                confidence=entity.get('confidence', 0.8)
                            ))
                except:
                    pass
                return entities
            
            def _anonymize_text(self, text, entities):
                result = text
                for entity in sorted(entities, key=lambda x: len(x.original_text), reverse=True):
                    result = result.replace(entity.original_text, entity.replacement)
                return result
        
        return SimpleLLMEngine(model_name)

    def _setup_korean_recognizers(self):
        """한국어 커스텀 인식기 설정"""

        # 직원/담당자 인식기 (직급 포함)
        staff_recognizer = PatternRecognizer(
            supported_entity="KOREAN_NAME",
            patterns=[
                Pattern(
                    name="korean_staff_with_title",
                    regex=r"([가-힣]{2,4})\s*(대리|주임|사원|과장|차장|부장|팀장|실장|소장|지사장)",
                    score=0.9,
                ),
                Pattern(
                    name="korean_staff_contact",
                    regex=r"담당자\s*([가-힣]{2,4})",
                    score=0.85,
                ),
            ],
            name="korean_staff_recognizer",
            context=["담당자", "대리", "과장", "차장", "부장", "팀장"],
        )

        # 한국 이름 인식기 (더 엄격한 패턴으로 수정)
        korean_name_recognizer = PatternRecognizer(
            supported_entity="KOREAN_NAME",
            patterns=[
                # "제 이름은 김철수이고" 패턴 (확실한 개인정보)
                Pattern(
                    name="korean_name_introduction",
                    regex=r"(?:제|내)\s*이름은\s*([가-힣]{2,4})(?:이고|입니다|이며)",
                    score=0.95,
                ),
                # "저는 김철수입니다" 패턴 (확실한 개인정보)
                Pattern(
                    name="korean_name_self_intro",
                    regex=r"저는\s*([가-힣]{2,4})(?:입니다|이고|라고)",
                    score=0.9,
                ),
                # 신고자/문의자 명시적 패턴 - 콜론이나 "이름/성명"이 명시적으로 있을 때만
                Pattern(
                    name="korean_name_reporter",
                    regex=r"(?:신고자|문의자|민원인|고객|신청자)\s*(?:이름|성명)\s*:?\s*([가-힣]{2,4})",
                    score=0.9,
                ),
                # 연락처와 함께 나오는 이름 (김철수 010-1234-5678) - 바로 인접한 경우만
                Pattern(
                    name="korean_name_with_contact",
                    regex=r"([가-힣]{2,4})\s*[(\[]?\s*0\d{1,2}[-\s]*\d{3,4}[-\s]*\d{4}",
                    score=0.85,
                ),
                # 직급과 함께 나오는 이름 (김철수 대리) - 직급이 바로 붙은 경우만
                Pattern(
                    name="korean_name_with_title",
                    regex=r"([가-힣]{2,3})\s*(대리|주임|사원|과장|차장|부장|팀장|실장|소장|지사장)(?:\s|,|\()",
                    score=0.9,
                ),
            ],
            name="korean_name_recognizer",
            context=["이름", "성명", "저는", "제", "연락처", "신고", "문의", "담당자"],
        )

        # 한국도로공사 연락처 패턴
        contact_recognizer = PatternRecognizer(
            supported_entity="KOREAN_CONTACT",
            patterns=[
                Pattern(
                    name="korean_phone_1", regex=r"0\d{1,2}-\d{3,4}-\d{4}", score=0.9
                ),
                Pattern(
                    name="korean_phone_2",
                    regex=r"0\d{1,2}\s*-\s*\d{3,4}\s*-\s*\d{4}",
                    score=0.9,
                ),
                Pattern(name="korean_phone_3", regex=r"\d{3}-\d{3,4}-\d{4}", score=0.8),
            ],
            name="korean_contact_recognizer",
            context=["연락처", "전화", "문의", "연락", "TEL"],
        )

        # 기관 정보 패턴
        org_info_recognizer = PatternRecognizer(
            supported_entity="ORGANIZATION_INFO",
            patterns=[
                Pattern(
                    name="korean_org_full",
                    regex=r"한국도로공사\s+[가-힣]+지사\s+[가-힣]+팀\s*\([^)]+\)",
                    score=0.95,
                ),
                Pattern(
                    name="korean_org_contact",
                    regex=r"한국도로공사\s+[^)]+\([^)]*\d{3}-\d{3,4}-\d{4}[^)]*\)",
                    score=0.9,
                ),
                Pattern(
                    name="korean_org_staff",
                    regex=r"\([^)]*담당자[^)]*\d{3}-\d{3,4}-\d{4}[^)]*\)",
                    score=0.85,
                ),
            ],
            name="organization_info_recognizer",
            context=["한국도로공사", "담당자", "지사", "팀", "문의하여"],
        )

        # 분석기에 커스텀 인식기 추가
        self.analyzer.registry.add_recognizer(staff_recognizer)
        self.analyzer.registry.add_recognizer(korean_name_recognizer)
        self.analyzer.registry.add_recognizer(contact_recognizer)
        self.analyzer.registry.add_recognizer(org_info_recognizer)

    def _advanced_multi_pass_processing(self, text):
        """다중 패스 처리로 순서 무관 패턴 매칭"""
        if pd.isna(text) or not text or str(text).strip() == "":
            return text

        text_str = str(text)

        # 보호할 일반 단어들 (한국도로공사 관련 업무용어 + 일반 동사/명사)
        protected_words = {
            # 도로/지명 관련
            "기흥", "시흥", "장수", "서해안", "수도권", "국토교통부",
            "도시지역", "측방여유폭", "유출입", "교통량", "포털",
            # 동사/형용사
            "지나", "얻고", "찾아", "제공", "하는지", "몇",
            "따르는지", "따라", "통해", "대한", "해당",
            # 기본 업무용어
            "고속도로", "고속돌", "기본구간", "엇갈림", "구간",
            "도로공사", "도로설계기준",
            "민원", "답변", "감사", "고객", "관련", "안전",
            "순찰", "목적", "참고", "추가", "만족", "서비스",
            "부탁", "질문", "문의", "요청", "처리", "확인",
            "검토", "조치", "개선", "협조", "이용", "운영",
            "관리", "점검", "보수", "공사", "통행", "요금",
            "휴게소", "주차", "화장실", "편의", "시설", "개통",
            "폐쇄", "우회",
            # 행정용어
            "요지", "내용", "사항", "방법", "조건", "기준",
            "절차", "규정", "계획", "방향", "정책", "지침",
            "원칙", "기본", "상황", "현황", "결과", "효과",
            "영향", "변화", "개선", "발전", "진행", "완료",
            # 일반 단어
            "시간", "장소", "지역", "구간", "구역", "위치",
            "방향", "거리", "속도", "신호", "표지", "안내",
            "정보", "알림", "공지", "발표", "기간", "일정",
            "예정", "계획", "준비", "실시", "시행", "적용",
            # 감정/태도 표현
            "다행", "노력", "최선", "협력", "배려", "이해",
            "양해", "죄송", "미안", "고마", "감동", "만족",
            "기쁘", "좋은", "나쁜", "어려운",
        }

        # 여러 번 처리하여 순서 무관 처리
        max_passes = 5
        current_text = text_str

        for pass_num in range(max_passes):
            previous_text = current_text

            # 1단계: 기관/조직 정보 처리
            org_patterns = [
                (
                    r"한국도로공사\s+[가-힣]+지사\s+[가-힣]+팀\s*\([^)]+\)",
                    "[기관연락처정보]",
                ),
                (r"\(담당자[^)]*\d{3}-\d{3,4}-\d{4}[^)]*\)", "[담당자연락처정보]"),
            ]

            for pattern, replacement in org_patterns:
                current_text = re.sub(pattern, replacement, current_text)

            # 2단계: 연락처와 이메일 처리
            contact_patterns = [
                (r"0\d{1,2}[-\s]*\d{3,4}[-\s]*\d{4}", "[연락처]"),
                (r"[a-zA-Z0-9._%+-]+@ex\.co\.kr", "[이메일주소]"),
                (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[이메일주소]"),
            ]

            for pattern, replacement in contact_patterns:
                current_text = re.sub(pattern, replacement, current_text)

            # 3단계: 이름+직급 조합 처리 (모든 가능한 조합)
            name_job_patterns = [
                # 이미 치환된 토큰이 포함된 경우
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\(\s*\[연락처\]\s*,?\s*\[이메일주소\]\s*\)",
                    "[담당자명]([연락처], [이메일주소])",
                ),
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\(\s*\[연락처\]\s*\)",
                    "[담당자명]([연락처])",
                ),
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\(\s*\[이메일주소\]\s*\)",
                    "[담당자명]([이메일주소])",
                ),
                # 실제 연락처/이메일이 포함된 경우
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\(\s*[0-9-]+\s*,?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*\)",
                    "[담당자명]([연락처], [이메일주소])",
                ),
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\(\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*,?\s*[0-9-]+\s*\)",
                    "[담당자명]([연락처], [이메일주소])",
                ),
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\(\s*[0-9-]+\s*\)",
                    "[담당자명]([연락처])",
                ),
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\(\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*\)",
                    "[담당자명]([이메일주소])",
                ),
                # 직급만 있는 경우
                (
                    r"([가-힣]{2,4})\s+(대리|주임|사원|과장|차장|부장|팀장|실장|소장)(?!\s*\()",
                    "[담당자명]",
                ),
            ]

            for pattern, replacement in name_job_patterns:
                current_text = re.sub(pattern, replacement, current_text)

            # 4단계: 개인 이름 패턴 (보호 단어 제외 + 더 엄격한 조건)
            personal_patterns = [
                # 명시적 자기소개 패턴 (확실한 개인정보)
                (
                    r"(?:제|내)\s*이름은\s*([가-힣]{2,4})(?:이고|입니다|이며)",
                    lambda m: "제 이름은 [이름]" + m.group(0)[m.group(0).rfind(m.group(1))+len(m.group(1)):],
                ),
                (
                    r"저는\s*([가-힣]{2,4})입니다",
                    lambda m: "저는 [이름]입니다",
                ),
                (
                    r"([가-힣]{2,4})(?:라고|이라고)\s*합니다",
                    lambda m: "[이름]" + m.group(0)[len(m.group(1)):],
                ),
                (
                    r"신고자\s*(?:이름|성명)\s*:\s*([가-힣]{2,4})",
                    lambda m: "신고자 이름: [이름]",
                ),
                (
                    r"문의자\s*(?:이름|성명)\s*:\s*([가-힣]{2,4})",
                    lambda m: "문의자 이름: [이름]",
                ),
                (
                    r"민원인\s*(?:이름|성명)\s*:\s*([가-힣]{2,4})",
                    lambda m: "민원인 이름: [이름]",
                ),
            ]

            for pattern, replacement_func in personal_patterns:
                # 보호 단어가 아닌 경우에만 치환
                matches = re.finditer(pattern, current_text)
                for match in reversed(list(matches)):  # 역순으로 처리하여 인덱스 문제 방지
                    if match.groups():
                        matched_word = match.group(1)
                        # 보호 단어 체크 + 일반적인 한국어 단어 패턴 체크
                        if matched_word not in protected_words:
                            # 추가 체크: 일반적인 동사나 조사가 아닌지 확인
                            if not any(matched_word.endswith(suffix) for suffix in ["하는", "되는", "있는", "없는", "같은", "위한"]):
                                if callable(replacement_func):
                                    replacement = replacement_func(match)
                                else:
                                    replacement = str(replacement_func)
                                current_text = (
                                    current_text[: match.start()]
                                    + replacement
                                    + current_text[match.end() :]
                                )

            # 5단계: 차량번호 처리
            vehicle_patterns = [
                (r"\d{2,3}[가-힣]\d{4}", "[차량번호]"),
                (r"[가-힣]{2}\d{2}[가-힣]\d{4}", "[차량번호]"),
                (r"\d{3}[가-힣]\d{4}", "[차량번호]"),
                (r"[가-힣]\d{2}[가-힣]\d{4}", "[차량번호]"),
            ]

            for pattern, replacement in vehicle_patterns:
                current_text = re.sub(pattern, replacement, current_text)

            # 변화가 없으면 중단
            if current_text == previous_text:
                break

        return current_text

    def process_text(self, text):
        """텍스트에서 개인정보 제거 (LLM 우선, 정규식 폴백)"""
        if pd.isna(text) or not text or str(text).strip() == "":
            return text

        # 1단계: LLM 우선 처리
        if self.use_llm and self.llm_remover:
            try:
                anonymized, entities = self.llm_remover.process_text(text)
                if entities:  # LLM이 PII를 탐지했다면
                    progress_tracker.add_pii_removed(len(entities))
                    return anonymized
            except Exception as e:
                print(f"[경고] LLM 처리 실패, 정규식 모드로 폴백: {e}")
        
        # 2단계: 정규식 폴백 처리
        processed_text = self._advanced_multi_pass_processing(text)

        # 3단계: Presidio로 추가 개인정보 탐지 (높은 신뢰도만)
        try:
            # 한국어 엔티티만 선택적으로 탐지
            entities_to_check = [
                "KOREAN_NAME",
                "KOREAN_CONTACT", 
                "ORGANIZATION_INFO",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
            ]
            
            results = self.analyzer.analyze(
                text=processed_text, 
                language="en",
                entities=entities_to_check,
                score_threshold=0.7  # 신뢰도 임계값 상향
            )

            if results:
                # 보호 단어 목록 (Presidio 결과 필터링용)
                protected_words = {
                    "기흥", "시흥", "장수", "서해안", "수도권", "국토교통부",
                    "도시지역", "측방여유폭", "유출입", "교통량", "포털",
                    "지나", "얻고", "찾아", "제공", "하는지", "몇",
                    "따르는지", "따라", "통해", "대한", "해당",
                }
                
                # Presidio 결과 필터링
                filtered_results = []
                for result in results:
                    # 탐지된 텍스트 추출
                    detected_text = processed_text[result.start:result.end]
                    
                    # 보호 단어가 아니고 높은 신뢰도인 경우만 처리
                    if (detected_text not in protected_words and 
                        result.score >= 0.7 and
                        result.entity_type in ["EMAIL_ADDRESS", "PHONE_NUMBER", "KOREAN_CONTACT"]):
                        filtered_results.append(result)
                
                if filtered_results:
                    try:
                        from presidio_anonymizer.entities import (
                            RecognizerResult as AnonymRecognizerResult,
                        )

                        # 안전한 타입 변환
                        anonymizer_results = []
                        for result in filtered_results:
                            anonymizer_result = AnonymRecognizerResult(
                                entity_type=str(result.entity_type),
                                start=int(result.start),
                                end=int(result.end),
                                score=float(result.score),
                            )
                            anonymizer_results.append(anonymizer_result)

                        anonymized_result = self.anonymizer.anonymize(
                            text=processed_text,
                            analyzer_results=anonymizer_results,
                            operators=self.operators,
                        )
                        return anonymized_result.text
                    except Exception as anonymizer_error:
                        # 오류 시 정규식 처리 결과만 반환
                        return processed_text
                else:
                    return processed_text
            else:
                return processed_text
        except Exception as e:
            # 오류 시 정규식 처리 결과만 반환
            return processed_text

    def process_expressway_file(self, input_file, output_file=None):
        """한국도로공사 민원 엑셀 파일 처리 (진행률 추적 포함)"""
        print(f"[파일] 파일 읽기: {input_file}")

        df = None

        try:
            # Excel 파일 안전하게 읽기 (파일 잠금 방지)
            max_read_attempts = 3
            for attempt in range(max_read_attempts):
                try:
                    # pandas의 engine 옵션으로 안전하게 읽기
                    df = pd.read_excel(input_file, engine="openpyxl")
                    break
                except PermissionError as pe:
                    if attempt < max_read_attempts - 1:
                        print(
                            f"   파일 읽기 재시도 {attempt + 1}/{max_read_attempts}: {pe}"
                        )
                        time.sleep(1)
                    else:
                        raise pe
                except Exception as e:
                    if attempt < max_read_attempts - 1:
                        print(
                            f"   파일 읽기 재시도 {attempt + 1}/{max_read_attempts}: {e}"
                        )
                        time.sleep(1)
                    else:
                        raise e

            if df is None:
                raise Exception("파일을 읽을 수 없습니다.")

            total_rows = len(df)
            print(f"   - 총 {total_rows:,}개 행 발견")

            # 진행률 추적 시작 (나중에 실제 셀 개수로 재설정됨)
            progress_tracker.start(total_rows, input_file)
            progress_tracker.pii_removed_count = 0  # PII 제거 카운터 초기화

            # 출력 파일명 생성
            if output_file is None:
                base_name = os.path.splitext(input_file)[0]
                output_file = f"{base_name}_개인정보제거.xlsx"

            # PII가 포함될 수 있는 특정 컬럼만 처리
            target_columns = ['민원제목', '질문내용', '답변내용']
            text_columns = []
            
            for col in target_columns:
                if col in df.columns and df[col].dtype == "object":
                    text_columns.append(col)
            
            if not text_columns:
                # 타겟 컬럼이 없으면 모든 텍스트 컬럼 처리
                text_columns = [col for col in df.columns if df[col].dtype == "object"]

            print(f"   - 처리할 텍스트 컬럼: {text_columns}")

            # 실제 처리할 행의 개수 계산 (빈 값 제외)
            total_cells_to_process = 0
            for col in text_columns:
                total_cells_to_process += df[col].notna().sum()
            
            print(f"   - 총 처리할 셀: {total_cells_to_process:,}개")
            
            # 진행률 추적 재설정
            progress_tracker.total_rows = total_cells_to_process
            progress_tracker.processed_rows = 0
            
            # 각 텍스트 컬럼에서 개인정보 제거 (개선된 진행률 추적)
            processed_cells = 0
            
            for col_idx, col in enumerate(text_columns):
                print(f"[{col_idx + 1}/{len(text_columns)}] '{col}' 컬럼 처리 중...")

                # 컬럼별로 진행률 업데이트
                for idx, value in enumerate(df[col]):
                    if pd.notna(value) and str(value).strip() and len(str(value).strip()) > 2:
                        processed_cells += 1
                        original_text = str(value)
                        processed_text = self.process_text(value)
                        df.loc[idx, col] = processed_text

                        # PII 제거 개수 카운트 (간단한 방법: 텍스트 변화 감지)
                        if original_text != processed_text:
                            progress_tracker.add_pii_removed()

                        # 매번 진행률 업데이트 (실시간 업데이트)
                        progress_tracker.update(
                            processed_cells,
                            f"{col} ({col_idx + 1}/{len(text_columns)})",
                        )

            # 최종 진행률 업데이트
            progress_tracker.update(total_cells_to_process, "완료")

            # 결과 저장 (안전한 파일 쓰기)
            max_write_attempts = 3
            for attempt in range(max_write_attempts):
                try:
                    # 임시 파일 생성 (같은 디렉토리에 .xlsx 확장자로)
                    temp_dir = os.path.dirname(output_file)
                    temp_name = f"temp_{uuid.uuid4().hex}.xlsx"
                    temp_output_path = os.path.join(temp_dir, temp_name)

                    with pd.ExcelWriter(temp_output_path, engine="openpyxl") as writer:
                        df.to_excel(writer, index=False, sheet_name="PII 제거 결과")

                    # 임시 파일을 최종 파일로 이동 (원자적 연산 시도)
                    if os.path.exists(output_file):
                        os.remove(output_file)
                    os.rename(temp_output_path, output_file)
                    break
                except PermissionError as pe:
                    if attempt < max_write_attempts - 1:
                        print(
                            f"   파일 저장 재시도 {attempt + 1}/{max_write_attempts}: {pe}"
                        )
                        time.sleep(1)
                    else:
                        raise pe
                except Exception as e:
                    if attempt < max_write_attempts - 1:
                        print(
                            f"   파일 저장 재시도 {attempt + 1}/{max_write_attempts}: {e}"
                        )
                        time.sleep(1)
                    else:
                        raise e

            print(f"[완료] 처리 완료: {output_file}")
            print(f"   - 제거된 개인정보: {progress_tracker.pii_removed_count}개")

            return output_file

        except Exception as e:
            print(f"[오류] 파일 처리 중 오류: {e}")
            raise
        finally:
            # 메모리 정리
            if df is not None:
                del df


# Flask 웹 애플리케이션
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB 제한

# PII 제거 엔진 전역 인스턴스
pii_remover = None


def get_pii_remover(use_llm=True):
    """PII 제거 엔진 팩토리 (모드별로 새 인스턴스 생성)"""
    return KoreaExpresswayPIIRemover(use_llm=use_llm)


# 웹 UI HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>한국도로공사 민원 개인정보 제거 시스템</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 600px;
            width: 100%;
            margin: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 16px;
        }
        
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 15px;
            padding: 60px 20px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            margin-bottom: 20px;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background-color: #f8f9ff;
        }
        
        .upload-area.dragover {
            border-color: #667eea;
            background-color: #f0f2ff;
            transform: scale(1.02);
        }
        
        .upload-icon {
            font-size: 48px;
            color: #ddd;
            margin-bottom: 20px;
        }
        
        .upload-text {
            font-size: 18px;
            color: #666;
            margin-bottom: 10px;
        }
        
        .upload-hint {
            font-size: 14px;
            color: #999;
        }
        
        .file-input {
            display: none;
        }
        
        .progress-section {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: #e8f5e8;
            border-radius: 15px;
        }
        
        .progress-title {
            text-align: center;
            font-size: 20px;
            color: #333;
            margin-bottom: 20px;
        }
        
        .progress-container {
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin: 15px 0;
        }
        
        .progress-bar {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            height: 40px;
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 16px;
        }
        
        .progress-info {
            margin-top: 15px;
            text-align: center;
        }
        
        .progress-info p {
            margin: 8px 0;
            color: #333;
            font-size: 14px;
        }
        
        .progress-stats {
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        
        .stat-item {
            background: #f8f9fa;
            padding: 10px 15px;
            border-radius: 8px;
            text-align: center;
            margin: 5px;
            flex: 1;
            min-width: 120px;
        }
        
        .stat-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }
        
        .result-container {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background-color: #d4edda;
            border-radius: 15px;
            border: 1px solid #c3e6cb;
        }
        
        .success-message {
            color: #155724;
            font-weight: bold;
            margin-bottom: 15px;
            text-align: center;
            font-size: 18px;
        }
        
        .result-stats {
            margin: 15px 0;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
        }
        
        .result-stat {
            text-align: center;
            margin: 10px;
        }
        
        .result-stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #28a745;
        }
        
        .result-stat-label {
            font-size: 14px;
            color: #666;
        }
        
        .download-btn {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s ease;
            width: 100%;
            margin-top: 15px;
        }
        
        .download-btn:hover {
            transform: translateY(-2px);
        }
        
        .error-message {
            color: #721c24;
            font-weight: bold;
            text-align: center;
            margin-top: 20px;
            padding: 20px;
            background-color: #f8d7da;
            border-radius: 15px;
            border: 1px solid #f5c6cb;
            display: none;
        }
        
        .features {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
        }
        
        .features h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .feature-list {
            list-style: none;
            color: #666;
        }
        
        .feature-list li {
            margin-bottom: 8px;
            padding-left: 20px;
            position: relative;
        }
        
        .feature-list li:before {
            content: "✓";
            color: #28a745;
            font-weight: bold;
            position: absolute;
            left: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛣️ 한국도로공사 민원 개인정보 제거</h1>
            <p>엑셀 파일을 업로드하면 개인정보가 자동으로 제거됩니다</p>
        </div>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📄</div>
            <div class="upload-text">파일을 선택하거나 여기로 드래그하세요</div>
            <div class="upload-hint">Excel 파일 (.xlsx, .xls) 지원</div>
        </div>
        
        <input type="file" id="fileInput" class="file-input" accept=".xlsx,.xls" />
        
        <div class="progress-section" id="progressSection">
            <div class="progress-title">🔄 개인정보 제거 진행중...</div>
            <div class="progress-container">
                <div class="progress-bar" id="progressBar">0%</div>
            </div>
            <div class="progress-stats">
                <div class="stat-item">
                    <div class="stat-label">처리 속도</div>
                    <div class="stat-value" id="speedValue">0 건/초</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">남은 시간</div>
                    <div class="stat-value" id="etaValue">계산중...</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">진행 상황</div>
                    <div class="stat-value">
                        <span id="currentValue">0</span> / <span id="totalValue">0</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="result-container" id="resultContainer">
            <div class="success-message">✅ 개인정보 제거가 완료되었습니다!</div>
            <div class="result-stats">
                <div class="result-stat">
                    <div class="result-stat-value" id="processedRows">0</div>
                    <div class="result-stat-label">처리된 행</div>
                </div>
                <div class="result-stat">
                    <div class="result-stat-value" id="removedPii">0</div>
                    <div class="result-stat-label">제거된 개인정보</div>
                </div>
            </div>
            <a class="download-btn" id="downloadLink">📥 처리된 파일 다운로드</a>
        </div>
        
        <div class="error-message" id="errorMessage"></div>
        
        <div class="features">
            <h3>🔐 제거되는 개인정보</h3>
            <ul class="feature-list">
                <li>한국 이름 (김철수, 최민정 등)</li>
                <li>연락처 (010-1234-5678, 053-714-6461 등)</li>
                <li>이메일 주소 (hazard72@ex.co.kr 등)</li>
                <li>차량번호 (12가3456, 울산34나5678 등)</li>
                <li>담당자 정보 (정제호 대리, 박미경 주임 등)</li>
                <li>기관 연락처 (한국도로공사 지사 정보)</li>
            </ul>
        </div>
    </div>

    <script>
        let progressInterval;
        
        // DOM 요소들
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const progressSection = document.getElementById('progressSection');
        const resultContainer = document.getElementById('resultContainer');
        const errorMessage = document.getElementById('errorMessage');
        
        // 이벤트 리스너 설정
        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileSelect);
        
        // 드래그 앤 드롭 이벤트
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
        
        function handleFileSelect(e) {
            const file = e.target.files[0];
            if (file) {
                handleFile(file);
            }
        }
        
        function handleFile(file) {
            if (!file.name.match(/\\.(xlsx|xls)$/i)) {
                showError('Excel 파일만 업로드 가능합니다.');
                return;
            }
            
            uploadFile(file);
        }
        
        function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            // UI 상태 초기화
            hideAllSections();
            progressSection.style.display = 'block';
            
            // 진행률 모니터링 시작
            startProgressMonitoring();
            
            // 파일 업로드
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                stopProgressMonitoring();
                
                if (data.success) {
                    showResult(data);
                } else {
                    showError(data.error || '파일 처리 중 오류가 발생했습니다.');
                }
            })
            .catch(error => {
                stopProgressMonitoring();
                showError('업로드 중 오류가 발생했습니다: ' + error.message);
            });
        }
        
        function startProgressMonitoring() {
            progressInterval = setInterval(() => {
                fetch('/progress')
                    .then(response => response.json())
                    .then(data => {
                        updateProgressDisplay(data);
                        
                        // 완료 시 모니터링 중지
                        if (data.percentage >= 100) {
                            stopProgressMonitoring();
                        }
                    })
                    .catch(error => {
                        console.error('Progress monitoring error:', error);
                    });
            }, 1000); // 1초마다 확인
        }
        
        function stopProgressMonitoring() {
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }
        }
        
        function updateProgressDisplay(data) {
            const progressBar = document.getElementById('progressBar');
            const speedValue = document.getElementById('speedValue');
            const etaValue = document.getElementById('etaValue');
            const currentValue = document.getElementById('currentValue');
            const totalValue = document.getElementById('totalValue');
            
            // 진행률 바 업데이트
            const percentage = Math.round(data.percentage);
            progressBar.style.width = percentage + '%';
            progressBar.textContent = percentage + '%';
            
            // 통계 업데이트
            speedValue.textContent = data.speed.toFixed(1) + ' 건/초';
            etaValue.textContent = data.eta && data.eta !== 'Unknown' ? data.eta : '계산중...';
            currentValue.textContent = data.processed.toLocaleString();
            totalValue.textContent = data.total.toLocaleString();
        }
        
        function showResult(data) {
            hideAllSections();
            resultContainer.style.display = 'block';
            
            // 결과 통계 업데이트
            document.getElementById('processedRows').textContent = data.processed_rows.toLocaleString();
            document.getElementById('removedPii').textContent = data.pii_removed.toLocaleString();
            
            // 다운로드 링크 설정
            const downloadLink = document.getElementById('downloadLink');
            downloadLink.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${data.file_data}`;
            downloadLink.download = data.filename;
        }
        
        function showError(message) {
            hideAllSections();
            errorMessage.textContent = message;
            errorMessage.style.display = 'block';
        }
        
        function hideAllSections() {
            progressSection.style.display = 'none';
            resultContainer.style.display = 'none';
            errorMessage.style.display = 'none';
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route("/progress")
def progress():
    """진행률 조회 API"""
    return jsonify(progress_tracker.get_progress())


@app.route("/progress-stream")
def progress_stream():
    """실시간 진행률 스트림 (Server-Sent Events)"""

    def generate():
        while True:
            progress_data = progress_tracker.get_progress()
            yield f"data: {jsonify(progress_data).get_data(as_text=True)}\n\n"
            time.sleep(1)  # 1초마다 업데이트

            # 완료되면 스트림 종료
            if progress_data["percentage"] >= 100:
                break

    return Response(generate(), mimetype="text/plain")


@app.route("/upload", methods=["POST"])
def upload_file():
    """파일 업로드 및 처리"""
    import gc  # 함수 내에서 gc 모듈 확실히 사용할 수 있도록 추가

    temp_input_file = None
    temp_output_file = None

    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "파일이 선택되지 않았습니다."})

        file = request.files["file"]
        if file.filename == "" or file.filename is None:
            return jsonify({"success": False, "error": "파일이 선택되지 않았습니다."})

        if not file.filename.lower().endswith((".xlsx", ".xls")):
            return jsonify(
                {"success": False, "error": "Excel 파일만 업로드 가능합니다."}
            )

        # 원본 파일명 미리 저장
        original_filename = file.filename
        
        # 처리 모드 확인
        processing_mode = request.form.get('processing_mode', 'llm')
        use_llm = (processing_mode == 'llm')

        # 안전한 임시 파일 처리 (시스템 임시 디렉토리 사용)

        # 시스템 임시 디렉토리에 고유한 파일 생성
        temp_dir = tempfile.gettempdir()
        temp_id = str(uuid.uuid4())[:8]
        temp_input_file = os.path.join(temp_dir, f"korea_pii_input_{temp_id}.xlsx")
        temp_output_file = os.path.join(temp_dir, f"korea_pii_output_{temp_id}.xlsx")

        print(f"임시 파일 생성: {temp_input_file}")

        # 파일 저장 전 기존 파일 확인 및 삭제
        if os.path.exists(temp_input_file):
            try:
                os.remove(temp_input_file)
            except:
                pass

        # 안전한 파일 저장
        try:
            file.save(temp_input_file)
            # 파일 스트림 강제 플러시
            file.stream.flush() if hasattr(file, "stream") else None
        except Exception as save_error:
            raise Exception(f"파일 저장 실패: {save_error}")

        # 파일 핸들 명시적 해제 및 가비지 컬렉션
        file.close() if hasattr(file, "close") else None
        del file
        gc.collect()

        # 파일이 실제로 저장되었는지 확인
        if not os.path.exists(temp_input_file):
            raise Exception("임시 파일 저장 실패")

        # 파일 접근 권한 확인
        try:
            with open(temp_input_file, "rb") as test_file:
                test_file.read(1)  # 1바이트만 읽어서 접근 가능한지 테스트
        except Exception as access_error:
            raise Exception(f"임시 파일 접근 실패: {access_error}")

        print(f"임시 파일 저장 완료: {os.path.getsize(temp_input_file)} bytes")

        # PII 제거 처리 (파일 잠금 방지 강화)
        remover = get_pii_remover(use_llm=use_llm)

        # 최대 재시도 횟수
        max_retries = 5  # 재시도 횟수 증가
        retry_count = 0
        processing_success = False

        while retry_count < max_retries and not processing_success:
            try:
                print(f"PII 처리 시도 {retry_count + 1}/{max_retries}")

                # 처리 전 잠시 대기 (파일 시스템 안정화)
                if retry_count > 0:
                    time.sleep(retry_count * 0.5)  # 점진적 대기 시간 증가

                # 파일 처리
                output_file = remover.process_expressway_file(
                    temp_input_file, temp_output_file
                )
                processing_success = True
                print(f"PII 처리 성공: {output_file}")

            except PermissionError as pe:
                retry_count += 1
                print(f"파일 잠금 오류, 재시도 {retry_count}/{max_retries}: {pe}")

                # 파일 핸들 강제 해제 시도
                gc.collect()

                if retry_count >= max_retries:
                    raise Exception(f"파일 처리 실패 (최대 재시도 초과): {pe}")

            except Exception as e:
                retry_count += 1
                print(f"처리 오류, 재시도 {retry_count}/{max_retries}: {e}")

                if retry_count >= max_retries:
                    raise Exception(f"파일 처리 실패: {e}")

        if not processing_success:
            raise Exception("파일 처리에 실패했습니다.")

        # 출력 파일이 생성되었는지 확인
        if not os.path.exists(output_file):
            raise Exception(f"처리된 파일이 생성되지 않았습니다: {output_file}")

        # 출력 파일 크기 확인
        output_size = os.path.getsize(output_file)
        if output_size == 0:
            raise Exception("처리된 파일이 비어있습니다.")

        print(f"처리된 파일 확인: {output_size} bytes")

        # 사용자 다운로드 폴더에 파일 저장 대신 base64로 인코딩하여 반환
        file_data = None
        read_attempts = 3

        for attempt in range(read_attempts):
            try:
                if attempt > 0:
                    time.sleep(0.5)

                with open(output_file, "rb") as f:
                    raw_data = f.read()
                    file_data = base64.b64encode(raw_data).decode("utf-8")
                break

            except PermissionError as pe:
                if attempt < read_attempts - 1:
                    print(f"파일 읽기 재시도 {attempt + 1}/{read_attempts}: {pe}")
                    gc.collect()
                else:
                    raise Exception(f"처리된 파일 읽기 실패: {pe}")
            except Exception as e:
                if attempt < read_attempts - 1:
                    print(f"파일 읽기 재시도 {attempt + 1}/{read_attempts}: {e}")
                else:
                    raise Exception(f"파일 읽기 오류: {e}")

        if file_data is None:
            raise Exception("파일 데이터를 읽을 수 없습니다.")

        # 결과 통계 가져오기
        stats = progress_tracker.get_final_stats()

        # 최종 파일명 생성
        base_name = os.path.splitext(original_filename)[0]
        extension = os.path.splitext(original_filename)[1]
        mode_suffix = "_LLM" if use_llm else "_정규식"
        final_filename = f"{base_name}_PII_제거완료{mode_suffix}{extension}"
        
        # 메시지에 모드 정보 포함
        mode_text = "LLM 모드" if use_llm else "정규식 모드"
        success_message = f"개인정보 제거가 완료되었습니다 ({mode_text})"

        return jsonify(
            {
                "success": True,
                "file_data": file_data,
                "filename": final_filename,
                "processed_rows": int(stats.get("total_rows", 0)),
                "pii_removed": int(stats.get("total_pii_removed", 0)),
                "message": success_message,
                "processing_mode": processing_mode,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"처리 중 오류 발생: {str(e)}"})

    finally:
        # 임시 파일 정리 (Windows 파일 잠금 고려 - 강화된 버전)
        import gc

        # 가비지 컬렉션 강제 실행
        gc.collect()

        cleanup_files = []
        if temp_input_file:
            cleanup_files.append(temp_input_file)
        if temp_output_file and "output_file" in locals():
            cleanup_files.append(output_file)

        for temp_file in cleanup_files:
            if temp_file and os.path.exists(temp_file):
                file_deleted = False

                # 최대 5회 재시도로 강화
                for attempt in range(5):
                    try:
                        # 파일 속성을 읽기/쓰기 가능으로 변경
                        try:
                            os.chmod(temp_file, 0o777)
                        except:
                            pass

                        # 파일 삭제
                        os.unlink(temp_file)
                        file_deleted = True
                        print(f"임시 파일 삭제 성공: {os.path.basename(temp_file)}")
                        break

                    except PermissionError as pe:
                        if attempt < 4:
                            print(
                                f"파일 삭제 재시도 {attempt + 1}/5: {os.path.basename(temp_file)}"
                            )
                            # 점진적으로 대기 시간 증가
                            time.sleep((attempt + 1) * 0.5)
                            # 가비지 컬렉션 재실행
                            gc.collect()
                        else:
                            print(f"[경고] 임시 파일 삭제 최종 실패: {temp_file}")
                            print(f"   파일은 시스템에서 자동으로 정리됩니다: {pe}")

                    except Exception as cleanup_error:
                        print(f"[경고] 파일 정리 중 예외: {cleanup_error}")
                        break

                if not file_deleted and os.path.exists(temp_file):
                    print(f"[경고] 파일 삭제 미완료: {temp_file}")
                    print("   시스템 재시작 후 수동으로 정리하시기 바랍니다.")


@app.route("/download/<filename>")
def download_file(filename):
    """처리된 파일 다운로드"""
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return "파일을 찾을 수 없습니다.", 404
    except Exception as e:
        return f"다운로드 중 오류: {str(e)}", 500


def main():
    """메인 실행 함수"""
    try:
        print("한국도로공사 민원 개인정보 제거 시스템 시작")
        print("순서 무관 다중패스 처리 지원")
        print("웹 UI: http://localhost:5000")
        print("서버 시작 중...")
    except UnicodeEncodeError:
        print("Korean Expressway PII Removal System Starting")
        print("Web UI: http://localhost:5000")
        print("Starting server...")

    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
