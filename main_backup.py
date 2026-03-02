import streamlit as st
import json
import base64
import database as db
import auth
import ai_engine
import prompts

def main():
    st.set_page_config(page_title="SK Enmove Chemistry Hub", layout="centered")
    db.init_db()
    
    st.title("🤝 동료 성향 궁합 PoC (보안 모드)")
    
    st.sidebar.title("🔐 로그인")
    input_id = st.sidebar.text_input("사번", placeholder="51584")
    input_pw = st.sidebar.text_input("비밀번호", type="password")
    input_name = st.sidebar.text_input("이름 (신규 가입 시 필수)", placeholder="홍길동")

    if not input_id or not input_pw:
        st.info("💡 사번과 비밀번호를 입력해 주세요.")
        return

    login_status = auth.check_login(input_id, input_pw)
    
    if login_status is None:
        if st.sidebar.button("신규 가입하기"):
            if not input_name:
                st.sidebar.error("이름을 입력해 주세요.")
            elif auth.register_user(input_id, input_pw, input_name):
                st.sidebar.success("🎊 가입 완료! 다시 로그인 하세요.")
            st.rerun()
        return
    elif login_status is False:
        st.sidebar.error("❌ 비밀번호 오류")
        return

    emp_id = input_id
    tab1, tab2, tab3 = st.tabs(["🔒 내 데이터 등록", "📩 궁합 요청", "📊 결과 보기"])

    with tab1:
        st.subheader("📋 성향 데이터 등록")
        st.code(prompts.USER_ANALYSIS_PROMPT, language="text")
        raw_input = st.text_area("보안 코드(Base64)를 붙여넣으세요", height=150)
        if st.button("데이터 저장"):
            try:
                decoded_str = base64.b64decode(raw_input).decode('utf-8')
                json.loads(decoded_str)
                db.save_profile(emp_id, decoded_str)
                st.success("✅ 저장 완료!")
            except:
                st.error("❌ 코드 형식이 올바르지 않습니다.")

    with tab2:
        st.subheader("📩 궁합 확인 요청")
        target_id = st.text_input("상대방 사번")
        if st.button("요청 보내기"):
            db.send_match_request(emp_id, target_id)
            st.info(f"📨 {target_id}님께 요청을 보냈습니다.")

    with tab3:
        st.subheader("📊 AI 분석 리포트")
        # 요청 수락 로직
        requests = db.get_pending_requests(emp_id)
        for req in requests:
            if st.button(f"{req[0]}님의 요청 수락"):
                db.accept_match_request(req[0], emp_id)
                st.rerun()

        accepted = db.get_accepted_matches(emp_id)
        if not accepted:
            st.info("상호 승인된 동료가 없습니다.")
        else:
            other_ids = list(set([m[0] if m[1] == emp_id else m[1] for m in accepted]))
            selected_other = st.selectbox("동료 선택", other_ids)
            if st.button("AI 분석 시작"):
                info_a = db.get_user_info(emp_id)
                info_b = db.get_user_info(selected_other)
                with st.spinner("🚀 분석 중..."):
                    report = ai_engine.analyze_compatibility(info_a[1], info_b[1], info_a[0], info_b[0])
                    st.markdown(report)

if __name__ == "__main__":
    main()