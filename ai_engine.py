import os
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv
import prompts

load_dotenv()

def get_api_key():
    # 키를 교체한 뒤 앱을 재시작하지 않아도 반영되도록 매번 조회
    return os.getenv("GOOGLE_API_KEY")

def init_genai():
    api_key = get_api_key()
    if not api_key:
        return None
    # DNS 문제를 해결하기 위해 transport='rest' 사용, 일관성을 위해 온도를 낮게 설정
    genai.configure(api_key=api_key, transport='rest')
    model = genai.GenerativeModel(
        model_name='models/gemini-3-flash-preview',
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 8192,
        }
    )
    return model

def analyze_compatibility(data_a, data_b, name_a, name_b, mode="colleague", additional_info=None):
    if not get_api_key():
        return "⚠️ API 키가 설정되지 않았습니다. 관리자에게 문의하세요."
    
    model = init_genai()
    if additional_info is None:
        additional_info = {}

    # 모드에 따른 시스템 프롬프트 및 추가 컨텍스트 설정
    if mode == "couple":
        system_prompt = prompts.COUPLE_PROMPT
        gender_a = additional_info.get('gender_a', '미설정')
        gender_b = additional_info.get('gender_b', '미설정')
        context_text = f"관계 유형: 연인 (A: {name_a}/{gender_a}, B: {name_b}/{gender_b})"
    elif mode == "hierarchy":
        system_prompt = prompts.HIERARCHY_PROMPT
        superior = additional_info.get('superior_name', '상사')
        subordinate = additional_info.get('subordinate_name', '부하')
        context_text = f"관계 유형: 상사-부하 (상사: {superior}, 부하: {subordinate})"
    elif mode == "self_mbti":
        system_prompt = prompts.SELF_MBTI_PROMPT
        context_text = f"[분석: MBTI] 대상자: {name_a}"
    elif mode == "self_archetype":
        system_prompt = prompts.SELF_ARCHETYPE_PROMPT
        gender = additional_info.get('gender', '미설정')
        context_text = f"[분석: 에겐테토] 대상자: {name_a} ({gender})"
    elif mode == "self_swot":
        system_prompt = prompts.SELF_SWOT_PROMPT
        context_text = f"[분석: 장단점] 대상자: {name_a}"
    else:
        system_prompt = prompts.COLLEAGUE_PROMPT
        context_text = f"관계 유형: 직장 동료"

    if mode.startswith("self"):
        user_content = f"""
        {context_text}
        [성향 데이터 원문]
        - {name_a}: {data_a}
        
        위 데이터를 바탕으로 전문적인 리포트를 작성해줘. 
        가독성을 위해 헤딩(###)과 이모지를 적극 활용하세요.
        **주의: 데이터 원본 문구를 절대 직접 인용하거나 출력하지 마세요.**
        """
    else:
        user_content = f"""
        {context_text}
        [성향 데이터 원문]
        - 대상자 A({name_a}): {data_a}
        - 대상자 B({name_b}): {data_b}
        
        위 데이터를 바탕으로 전문적인 리포트를 작성해줘. 
        모드별로 완전히 다른 페르소나와 점수 산출 방식을 적용하세요.
        **주의: 데이터 원본 문구를 절대 직접 인용하거나 출력하지 마세요.**
        """
    
    try:
        # Streamlit Cloud에서 네트워크/모델 응답 지연 시 무한 스피너를 막기 위해 timeout 설정
        response = model.generate_content([system_prompt, user_content], request_options={"timeout": 60})
        return response.text
    except Exception as e:
        return handle_ai_error(e)

def analyze_team_synergy(team_members, team_name, leader_name):
    if not get_api_key():
        return "⚠️ API 키가 설정되지 않았습니다. 관리자에게 문의하세요."
    
    model = init_genai()
    
    # 멤버 데이터를 문자열로 변환
    members_data_str = ""
    for member in team_members:
        # member: (name, profile_data, emp_id)
        role = "(리더)" if member[0] == leader_name else "(팀원)"
        members_data_str += f"- {member[0]} {role}: {member[1]}\n"

    system_prompt = prompts.TEAM_SYNERGY_PROMPT.format(
        team_name=team_name,
        leader_name=leader_name,
        members_data=members_data_str
    )
    
    try:
        response = model.generate_content(system_prompt, request_options={"timeout": 60})
        return response.text
    except Exception as e:
        return handle_ai_error(e)

def handle_ai_error(e):
    err_msg = str(e)
    if "Resource exhausted" in err_msg:
        return f"⚠️ 하루 사용량(Quota) 초과 또는 요금제 한도 부족입니다. (Error: {err_msg})"
    elif "429" in err_msg:
        return f"⚠️ 짧은 시간에 너무 많은 요청이 있었습니다. 잠시 후 다시 시도해 주세요. (Rate Limit)"
    elif "401" in err_msg or "Unauthenticated" in err_msg:
        return "⚠️ API 키가 유효하지 않거나 만료되었습니다. 설정을 확인해 주세요."
    elif "400" in err_msg or "InvalidArgument" in err_msg:
        return "⚠️ 입력된 데이터 형식이 올바르지 않거나 데이터가 너무 큽니다."
    elif "DeadlineExceeded" in err_msg:
        return "⚠️ 분석 시간이 너무 오래 걸려 중단되었습니다. 잠시 후 다시 시도해 주세요."
    return f"⚠️ 분석 중 오류가 발생했습니다: {err_msg}"
