#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국도로공사 민원 데이터 개인정보 제거 - 간단 사용법
"""

from expressway_pii_remover import process_expressway_file, KoreaExpresswayPIIRemover


def quick_usage_guide():
    """빠른 사용 가이드"""

    print("🛣️ 한국도로공사 민원 데이터 개인정보 제거 도구")
    print("=" * 60)

    print("\n🎯 이 도구가 처리하는 개인정보:")
    processed_info = [
        "👤 담당자 이름: '정제호 대리', '이영희 주임', '박철수 과장' → [담당자명]",
        "📞 연락처: '053-714-6461', '010-1234-5678' → [연락처]",
        "📧 이메일: 'hazard72@ex.co.kr', 'min.choi@ex.co.kr' → [이메일주소]",
        "🏢 기관정보: '한국도로공사 군위지사 교통안전팀 (담당자...)' → [기관연락처정보]",
        "📋 담당자정보: '(담당자 정제호 대리, 053-714-6461, ...)' → [담당자연락처정보]",
    ]

    for info in processed_info:
        print(f"  {info}")

    print("\n📖 사용법:")
    print("```python")
    print("from expressway_pii_remover import process_expressway_file")
    print("")
    print("# 가장 간단한 사용법")
    print("process_expressway_file('민원데이터.xlsx')")
    print("")
    print("# 출력 파일명 지정")
    print("process_expressway_file('민원데이터.xlsx', '처리완료.xlsx')")
    print("```")


def show_examples():
    """처리 예시 보여주기"""

    print("\n" + "=" * 60)
    print("📋 처리 전후 비교 예시")
    print("=" * 60)

    examples = [
        {
            "title": "담당자 정보 마스킹",
            "before": "고객님 안녕하십니까. 군위지사 교통안전팀 정제호 대리입니다.",
            "after": "고객님 안녕하십니까. 군위지사 교통안전팀 [담당자명]입니다.",
        },
        {
            "title": "한국도로공사 연락처 정보 전체 마스킹",
            "before": "한국도로공사 군위지사 교통안전팀 (담당자 정제호 대리, 053-714-6461, hazard72@ex.co.kr)으로 문의하여 주시기 바랍니다.",
            "after": "[기관연락처정보]으로 문의하여 주시기 바랍니다.",
        },
        {
            "title": "일반 연락처 마스킹",
            "before": "제 연락처는 010-1234-5678입니다.",
            "after": "제 연락처는 [연락처]입니다.",
        },
        {
            "title": "이메일 마스킹",
            "before": "울산지사 도로관리팀 최민정 대리(052-987-6543, min.choi@ex.co.kr)입니다.",
            "after": "울산지사 도로관리팀 [담당자명]([연락처], [이메일주소])입니다.",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n🔸 예시 {i}: {example['title']}")
        print(f"   처리 전: {example['before']}")
        print(f"   처리 후: {example['after']}")


def step_by_step():
    """단계별 가이드"""

    print("\n" + "=" * 60)
    print("📖 단계별 사용 가이드")
    print("=" * 60)

    steps = [
        "1️⃣ 민원 엑셀 파일 준비",
        "   - 컬럼: 접수채널, 서비스유형(대), 서비스유형(중), 서비스유형(소),",
        "          민원제목, 질문내용, 처리일자, 처리기관, 답변내용",
        "",
        "2️⃣ Python 스크립트 작성",
        "   ```python",
        "   from expressway_pii_remover import process_expressway_file",
        "   process_expressway_file('민원데이터.xlsx')",
        "   ```",
        "",
        "3️⃣ 스크립트 실행",
        "   - 자동으로 '질문내용'과 '답변내용' 컬럼에서 개인정보 탐지",
        "   - 담당자명, 연락처, 이메일, 기관정보 마스킹",
        "",
        "4️⃣ 결과 확인",
        "   - '파일명_개인정보제거.xlsx' 파일 생성됨",
        "   - 원본 파일은 그대로 보존됨",
        "",
        "5️⃣ 검토 및 완료",
        "   - 처리 결과 검토 후 원본 파일 삭제 또는 보관",
    ]

    for step in steps:
        print(step)


def advanced_usage():
    """고급 사용법"""

    print("\n" + "=" * 60)
    print("🔧 고급 사용법")
    print("=" * 60)

    print("\n📋 미리보기 기능:")
    print("```python")
    print("from expressway_pii_remover import KoreaExpresswayPIIRemover")
    print("")
    print("remover = KoreaExpresswayPIIRemover()")
    print("remover.preview_changes('민원데이터.xlsx')  # 처리 전후 비교")
    print("```")

    print("\n📋 커스터마이징:")
    print("```python")
    print("# 특정 컬럼만 처리하고 싶은 경우")
    print("# expressway_pii_remover.py 파일에서")
    print("# target_columns = ['질문내용', '답변내용'] 부분을")
    print("# target_columns = ['원하는컬럼명'] 으로 수정")
    print("```")


def test_with_sample():
    """샘플 데이터로 테스트"""

    print("\n" + "=" * 60)
    print("🧪 샘플 데이터로 테스트")
    print("=" * 60)

    print("테스트를 위한 샘플 파일이 생성됩니다...")

    try:
        from expressway_pii_remover import create_test_data

        test_file = create_test_data()

        print(f"✅ 테스트 파일 생성됨: {test_file}")
        print("\n이제 다음 명령어로 테스트할 수 있습니다:")
        print(f"process_expressway_file('{test_file}')")

        return test_file
    except Exception as e:
        print(f"❌ 테스트 파일 생성 실패: {e}")
        return None


if __name__ == "__main__":
    quick_usage_guide()
    show_examples()
    step_by_step()
    advanced_usage()

    print("\n" + "=" * 60)
    print("🔥 실제 사용 예시")
    print("=" * 60)

    # 샘플 테스트
    test_file = test_with_sample()

    if test_file:
        print(f"\n🚀 실제 처리 시작...")
        try:
            result = process_expressway_file(test_file)
            if result:
                print(f"✅ 처리 완료: {result}")
        except Exception as e:
            print(f"❌ 처리 중 오류: {e}")

    print("\n" + "=" * 60)
    print("✅ 이제 여러분의 한국도로공사 민원 데이터를 안전하게 처리할 수 있습니다!")
    print("📞 지원이 필요하시면 언제든 문의해주세요.")
    print("=" * 60)
