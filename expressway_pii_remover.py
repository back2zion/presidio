#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국도로공사 민원 데이터 개인정보 제거 도구
특정 패턴의 담당자 정보, 연락처, 이메일을 마스킹 처리
"""

import pandas as pd
import re
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer import PatternRecognizer
import os


class KoreaExpresswayPIIRemover:
    def __init__(self):
        """한국도로공사 민원 데이터용 개인정보 제거 클래스"""
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # 커스텀 인식기 추가
        self._add_custom_recognizers()

        # 익명화 설정
        self.operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[담당자명]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[이메일주소]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[연락처]"}),
            "KOREAN_STAFF": OperatorConfig("replace", {"new_value": "[담당자명]"}),
            "KOREAN_CONTACT": OperatorConfig("replace", {"new_value": "[연락처]"}),
            "ORGANIZATION_INFO": OperatorConfig("replace", {"new_value": "[기관정보]"}),
        }

    def _add_custom_recognizers(self):
        """한국도로공사 민원 데이터에 특화된 인식기 추가"""

        # 담당자 이름 패턴 (예: "정제호 대리", "김철수 주임")
        staff_recognizer = PatternRecognizer(
            supported_entity="KOREAN_STAFF",
            patterns=[
                {
                    "pattern": r"([가-힣]{2,4})\s*(대리|주임|사원|과장|차장|부장|팀장|실장|소장|지사장)",
                    "score": 0.9,
                },
                {
                    "pattern": r"담당자\s*([가-힣]{2,4})\s*(대리|주임|사원|과장|차장|부장|팀장)",
                    "score": 0.9,
                },
                {"pattern": r"([가-힣]{2,4})\s*담당자", "score": 0.8},
            ],
            name="korean_staff_recognizer",
            context=["담당자", "대리", "주임", "과장", "팀장", "안녕하십니까"],
        )

        # 일반 한국어 이름 패턴 (질문내용에서 개인 이름 탐지)
        korean_name_recognizer = PatternRecognizer(
            supported_entity="KOREAN_NAME",
            patterns=[
                # "제 이름은 김철수이고" 패턴
                {
                    "pattern": r"(?:제|내)\s*이름은\s*([가-힣]{2,4})(?:이고|입니다|이며)",
                    "score": 0.95,
                },
                # "저는 김철수입니다" 패턴
                {"pattern": r"저는\s*([가-힣]{2,4})입니다", "score": 0.9},
                # "김철수라고 합니다" 패턴
                {"pattern": r"([가-힣]{2,4})(?:라고|이라고)\s*합니다", "score": 0.9},
                # "김철수(010-1234-5678)" 패턴 - 이름 뒤에 연락처
                {"pattern": r"([가-힣]{2,4})\s*\([0-9-]+\)", "score": 0.85},
                # "연락처는... 김철수입니다" 문맥상 이름
                {
                    "pattern": r"(?:연락처|전화번호).*?([가-힣]{2,4})입니다",
                    "score": 0.8,
                },
                # 일반적인 한국어 이름 (2-4글자, 특정 맥락에서)
                {
                    "pattern": r"\b([가-힣]{2,4})(?=입니다|이고|이며|님|씨)",
                    "score": 0.7,
                },
            ],
            name="korean_name_recognizer",
            context=["이름", "성명", "저는", "제", "연락처", "신고", "문의"],
        )  # 한국도로공사 연락처 패턴
        contact_recognizer = PatternRecognizer(
            supported_entity="KOREAN_CONTACT",
            patterns=[
                {"pattern": r"0\d{1,2}-\d{3,4}-\d{4}", "score": 0.9},
                {"pattern": r"0\d{1,2}\s*-\s*\d{3,4}\s*-\s*\d{4}", "score": 0.9},
                {"pattern": r"\d{3}-\d{3,4}-\d{4}", "score": 0.8},
            ],
            name="korean_contact_recognizer",
            context=["연락처", "전화", "문의", "연락", "TEL"],
        )

        # 기관 정보 패턴 (예: "한국도로공사 군위지사 교통안전팀 (담당자 정제호 대리, 053-714-6461, hazard72@ex.co.kr)")
        org_info_recognizer = PatternRecognizer(
            supported_entity="ORGANIZATION_INFO",
            patterns=[
                {
                    "pattern": r"한국도로공사\s+[가-힣]+지사\s+[가-힣]+팀\s*\([^)]+\)",
                    "score": 0.95,
                },
                {
                    "pattern": r"한국도로공사\s+[^)]+\([^)]*\d{3}-\d{3,4}-\d{4}[^)]*\)",
                    "score": 0.9,
                },
                {
                    "pattern": r"\([^)]*담당자[^)]*\d{3}-\d{3,4}-\d{4}[^)]*\)",
                    "score": 0.85,
                },
            ],
            name="organization_info_recognizer",
            context=["한국도로공사", "담당자", "지사", "팀", "문의하여"],
        )

        # 분석기에 커스텀 인식기 추가
        self.analyzer.registry.add_recognizer(staff_recognizer)
        self.analyzer.registry.add_recognizer(korean_name_recognizer)
        self.analyzer.registry.add_recognizer(contact_recognizer)
        self.analyzer.registry.add_recognizer(org_info_recognizer)

    def _advanced_text_processing(self, text):
        """고급 텍스트 전처리 및 패턴 매칭"""
        if pd.isna(text) or not text or str(text).strip() == "":
            return text

        text_str = str(text)

        # 1단계: 정규식으로 특정 패턴 직접 처리
        patterns_to_replace = [
            # 한국도로공사 뒤의 모든 정보 마스킹
            (
                r"한국도로공사\s+[가-힣]+지사\s+[가-힣]+팀\s*\([^)]+\)",
                "[기관연락처정보]",
            ),
            # 담당자 정보가 포함된 괄호 전체 마스킹
            (r"\(담당자[^)]*\d{3}-\d{3,4}-\d{4}[^)]*\)", "[담당자연락처정보]"),
            # 이름 + 직급 + 연락처 패턴 (우선 처리)
            (
                r"([가-힣]{2,4})\s*(대리|주임|사원|과장|차장|부장|팀장|실장|소장)\s*\([0-9-]+\)",
                "[담당자명]([연락처])",
            ),
            # 개인 이름 패턴들
            (
                r"(?:제|내)\s*이름은\s*([가-힣]{2,4})(?:이고|입니다|이며)",
                "제 이름은 [이름]이고",
            ),
            (r"저는\s*([가-힣]{2,4})입니다", "저는 [이름]입니다"),
            (r"([가-힣]{2,4})(?:라고|이라고)\s*합니다", "[이름]라고 합니다"),
            (r"([가-힣]{2,4})\s*\([0-9-]+\)", "[이름]([연락처])"),
            (r"신고자\s*이름:\s*([가-힣]{2,4})", "신고자 이름: [이름]"),
            # 차량번호 패턴 (한국 차량번호 형식)
            (r"\d{2,3}[가-힣]\d{4}", "[차량번호]"),  # 12가3456 형식
            (r"[가-힣]{2}\d{2}[가-힣]\d{4}", "[차량번호]"),  # 서울12가3456 형식
            (r"\d{3}[가-힣]\d{4}", "[차량번호]"),  # 123가4567 형식
            (r"[가-힣]\d{2}[가-힣]\d{4}", "[차량번호]"),  # 가12나3456 형식
            # 이름 + 직급 패턴 (일반)
            (
                r"([가-힣]{2,4})\s*(대리|주임|사원|과장|차장|부장|팀장|실장|소장)",
                "[담당자명]",
            ),
            # 전화번호 패턴
            (r"0\d{1,2}[-\s]*\d{3,4}[-\s]*\d{4}", "[연락처]"),
            # 이메일 패턴 (@ex.co.kr 도메인 포함)
            (r"[a-zA-Z0-9._%+-]+@ex\.co\.kr", "[이메일주소]"),
            (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[이메일주소]"),
        ]

        processed_text = text_str
        for pattern, replacement in patterns_to_replace:
            processed_text = re.sub(pattern, replacement, processed_text)

        return processed_text

    def process_text(self, text):
        """텍스트에서 개인정보 제거 (정규식 + Presidio 결합)"""
        if pd.isna(text) or not text or str(text).strip() == "":
            return text

        # 1단계: 고급 정규식 처리
        processed_text = self._advanced_text_processing(text)

        # 2단계: Presidio로 추가 개인정보 탐지
        try:
            results = self.analyzer.analyze(text=processed_text, language="en")

            if results:
                anonymized_result = self.anonymizer.anonymize(
                    text=processed_text,
                    analyzer_results=results,
                    operators=self.operators,
                )
                return anonymized_result.text
            else:
                return processed_text
        except Exception as e:
            print(f"  ⚠️ Presidio 처리 중 오류 (정규식 결과 반환): {e}")
            return processed_text

    def process_excel_file(self, input_file_path, output_file_path=None):
        """
        한국도로공사 민원 엑셀 파일 처리

        Args:
            input_file_path (str): 입력 엑셀 파일 경로
            output_file_path (str): 출력 파일 경로
        """

        print(f"📁 한국도로공사 민원 데이터 읽는 중: {input_file_path}")

        try:
            df = pd.read_excel(input_file_path)
        except Exception as e:
            print(f"❌ 파일 읽기 오류: {e}")
            return None

        print(f"📊 데이터 크기: {df.shape[0]}행 x {df.shape[1]}열")
        print(f"📋 컬럼명: {list(df.columns)}")

        # 주요 처리 대상 컬럼 식별
        target_columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            if any(
                keyword in col_lower
                for keyword in ["질문내용", "답변내용", "민원내용", "처리내용", "내용"]
            ):
                target_columns.append(col)

        if not target_columns:
            print(
                "⚠️ 질문내용/답변내용 컬럼을 찾을 수 없습니다. 모든 텍스트 컬럼을 처리합니다."
            )
            target_columns = [col for col in df.columns if df[col].dtype == "object"]

        print(f"🎯 처리할 컬럼: {target_columns}")

        # 통계 초기화
        total_changes = 0
        column_stats = {}

        # 각 컬럼 처리
        for column in target_columns:
            print(f"\n🔍 '{column}' 컬럼 처리 중...")
            column_changes = 0

            for idx, value in df[column].items():
                if pd.notna(value) and str(value).strip():
                    original_value = str(value)
                    processed_value = self.process_text(original_value)

                    if processed_value != original_value:
                        df.at[idx, column] = processed_value
                        column_changes += 1
                        total_changes += 1

                        # 첫 3개 변경사항만 출력
                        if column_changes <= 3:
                            print(f"  변경 {column_changes}: ")
                            print(f"    원본: {original_value[:100]}...")
                            print(f"    처리: {processed_value[:100]}...")
                            print()

            column_stats[column] = column_changes
            print(f"  ✅ '{column}' 컬럼에서 {column_changes}개 항목 수정됨")

        print(f"\n📊 전체 처리 통계:")
        print(f"   총 수정된 항목: {total_changes}개")
        for col, count in column_stats.items():
            if count > 0:
                print(f"   - {col}: {count}개")

        # 출력 파일명 생성
        if output_file_path is None:
            base_name = os.path.splitext(input_file_path)[0]
            output_file_path = f"{base_name}_개인정보제거.xlsx"

        # 결과 저장
        try:
            df.to_excel(output_file_path, index=False)
            print(f"\n✅ 처리 완료! 결과 파일: {output_file_path}")
            return output_file_path
        except Exception as e:
            print(f"❌ 파일 저장 오류: {e}")
            return None

    def preview_changes(self, input_file_path, num_samples=3):
        """처리 전후 비교 미리보기"""
        print(f"🔍 처리 미리보기: {input_file_path}")

        try:
            df = pd.read_excel(input_file_path)
        except Exception as e:
            print(f"❌ 파일 읽기 오류: {e}")
            return

        # 질문내용과 답변내용 컬럼 찾기
        content_columns = []
        for col in df.columns:
            if any(keyword in str(col) for keyword in ["질문내용", "답변내용", "내용"]):
                content_columns.append(col)

        if not content_columns:
            print("질문내용/답변내용 컬럼을 찾을 수 없습니다.")
            return

        print(f"📋 미리보기 대상 컬럼: {content_columns}")

        sample_count = 0
        for col in content_columns:
            print(f"\n🔸 {col} 컬럼 샘플:")
            for idx, value in df[col].items():
                if (
                    pd.notna(value)
                    and str(value).strip()
                    and sample_count < num_samples
                ):
                    original = str(value)
                    processed = self.process_text(original)

                    if processed != original:
                        sample_count += 1
                        print(f"\n샘플 {sample_count}:")
                        print(f"원본: {original}")
                        print(f"처리: {processed}")
                        print("-" * 50)

                        if sample_count >= num_samples:
                            break


def create_test_data():
    """테스트용 한국도로공사 민원 데이터 생성"""
    test_data = {
        "접수채널": ["홈페이지", "전화", "방문", "이메일"],
        "서비스유형(대)": ["도로관리", "통행료", "시설이용", "기타"],
        "서비스유형(중)": ["도로보수", "요금문의", "휴게소", "민원신청"],
        "서비스유형(소)": ["포트홀", "하이패스", "화장실", "기타"],
        "민원제목": ["도로 파손 신고", "통행료 문의", "휴게소 이용 불편", "기타 문의"],
        "질문내용": [
            "고속도로 1번 구간에 포트홀이 발생하여 신고드립니다. 제 이름은 김철수이고 연락처는 010-1234-5678입니다.",
            "하이패스 요금이 잘못 부과된 것 같습니다. 확인 부탁드립니다.",
            "휴게소 화장실이 너무 더럽습니다. 개선이 필요합니다.",
            "도로 표지판이 잘 안 보입니다. 박민수(010-9876-5432)입니다.",
        ],
        "처리일자": ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18"],
        "처리기관": ["군위지사", "대구지사", "부산지사", "울산지사"],
        "답변내용": [
            "고객님 안녕하십니까. 군위지사 교통안전팀 정제호 대리입니다. 신고해주신 포트홀 관련 조치를 완료하였습니다. 추가적으로 문의사항이 있으시면 한국도로공사 군위지사 교통안전팀 (담당자 정제호 대리, 053-714-6461, hazard72@ex.co.kr)으로 문의하여 주시기 바랍니다.",
            "안녕하십니까. 대구지사 요금관리팀 이영희 주임입니다. 하이패스 요금 관련 확인 결과 정상 부과되었습니다.",
            "고객님의 불편사항을 확인하였습니다. 부산지사 시설관리팀 박철수 과장(051-123-4567)이 조치하겠습니다.",
            "표지판 개선 작업을 진행하겠습니다. 울산지사 도로관리팀 최민정 대리(052-987-6543, min.choi@ex.co.kr)입니다.",
        ],
    }

    df = pd.DataFrame(test_data)
    test_file = "한국도로공사_민원_테스트데이터.xlsx"
    df.to_excel(test_file, index=False)
    print(f"📁 테스트 파일 생성: {test_file}")
    return test_file


def main():
    """메인 함수"""
    print("🛣️ 한국도로공사 민원 데이터 개인정보 제거 도구")
    print("=" * 60)

    # 도구 초기화
    pii_remover = KoreaExpresswayPIIRemover()

    # 1. 테스트 데이터 생성
    print("\n1️⃣ 테스트 데이터 생성")
    test_file = create_test_data()

    # 2. 처리 미리보기
    print("\n2️⃣ 처리 미리보기")
    pii_remover.preview_changes(test_file)

    # 3. 실제 처리
    print("\n3️⃣ 실제 파일 처리")
    output_file = pii_remover.process_excel_file(test_file)

    # 4. 결과 확인
    if output_file:
        print(f"\n4️⃣ 처리 결과 확인")
        result_df = pd.read_excel(output_file)
        print("\n처리된 답변내용 샘플:")
        for idx, content in enumerate(result_df["답변내용"]):
            print(f"\n{idx+1}. {content}")

    print("\n✅ 테스트 완료!")


# 간단한 사용 함수
def process_expressway_file(input_file, output_file=None):
    """
    한국도로공사 민원 파일 처리 간단 함수

    Args:
        input_file (str): 입력 파일 경로
        output_file (str): 출력 파일 경로 (선택사항)

    Usage:
        process_expressway_file("민원데이터.xlsx")
    """
    remover = KoreaExpresswayPIIRemover()
    return remover.process_excel_file(input_file, output_file)


if __name__ == "__main__":
    main()
