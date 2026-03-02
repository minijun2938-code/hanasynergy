import os
import streamlit as st
import json
import base64
import database as db
import auth
import ai_engine
import prompts
import re
from datetime import datetime
import pandas as pd

# --- UI 세션 상태 초기화 ---
if 'logged_in_id' not in st.session_state:
    # 쿼리 파라미터에서 사용자 ID 확인 (새로고침 시 유지용)
    query_params = st.query_params
    if "user" in query_params:
        st.session_state.logged_in_id = query_params["user"]

if 'excluded_members' not in st.session_state:
    st.session_state.excluded_members = set()

if 'view' not in st.session_state:
    st.session_state.view = 'login'
if 'excluded_members' not in st.session_state:
    st.session_state.excluded_members = set()
if 'selected_member_to_move' not in st.session_state:
    st.session_state.selected_member_to_move = None

def set_page_style():
    """다크모드 완벽 대응 및 SaaS 스타일 UI"""
    st.set_page_config(
        page_title="하나은행 궁합 프로그램", 
        page_icon="🤝",
        layout="centered"
    )
    
    # CSS 변수를 활용하여 라이트/다크 모드 통합 대응
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', 'Noto Sans KR', sans-serif;
        }

        /* 메인 배경 효과 - 몽환적인 오로라 스타일 */
        .stApp {
            background: 
                radial-gradient(circle at 10% 10%, rgba(123, 97, 255, 0.08), transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(0, 209, 255, 0.08), transparent 40%),
                radial-gradient(circle at 50% 50%, rgba(255, 0, 128, 0.03), transparent 60%);
            background-attachment: fixed;
        }

        /* 버튼 및 인터랙션 요소 */
        .stButton > button {
            width: 100%;
            border-radius: 16px;
            height: 3.5rem;
            font-weight: 600;
            transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.05);
            color: inherit;
        }

        /* 강조 버튼 - 트렌디한 인디고-퍼플 그라데이션 */
        div.stButton > button:first-child, .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
        }
        
        div.stButton > button:hover {
            box-shadow: 0 12px 30px rgba(99, 102, 241, 0.5);
            transform: translateY(-3px) scale(1.02);
        }

        /* 카드형 섹션 - 더 투명하고 깊이감 있게 */
        .card {
            padding: 2.5rem;
            border-radius: 28px;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background: rgba(255, 255, 255, 0.04);
            backdrop-filter: blur(20px);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
        }

        /* 타이틀 디자인 - 모바일에서 과도하게 커지지 않도록 clamp 적용 */
        .header-title {
            font-size: clamp(1.6rem, 4.5vw, 2.6rem);
            font-weight: 900;
            letter-spacing: -1.8px;
            text-align: center;
            margin-bottom: 0.4rem;
            background: linear-gradient(135deg, #fff 30%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 12px rgba(168, 85, 247, 0.28));
        }
        
        .header-sub {
            font-size: clamp(0.75rem, 2.2vw, 0.95rem);
            color: #a1a1aa;
            text-align: center;
            margin-bottom: 2.2rem;
            font-weight: 400;
            letter-spacing: 3px;
            text-transform: uppercase;
            opacity: 0.8;
        }

        /* 탭 디자인 - 확실한 존재감과 다크 테마 최적화 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            padding: 10px;
            background-color: rgba(255, 255, 255, 0.07) !important;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            padding: 12px 24px;
            transition: all 0.3s;
            color: #555 !important; /* 기본(라이트모드) 글자색: 진한 회색 */
            background-color: rgba(0, 0, 0, 0.05) !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
            margin-right: 6px;
        }

        /* 다크모드 대응 미디어 쿼리 */
        @media (prefers-color-scheme: dark) {
            .stTabs [data-baseweb="tab"] {
                color: rgba(255, 255, 255, 0.9) !important;
                background-color: rgba(255, 255, 255, 0.1) !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important;
            }
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%) !important;
            color: #fff !important;
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
            opacity: 1.0 !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
        }

        /* 스트림릿 기본 빨간색 선 및 하이라이트 완전히 제거 */
        .stTabs [data-baseweb="tab-highlight-point"], 
        .stTabs [data-testid="stMarkdownContainer"] + div {
            background-color: transparent !important;
            display: none !important;
        }
        
        div[data-baseweb="tab-border"] {
            display: none !important;
        }
        
        /* 결과 리포트 박스 - 네온 보더 효과 및 마크다운 스타일링 */
        .report-box {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(168, 85, 247, 0.2);
            padding: 2.5rem;
            border-radius: 24px;
            margin-top: 2rem;
            position: relative;
            overflow: hidden;
            line-height: 1.8;
            color: #e2e8f0;
        }
        
        .report-box h1, .report-box h2, .report-box h3 {
            color: #fff;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #fff 0%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .report-box hr {
            border: 0;
            height: 1px;
            background: linear-gradient(to right, transparent, rgba(168, 85, 247, 0.5), transparent);
            margin: 2rem 0;
        }

        .report-box strong {
            color: #a855f7;
            font-weight: 700;
        }

        .report-box ul, .report-box ol {
            padding-left: 1.2rem;
            margin-bottom: 1.5rem;
        }

        .report-box li {
            margin-bottom: 0.5rem;
        }
        
        .report-box::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(to right, #6366F1, #A855F7);
        }

        /* 입력창 디자인 - 다크 모던 */
        .stTextInput input, .stTextArea textarea {
            border-radius: 16px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            background-color: rgba(0, 0, 0, 0.3) !important;
            color: #fff !important;
            padding: 1rem !important;
        }

        /* 분석 결과 상세 다이얼로그 내 버튼 등 추가 요소 스타일링 */
        div[data-testid="stDialog"] button {
            border-radius: 12px;
        }
        
        /* 성공 메시지 컬러 변경 (Indigo 계열) */
        div[data-testid="stNotification"] {
            background-color: rgba(99, 102, 241, 0.1) !important;
            color: #A855F7 !important;
            border: 1px solid rgba(168, 85, 247, 0.2) !important;
        }

        /* 팀 멤버 리스트 컨테이너 - 가로 나열 및 줄바꿈 */
        .member-list-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            padding: 10px 0;
            justify-content: flex-start;
        }

        .member-tag {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
            padding: 10px 16px;
            transition: all 0.3s ease;
            cursor: pointer;
            min-width: 60px;
            font-weight: 600;
            font-size: 0.95rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* 참여 상태 스타일 (기본) */
        .member-active {
            background: rgba(168, 85, 247, 0.15);
            color: #fff;
            border-color: rgba(168, 85, 247, 0.3);
            box-shadow: 0 4px 12px rgba(168, 85, 247, 0.1);
        }

        /* 제외 상태 스타일 (옅어짐) */
        .member-excluded {
            background: rgba(255, 255, 255, 0.03);
            color: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.05);
            opacity: 0.5;
        }
        </style>
    """, unsafe_allow_html=True)

def validate_emp_id(emp_id):
    """사번/ID 제약을 두지 않습니다(자유 입력)."""
    return bool(emp_id and str(emp_id).strip())

def show_login_page():
    # 저장된 아이디 불러오기
    saved_id = st.query_params.get("remembered_user", "")
    
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="header-title">하나은행 궁합 프로그램</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">Professional Synergy Analysis Tool for Hana Bank</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        user_id = st.text_input("사번/ID", value=saved_id, placeholder="예: s11111")
        user_pw = st.text_input("비밀번호", type="password", placeholder="••••••••")
        
        # 아이디 저장 체크박스
        remember_me = st.checkbox("아이디 저장", value=bool(saved_id))
        
        # 에러 메시지를 표시할 공간
        error_placeholder = st.empty()
        
        if st.button("로그인", use_container_width=True):
            if auth.check_login(user_id, user_pw):
                st.session_state.logged_in_id = user_id
                # URL 쿼리 파라미터에 사용자 ID 저장 (새로고침 시 유지)
                st.query_params["user"] = user_id
                
                # 아이디 저장 여부 업데이트
                if remember_me:
                    st.query_params["remembered_user"] = user_id
                else:
                    if "remembered_user" in st.query_params:
                        del st.query_params["remembered_user"]
                st.rerun()
            else:
                error_placeholder.markdown('<div style="color: #ff4b4b; font-size: 0.85rem; text-align: center; margin-top: -10px; margin-bottom: 10px;">❌ 사번 또는 비밀번호가 일치하지 않습니다.</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="text-align: center; margin-top: 1.5rem;">', unsafe_allow_html=True)
        if st.button("신규 구성원 가입", key="signup_btn"):
            signup_dialog()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("신규 구성원 가입")
def signup_dialog():
    st.markdown("### 📝 구성원 등록")
    new_id = st.text_input("사번/ID", placeholder="자유롭게 입력")
    new_name = st.text_input("이름", placeholder="성함을 입력하세요")
    new_team = st.text_input("팀 이름", placeholder="ex) 기업문화팀 (정확히 입력)")
    new_pw = st.text_input("비밀번호", type="password", help="특수문자, 숫자 등을 포함한 복잡한 비밀번호도 가능합니다.")
    
    st.divider()
    st.caption("개인정보 보호정책: 수집된 성향 데이터는 시너지 분석 목적으로만 사용되며, 언제든 파기 가능합니다.")
    agreed = st.checkbox("약관에 동의합니다.")
    
    if st.button("가입 완료", use_container_width=True):
        if not new_id or not new_name or not new_pw or not new_team:
            st.error("모든 정보를 입력해주세요.")
        elif not validate_emp_id(new_id):
            st.error("사번/ID를 입력해주세요.")
        elif not agreed:
            st.warning("동의가 필요합니다.")
        else:
            # 비밀번호 제약 없이 가입 허용
            if auth.register_user(new_id, new_pw, new_name, new_team.strip()):
                st.success("가입 성공! 로그인을 진행해주세요.")
                st.rerun()

@st.dialog("📋 분석 결과 상세")
def show_report_dialog(title, content):
    st.markdown(f"### {title}")
    st.markdown("---")
    with st.container():
        st.markdown(f'<div class="report-box" style="margin-top:0;">', unsafe_allow_html=True)
        st.markdown(content)
        st.markdown('</div>', unsafe_allow_html=True)

def show_main_content(emp_id):
    user_info = db.get_user_info(emp_id)
    # user_info: (name, profile_data, last_sync, llm_name, team_name)
    if not user_info:
        # DB 리셋/손상/새로고침 시 query param(user)만 남아 자동 로그인되는 케이스 방지
        st.error("사용자 정보를 찾을 수 없습니다. (DB 초기화/리셋 후에는 다시 로그인해야 합니다)")
        if "user" in st.query_params:
            del st.query_params["user"]
        if "logged_in_id" in st.session_state:
            del st.session_state.logged_in_id
        st.stop()

    user_name = user_info[0]
    user_team = user_info[4] if len(user_info) > 4 else "미소속"

    # --- 관리자 로그인 상태 ---
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    
    with st.sidebar:
        st.markdown(f"### 👤 {user_name}님")
        st.caption(f"사번: {emp_id}")
        st.caption(f"소속: {user_team}")

        # 관리자 로그인(Secrets 기반)
        with st.expander("🛠 관리자 로그인", expanded=False):
            admin_pw = st.text_input("관리자 비밀번호", type="password", placeholder="Secrets에 설정한 비밀번호")
            if st.button("관리자 인증"):
                expected = st.secrets.get("ADMIN_PASSWORD") if "ADMIN_PASSWORD" in st.secrets else os.getenv("ADMIN_PASSWORD")
                if expected and admin_pw == expected:
                    st.session_state.is_admin = True
                    st.success("관리자 인증 완료")
                else:
                    st.error("관리자 비밀번호가 올바르지 않습니다.")

        if st.button("로그아웃"):
            if "user" in st.query_params:
                del st.query_params["user"]
            if "logged_in_id" in st.session_state:
                del st.session_state.logged_in_id
            st.session_state.is_admin = False
            st.rerun()
        
        st.divider()
        st.subheader("📜 분석 히스토리")
        history = db.get_analysis_history(emp_id)
        if not history:
            st.caption("아직 분석 내역이 없습니다.")
        else:
            for h_info in history:
                # 데이터 구조가 바뀐 것을 고려하여 안전하게 추출
                h_target_id, h_target_name, h_mode, h_report, h_date = h_info[:5]
                display_name = h_target_name if h_target_name else "본인"
                
                # 모드명 한글 변환
                mode_kr = {
                    "colleague": "직장동료", "couple": "연인궁합", "hierarchy": "상사부하",
                    "self_mbti": "MBTI", "self_archetype": "에겐테토", "self_swot": "장단점",
                    "Team Analysis": "팀 분석"
                }.get(h_mode, h_mode)
                
                title = f"{display_name} | {mode_kr}"
                if st.button(f"{title}\n({h_date})", key=f"hist_{h_date}_{h_target_id}", help=h_date):
                    show_report_dialog(title, h_report)

    # 알림 데이터 가져오기
    pending_requests = db.get_pending_requests(emp_id)
    notif_badge = f" 🔴 {len(pending_requests)}" if pending_requests else ""

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔒 데이터 등록", f"📩 파트너 매칭{notif_badge}", "📊 시너지 분석", "🏢 팀 분석", "👤 내 성향 분석", "🛠 관리자"])

    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 내 성향 데이터 업데이트")

        if user_info and user_info[2]:
            st.caption(f"⏱ 마지막 동기화: {user_info[2]} ({user_info[3]})")
        else:
            st.caption("⏱ 동기화 이력 없음")

        st.markdown('<div class="description">외부 LLM을 통해 분석된 본인의 고유 성향 코드를 등록하세요. 기존 데이터가 있다면 새로운 내용으로 업데이트됩니다.</div>', unsafe_allow_html=True)
        
        selected_llm = st.selectbox("사용 중인 LLM을 선택해 주세요", ["ChatGPT", "Gemini", "Claude", "기타"], index=0)
        
        prompt_text = prompts.USER_ANALYSIS_PROMPT.replace("`", "\\`").replace("\n", "\\n")
        copy_code_html = f"""
            <div style="margin-bottom: 20px;">
                <button onclick="copyToClipboard()" style="
                    width: 100%;
                    background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%);
                    color: white;
                    border: none;
                    padding: 16px 20px;
                    border-radius: 16px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 1.1rem;
                    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
                    transition: all 0.3s ease;
                ">📋 {selected_llm}용 분석 문구 복사하기</button>
            </div>
            <script>
                function copyToClipboard() {{
                    const text = `{prompt_text}`;
                    navigator.clipboard.writeText(text).then(function() {{
                        alert('{selected_llm}용 분석 문구가 복사되었습니다!');
                    }});
                }}
            </script>
        """
        st.components.v1.html(copy_code_html, height=80)
        
        raw_input = st.text_area("분석 결과는 타인이 볼 수 없습니다.", height=150, placeholder="영문/숫자 결과 코드를 붙여넣으세요.")
        
        sync_col1, sync_col2 = st.columns([1, 1])
        with sync_col1:
            if st.button("데이터 동기화", use_container_width=True):
                if not raw_input:
                    st.warning("코드를 입력해주세요.")
                else:
                    try:
                        original_input = raw_input.strip()

                        # 1) 사용자가 붙여넣을 때 설명문/한글/마크다운이 같이 섞이는 케이스를 먼저 감지
                        if re.search(r"[가-힣]", original_input) or re.search(r"[`*_#<>]", original_input):
                            st.error("코드에 한글/마크다운/부적절한 기호가 섞여 있어 동기화에 실패했습니다. '코드만' 복사해서 붙여넣거나, 새 대화/새로고침 후 다시 시도해주세요.")
                            st.stop()

                        # 2) Base64에 허용되는 문자만 남김
                        cleaned_input = re.sub(r"[^A-Za-z0-9+/=]", "", original_input)

                        if len(cleaned_input) < 40:
                            st.error("코드 길이가 너무 짧습니다. 올바른 결과 코드를 다시 복사해 붙여넣어 주세요.")
                            st.stop()

                        # 3) 길이(패딩) 보정
                        missing_padding = len(cleaned_input) % 4
                        if missing_padding:
                            cleaned_input += "=" * (4 - missing_padding)

                        try:
                            decoded_bytes = base64.b64decode(cleaned_input)
                        except Exception:
                            st.error("코드 길이가 맞지 않거나(Base64 패딩 오류), 일부 문자가 누락되었습니다. 다시 복사해서 붙여넣어 주세요.")
                            st.stop()

                        # 4) 문자열 디코딩
                        try:
                            decoded_str = decoded_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            try:
                                decoded_str = decoded_bytes.decode("cp949")
                            except UnicodeDecodeError:
                                st.error("코드가 UTF-8/CP949로 해석되지 않습니다. 복사 과정에서 코드가 손상된 것 같아요. 다시 복사해 주세요.")
                                st.stop()

                        # 5) JSON 파싱
                        try:
                            json_data = json.loads(decoded_str)
                        except json.JSONDecodeError:
                            match = re.search(r"\\{.*\\}", decoded_str, re.DOTALL)
                            if match:
                                json_data = json.loads(match.group())
                            else:
                                st.error("코드 안에서 JSON 데이터를 찾을 수 없습니다. (예: 중간에 줄바꿈/문구가 섞였을 수 있어요) 코드만 다시 붙여넣어 주세요.")
                                st.stop()

                        db.save_profile(emp_id, json.dumps(json_data, ensure_ascii=False), llm_name=selected_llm)
                        st.session_state.sync_success = True
                        st.rerun()
                    except Exception as e:
                        # 최후의 방어: 예상 못한 케이스는 최소 정보로 안내
                        st.error("데이터 동기화 중 오류가 발생했습니다. 코드만 다시 붙여넣어 시도해 주세요.")
        
        with sync_col2:
            if st.session_state.get('sync_success'):
                st.markdown('<div style="color: #10b981; font-weight: bold; padding: 0.8rem 0;">✅ 데이터 동기화 성공!</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        if pending_requests:
            st.subheader(f"🔔 받은 매칭 요청 ({len(pending_requests)})")
            for req in pending_requests:
                req_id_val = req[0]
                u_info = db.get_user_info(req_id_val)
                sender_display = f"{u_info[0]} ({req_id_val})" if u_info else req_id_val
                
                c1, c2 = st.columns([3, 1])
                c1.write(f"👉 **{sender_display}** 님이 매칭을 요청했습니다.")
                if c2.button("수락", key=f"acc_{req_id_val}"):
                    db.accept_match_request(req_id_val, emp_id)
                    st.rerun()
            st.divider()

        sent_requests = db.get_sent_requests(emp_id)
        if sent_requests:
            st.subheader(f"📨 보낸 매칭 요청 ({len(sent_requests)})")
            for req in sent_requests:
                target_id_val = req[0]
                t_info = db.get_user_info(target_id_val)
                target_display = f"{t_info[0]} ({target_id_val})" if t_info else target_id_val
                
                c1, c2 = st.columns([3, 1])
                c1.write(f"⌛ **{target_display}** 님께 요청을 보냈습니다.")
                if c2.button("철회", key=f"can_{target_id_val}", help="상대방이 수락하기 전까지 취소 가능"):
                    db.cancel_match_request(emp_id, target_id_val)
                    st.toast("요청이 철회되었습니다.")
                    st.rerun()
            st.divider()

        st.subheader("➕ 새로운 파트너 매칭")
        st.caption("💡 상대방이 아직 가입하지 않았더라도 ID만 정확하면 요청을 보낼 수 있습니다.")
        target_id = st.text_input("상대방 사번/ID", placeholder="자유롭게 입력")
        if st.button("매칭 요청 발송"):
            if not validate_emp_id(target_id):
                st.error("사번/ID를 입력해주세요.")
            elif target_id == emp_id:
                st.warning("본인에게는 요청할 수 없습니다.")
            else:
                db.send_match_request(emp_id, target_id)
                st.success("요청 완료!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 시너지 리포트 센터")
        
        accepted = db.get_accepted_matches(emp_id)
        if not accepted:
            st.info("현재 매칭된 파트너가 없습니다.")
        else:
            other_ids = list(set([m[0] if m[1] == emp_id else m[1] for m in accepted]))
            partner_options = {}
            for oid in other_ids:
                u_info = db.get_user_info(oid)
                if u_info:
                    display_label = f"{u_info[0]} ({oid})"
                    partner_options[display_label] = oid
            
            if not partner_options:
                st.warning("유효한 파트너 정보를 불러올 수 없습니다.")
            else:
                col_sel, col_del = st.columns([12, 1])
                with col_sel:
                    selected_label = st.selectbox("분석 대상 선택", list(partner_options.keys()), label_visibility="collapsed")
                with col_del:
                    if st.button("×", help="목록에서 삭제", key="del_partner"):
                        db.remove_match(emp_id, partner_options[selected_label])
                        st.rerun()
                
                selected_other = partner_options[selected_label]
                st.write("")
                mode = st.radio("분석 관점 선택", ["직장 동료", "연인 궁합", "상사-부하"], horizontal=True)
                
                additional_info = {}
                can_proceed = True
                
                if mode == "연인 궁합":
                    st.markdown("---")
                    cg1, cg2 = st.columns(2)
                    additional_info['gender_a'] = cg1.selectbox(f"내({user_name}) 성별", ["선택", "남성", "여성"])
                    additional_info['gender_b'] = cg2.selectbox(f"상대방 성별", ["선택", "남성", "여성"])
                    if "선택" in [additional_info['gender_a'], additional_info['gender_b']]:
                        can_proceed = False
                elif mode == "상사-부하":
                    st.markdown("---")
                    other_name = db.get_user_info(selected_other)[0]
                    superior = st.selectbox("누가 리더(상사)인가요?", [user_name, other_name])
                    additional_info['superior_name'] = superior
                    additional_info['subordinate_name'] = other_name if superior == user_name else user_name

                if st.button("시너지 분석 시작", disabled=not can_proceed):
                    info_a = db.get_user_info(emp_id)
                    info_b = db.get_user_info(selected_other)
                    mode_map = {"직장 동료": "colleague", "연인 궁합": "couple", "상사-부하": "hierarchy"}
                    with st.spinner("🔍 Gemini 3가 시너지를 정교하게 분석 중입니다..."):
                        report, meta = ai_engine.analyze_compatibility_with_meta(
                            info_a[1],
                            info_b[1],
                            info_a[0],
                            info_b[0],
                            mode=mode_map[mode],
                            additional_info=additional_info,
                        )
                        db.save_analysis_report(emp_id, selected_other, mode_map[mode], report)
                        if meta:
                            db.save_analysis_audit(
                                emp_id=emp_id,
                                target_id=selected_other,
                                mode=mode_map[mode],
                                model=meta.get("model"),
                                system_prompt=meta.get("system_prompt"),
                                user_prompt=meta.get("user_prompt"),
                                report=report,
                            )
                    st.markdown("---")
                    with st.container():
                        st.markdown(f'<div class="report-box">', unsafe_allow_html=True)
                        st.markdown(report)
                        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader(f"🏢 팀 분석 ({user_team})")
        
        if not user_team or user_team == "미소속":
             st.warning("소속된 팀 정보가 없습니다.")
        else:
            team_members = db.get_team_members(user_team)
            if len(team_members) < 2:
                st.info(f"현재 {user_team}에 등록된 멤버가 부족합니다. (최소 2명 이상 필요)")
            else:
                st.markdown("**참여 멤버 관리**")
                st.caption("💡 분석에서 제외하고 싶은 사람은 이름을 클릭해 주세요. (옅게 표시됨)")
                
                # 멤버 리스트 가로 나열 - Columns 활용
                active_members = []
                cols = st.columns(5)
                
                for idx, member in enumerate(team_members):
                    m_name, m_data, m_id = member
                    is_excluded = m_id in st.session_state.excluded_members
                    
                    if not is_excluded:
                        active_members.append(member)
                    
                    with cols[idx % 5]:
                        # 제외 상태에 따른 버튼 레이블 (이름 오른쪽 이모지 토글)
                        label = f"{m_name}" if is_excluded else f"{m_name} 🙋"
                        
                        # 스타일 주입
                        if is_excluded:
                            st.markdown(f"""
                                <style>
                                div.stButton > button[key="m_tag_{m_id}"] {{
                                    background: rgba(255, 255, 255, 0.05) !important;
                                    color: rgba(255, 255, 255, 0.2) !important;
                                    border: 1px dashed rgba(255, 255, 255, 0.2) !important;
                                    opacity: 0.3 !important;
                                    height: 35px !important;
                                    font-size: 13px !important;
                                }}
                                </style>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <style>
                                div.stButton > button[key="m_tag_{m_id}"] {{
                                    background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%) !important;
                                    color: #FFFFFF !important;
                                    border: none !important;
                                    height: 35px !important;
                                    font-size: 13px !important;
                                    box-shadow: 0 4px 10px rgba(99, 102, 241, 0.3) !important;
                                }}
                                </style>
                            """, unsafe_allow_html=True)

                        # 클릭 이벤트: st.session_state를 즉시 변경하고 rerun
                        if st.button(label, key=f"m_tag_{m_id}", use_container_width=True):
                            if m_id in st.session_state.excluded_members:
                                st.session_state.excluded_members.remove(m_id)
                            else:
                                st.session_state.excluded_members.add(m_id)
                            st.rerun()
                
                st.divider()

                if len(active_members) < 2:
                    st.warning("분석을 위해 최소 2명 이상의 멤버를 포함해 주세요.")
                else:
                    member_names = [m[0] for m in active_members]
                    leader_name = st.selectbox("이 팀의 리더(팀장)는 누구인가요?", member_names)
                    
                    if st.button("🚀 팀 전체 시너지 분석"):
                        with st.spinner("팀 역학 관계 및 시너지 분석 중..."):
                            data_for_ai = [(m[0], m[1], m[2]) for m in active_members]
                            report, meta = ai_engine.analyze_team_synergy_with_meta(data_for_ai, user_team, leader_name)
                            db.save_analysis_report(emp_id, user_team, "Team Analysis", report)
                            if meta:
                                db.save_analysis_audit(
                                    emp_id=emp_id,
                                    target_id=user_team,
                                    mode="Team Analysis",
                                    model=meta.get("model"),
                                    system_prompt=meta.get("system_prompt"),
                                    user_prompt=meta.get("user_prompt"),
                                    report=report,
                                )
                        st.markdown("---")
                        with st.container():
                            st.markdown(f'<div class="report-box">', unsafe_allow_html=True)
                            st.markdown(report)
                            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab5:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("👤 개인 성향 심층 분석")
        info_self = db.get_user_info(emp_id)
        if not info_self:
            st.warning("사용자 정보를 찾을 수 없습니다. 로그아웃 후 다시 로그인해주세요.")
        elif not info_self[1]:
            st.warning("데이터 등록 탭에서 먼저 정보를 입력해주세요.")
        else:
            gender = st.radio("성별 (분석용)", ["남성", "여성"], horizontal=True)
            st.write("")
            btn_cols = st.columns([1, 1, 1])
            report_type = None
            if btn_cols[0].button("🧩 MBTI 분석", use_container_width=True): report_type = "self_mbti"
            if btn_cols[1].button("🎭 에겐테토 분석", use_container_width=True): report_type = "self_archetype"
            if btn_cols[2].button("🌟 장단점 분석", use_container_width=True): report_type = "self_swot"
            
            if report_type:
                with st.spinner("🔍 Gemini 3가 당신의 페르소나를 매핑 중입니다..."):
                    report, meta = ai_engine.analyze_compatibility_with_meta(
                        info_self[1],
                        None,
                        info_self[0],
                        None,
                        mode=report_type,
                        additional_info={"gender": gender},
                    )
                    db.save_analysis_report(emp_id, None, report_type, report)
                    if meta:
                        db.save_analysis_audit(
                            emp_id=emp_id,
                            target_id=None,
                            mode=report_type,
                            model=meta.get("model"),
                            system_prompt=meta.get("system_prompt"),
                            user_prompt=meta.get("user_prompt"),
                            report=report,
                        )
                st.markdown("---")
                with st.container():
                    st.markdown(f'<div class="report-box">', unsafe_allow_html=True)
                    st.markdown(report)
                    st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab6:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🛠 관리자 페이지")

        if not st.session_state.get("is_admin"):
            st.info("관리자 권한이 필요합니다. 좌측 사이드바에서 관리자 비밀번호를 입력해 인증해주세요.")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.caption("최근 분석 로그(프롬프트/결과)를 조회합니다. 개인정보/민감정보는 외부 공유 금지.")

            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_a:
                filter_emp = st.text_input("사번/ID 필터(선택)", placeholder="예: s11111")
            with col_b:
                filter_mode = st.selectbox(
                    "모드 필터",
                    ["(전체)", "colleague", "couple", "hierarchy", "self_mbti", "self_archetype", "self_swot", "Team Analysis"],
                )
            with col_c:
                limit = st.selectbox("표시 개수", [50, 100, 200, 500], index=2)

            rows = db.get_analysis_audit(limit=limit, emp_id=(filter_emp.strip() if filter_emp else None), mode=filter_mode)
            if not rows:
                st.warning("표시할 로그가 없습니다.")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # rows: (id, emp_id, target_id, mode, model, system_prompt, user_prompt, report, created_at)
                data = []
                for r in rows:
                    _id, _emp, _target, _mode, _model, _sys, _usr, _rep, _ts = r
                    data.append(
                        {
                            "id": _id,
                            "created_at": _ts,
                            "emp_id": _emp,
                            "target_id": _target,
                            "mode": _mode,
                            "model": _model,
                            "prompt_preview": ("" if not _usr else (_usr[:120] + "…" if len(_usr) > 120 else _usr)),
                            "report_preview": ("" if not _rep else (_rep[:120] + "…" if len(_rep) > 120 else _rep)),
                        }
                    )

                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                selected_id = st.selectbox("상세 보기(id)", options=df["id"].tolist())
                selected_row = next((r for r in rows if r[0] == selected_id), None)
                if selected_row:
                    _id, _emp, _target, _mode, _model, _sys, _usr, _rep, _ts = selected_row
                    st.markdown("---")
                    st.write(f"**시간:** {_ts} | **사번/ID:** {_emp} | **대상:** {_target} | **모드:** {_mode} | **모델:** {_model}")

                    with st.expander("System Prompt", expanded=False):
                        st.code(_sys or "(없음)")
                    with st.expander("User Prompt", expanded=False):
                        st.code(_usr or "(없음)")
                    with st.expander("Report (결과)", expanded=True):
                        st.markdown(_rep or "(없음)")

                st.markdown('</div>', unsafe_allow_html=True)

def main():
    set_page_style()
    db.init_db()
    if 'logged_in_id' not in st.session_state:
        show_login_page()
    else:
        show_main_content(st.session_state.logged_in_id)

if __name__ == "__main__":
    main()
