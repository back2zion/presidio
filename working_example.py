#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Presidio 기본 사용법 - 한국어 지원
"""

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine


def basic_example():
    """기본적인 Presidio 사용법"""

    print("🇺🇸 영어 개인정보 식별 및 익명화 예제")
    print("=" * 50)

    # 기본 분석기와 익명화기 초기화
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()

    # 테스트 텍스트 (영어)
    text = """
    Hello, my name is John Smith.
    My phone number is 555-123-4567.
    My email address is john.smith@company.com.
    My credit card number is 4532-1234-5678-9012.
    """

    print(f"📝 원본 텍스트:\n{text}")

    # 개인정보 식별
    print("🔍 개인정보 식별 중...")
    results = analyzer.analyze(text=text, language="en")

    print("발견된 개인정보:")
    for result in results:
        detected_text = text[result.start : result.end]
        print(f"  - 유형: {result.entity_type}")
        print(f"    텍스트: '{detected_text}'")
        print(f"    신뢰도: {result.score:.2f}")
        print()

    # 기본 익명화
    print("🔒 기본 익명화:")
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
    print(f"{anonymized_result.text}")

    # 커스텀 익명화
    print("🔒 커스텀 익명화:")
    operators = {
        "PERSON": {"type": "replace", "new_value": "[이름]"},
        "PHONE_NUMBER": {"type": "replace", "new_value": "[전화번호]"},
        "EMAIL_ADDRESS": {"type": "replace", "new_value": "[이메일]"},
        "CREDIT_CARD": {"type": "replace", "new_value": "[신용카드]"},
    }

    custom_anonymized = anonymizer.anonymize(
        text=text, analyzer_results=results, operators=operators
    )
    print(f"{custom_anonymized.text}")


def mixed_text_example():
    """한영 혼합 텍스트 예제"""

    print("🌏 한영 혼합 텍스트 예제")
    print("=" * 50)

    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()

    # 한영 혼합 텍스트
    mixed_text = """
    안녕하세요. Hello, my name is John Smith (김철수).
    Contact: john.smith@company.com, 010-1234-5678
    Credit Card: 4532-1234-5678-9012
    주소: 서울시 강남구, Address: 123 Main St, New York
    """

    print(f"📝 원본 텍스트:\n{mixed_text}")

    # 개인정보 식별
    print("🔍 개인정보 식별 중...")
    results = analyzer.analyze(text=mixed_text, language="en")

    print("발견된 개인정보:")
    for result in results:
        detected_text = mixed_text[result.start : result.end]
        print(f"  - 유형: {result.entity_type}")
        print(f"    텍스트: '{detected_text}'")
        print(f"    신뢰도: {result.score:.2f}")
        print()

    # 익명화
    print("🔒 익명화된 텍스트:")
    anonymized_result = anonymizer.anonymize(text=mixed_text, analyzer_results=results)
    print(f"{anonymized_result.text}")


def masking_example():
    """마스킹 예제"""

    print("🎭 마스킹 예제")
    print("=" * 50)

    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()

    text = "My phone number is 555-123-4567 and email is john.doe@example.com"

    print(f"📝 원본 텍스트:\n{text}")

    # 개인정보 식별
    results = analyzer.analyze(text=text, language="en")

    # 마스킹 설정
    operators = {
        "PHONE_NUMBER": {
            "type": "mask",
            "masking_char": "*",
            "chars_to_mask": 4,
            "from_end": True,
        },
        "EMAIL_ADDRESS": {
            "type": "mask",
            "masking_char": "*",
            "chars_to_mask": 5,
            "from_end": False,
        },
    }

    # 마스킹 적용
    print("🔒 마스킹된 텍스트:")
    masked_result = anonymizer.anonymize(
        text=text, analyzer_results=results, operators=operators
    )
    print(f"{masked_result.text}")


if __name__ == "__main__":
    try:
        print("🚀 Presidio 사용법 데모")
        print("=" * 60)

        # 기본 예제
        basic_example()

        print("\n" + "=" * 60)

        # 한영 혼합 텍스트 예제
        mixed_text_example()

        print("\n" + "=" * 60)

        # 마스킹 예제
        masking_example()

        print("\n✅ 데모 완료!")

        print("\n📖 Presidio 주요 기능:")
        print("1. 개인정보 자동 식별 (이름, 전화번호, 이메일, 신용카드 등)")
        print("2. 다양한 익명화 방법 (대체, 마스킹, 암호화 등)")
        print("3. 커스텀 인식기 추가 가능")
        print("4. 다국어 지원 (주로 영어, 다른 언어는 커스텀 필요)")
        print("5. 높은 정확도와 유연성")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
