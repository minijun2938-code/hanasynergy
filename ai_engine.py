import os
import socket
import prompts
from dotenv import load_dotenv

# OpenAI
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, AuthenticationError, BadRequestError

load_dotenv()


def get_openai_api_key():
    # Streamlit Cloud/로컬에서 키 교체 후 재시작 없이 반영되도록 매번 조회
    return os.getenv("OPENAI_API_KEY")


def get_openai_model():
    # 필요하면 Streamlit Secrets에서 모델 교체 가능
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def init_openai_client():
    api_key = get_openai_api_key()
    if not api_key:
        return None

    # 선택: 프록시/커스텀 엔드포인트가 필요하면 OPENAI_BASE_URL 사용
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _build_prompt(data_a, data_b, name_a, name_b, mode, additional_info):
    if additional_info is None:
        additional_info = {}

    # 모드에 따른 시스템 프롬프트 및 추가 컨텍스트 설정
    if mode == "couple":
        system_prompt = prompts.COUPLE_PROMPT
        gender_a = additional_info.get("gender_a", "미설정")
        gender_b = additional_info.get("gender_b", "미설정")
        context_text = f"관계 유형: 연인 (A: {name_a}/{gender_a}, B: {name_b}/{gender_b})"
    elif mode == "hierarchy":
        system_prompt = prompts.HIERARCHY_PROMPT
        superior = additional_info.get("superior_name", "상사")
        subordinate = additional_info.get("subordinate_name", "부하")
        context_text = f"관계 유형: 상사-부하 (상사: {superior}, 부하: {subordinate})"
    elif mode == "self_mbti":
        system_prompt = prompts.SELF_MBTI_PROMPT
        context_text = f"[분석: MBTI] 대상자: {name_a}"
    elif mode == "self_archetype":
        system_prompt = prompts.SELF_ARCHETYPE_PROMPT
        gender = additional_info.get("gender", "미설정")
        context_text = f"[분석: 에겐테토] 대상자: {name_a} ({gender})"
    elif mode == "self_swot":
        system_prompt = prompts.SELF_SWOT_PROMPT
        context_text = f"[분석: 장단점] 대상자: {name_a}"
    else:
        system_prompt = prompts.COLLEAGUE_PROMPT
        context_text = "관계 유형: 직장 동료"

    # 길이/속도 최적화를 위한 기본 가드(필요하면 prompts.py에서 더 강하게 제한 가능)
    length_hint = "리포트는 너무 길지 않게, 핵심 위주로 1200~1800자 내로 작성해줘."

    if mode.startswith("self"):
        user_content = f"""
{context_text}
[성향 데이터 원문]
- {name_a}: {data_a}

위 데이터를 바탕으로 전문적인 리포트를 작성해줘.
가독성을 위해 헤딩(###)과 이모지를 적극 활용하세요.
{length_hint}
**주의: 데이터 원본 문구를 절대 직접 인용하거나 출력하지 마세요.**
""".strip()
    else:
        user_content = f"""
{context_text}
[성향 데이터 원문]
- 대상자 A({name_a}): {data_a}
- 대상자 B({name_b}): {data_b}

위 데이터를 바탕으로 전문적인 리포트를 작성해줘.
모드별로 완전히 다른 페르소나와 점수 산출 방식을 적용하세요.
{length_hint}
**주의: 데이터 원본 문구를 절대 직접 인용하거나 출력하지 마세요.**
""".strip()

    return system_prompt, user_content


def analyze_compatibility(data_a, data_b, name_a, name_b, mode="colleague", additional_info=None):
    if not get_openai_api_key():
        return "⚠️ OPENAI_API_KEY가 설정되지 않았습니다. 관리자에게 문의하세요."

    client = init_openai_client()
    if not client:
        return "⚠️ OpenAI 클라이언트 초기화에 실패했습니다."

    system_prompt, user_content = _build_prompt(
        data_a=data_a,
        data_b=data_b,
        name_a=name_a,
        name_b=name_b,
        mode=mode,
        additional_info=additional_info,
    )

    try:
        model = get_openai_model()
        # timeout: 무한로딩 방지
        timeout_s = int(os.getenv("OPENAI_TIMEOUT", "60"))

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1200")),
            timeout=timeout_s,
        )
        return resp.choices[0].message.content

    except Exception as e:
        return handle_ai_error(e)


def analyze_team_synergy(team_members, team_name, leader_name):
    if not get_openai_api_key():
        return "⚠️ OPENAI_API_KEY가 설정되지 않았습니다. 관리자에게 문의하세요."

    client = init_openai_client()
    if not client:
        return "⚠️ OpenAI 클라이언트 초기화에 실패했습니다."

    members_data_str = ""
    for member in team_members:
        role = "(리더)" if member[0] == leader_name else "(팀원)"
        members_data_str += f"- {member[0]} {role}: {member[1]}\n"

    system_prompt = prompts.TEAM_SYNERGY_PROMPT.format(
        team_name=team_name,
        leader_name=leader_name,
        members_data=members_data_str,
    )

    try:
        model = get_openai_model()
        timeout_s = int(os.getenv("OPENAI_TIMEOUT", "60"))

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
            ],
            temperature=0.3,
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1200")),
            timeout=timeout_s,
        )
        return resp.choices[0].message.content

    except Exception as e:
        return handle_ai_error(e)


def handle_ai_error(e):
    # OpenAI SDK 예외 매핑 + 혹시 모르는 문자열 에러까지 커버
    if isinstance(e, AuthenticationError):
        return "⚠️ OpenAI API 키가 유효하지 않거나 권한이 없습니다. (OPENAI_API_KEY 확인)"
    if isinstance(e, RateLimitError):
        return "⚠️ 요청이 너무 많거나 한도(레이트리밋/쿼터)에 걸렸습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(e, BadRequestError):
        return "⚠️ 요청 형식이 올바르지 않거나 입력 데이터가 너무 큽니다."
    if isinstance(e, APIConnectionError):
        return "⚠️ OpenAI 연결 오류가 발생했습니다. 네트워크 상태를 확인해 주세요."
    if isinstance(e, APIError):
        return f"⚠️ OpenAI API 오류: {str(e)}"

    # 타임아웃/기타
    if isinstance(e, TimeoutError) or isinstance(e, socket.timeout):
        return "⚠️ 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."

    err_msg = str(e)
    if "429" in err_msg:
        return "⚠️ 요청이 너무 많거나 한도(레이트리밋/쿼터)에 걸렸습니다. 잠시 후 다시 시도해 주세요."
    if "401" in err_msg:
        return "⚠️ OpenAI API 키가 유효하지 않거나 권한이 없습니다. (OPENAI_API_KEY 확인)"
    return f"⚠️ 분석 중 오류가 발생했습니다: {err_msg}"
