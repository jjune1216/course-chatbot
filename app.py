import streamlit as st
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import os

# API 키 로드
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 페이지 설정
st.set_page_config(page_title="수강신청 도우미", page_icon="🎓", layout="wide")
st.title("🎓 수강신청 도우미 챗봇")
st.write("강좌에 대해 궁금한 점을 물어보세요!")

# CSV 파일 읽기
@st.cache_data
def load_courses():
    try:
        df = pd.read_csv("courses.csv", encoding="utf-8")
    except:
        try:
            df = pd.read_csv("courses.csv", encoding="cp949")
        except:
            df = pd.read_csv("courses.csv", encoding="utf-8-sig")
    return df

try:
    courses_df = load_courses()
    st.success(f"✅ {len(courses_df)}개의 강좌 정보를 불러왔습니다!")
except Exception as e:
    st.error(f"❌ CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
    st.stop()

# 강좌 정보를 텍스트로 변환
def get_course_info():
    course_text = "=== 현재 수강신청 가능한 강좌 목록 ===\n\n"
    for idx, row in courses_df.iterrows():
        course_text += f"【과목 {idx+1}】\n"
        course_text += f"과목코드: {row['과목코드']}\n"
        course_text += f"과목명: {row['과목명']}\n"
        course_text += f"교수명: {row['교수명']}\n"
        course_text += f"학점: {row['학점']}\n"
        course_text += f"수업시간: {row['요일']} {row['시간']}\n"
        course_text += f"강의실: {row['강의실']}\n"
        course_text += f"정원: {row['정원']}명\n"
        course_text += f"비고: {row['비고']}\n\n"
    return course_text

# Gemini 모델 초기화 (수정된 부분)
model = genai.GenerativeModel('gemini-2.5-flash')

# 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat" not in st.session_state:
    # 시스템 프롬프트 설정
    system_prompt = f"""당신은 대학교 수강신청을 돕는 친절하고 전문적인 상담 챗봇입니다.
학생들의 질문에 아래 강좌 정보를 바탕으로 정확하게 답변하세요.

{get_course_info()}

답변 시 주의사항:
1. 강좌 정보에 없는 내용은 "해당 정보가 제공되지 않았습니다"라고 답변
2. 여러 과목을 추천할 때는 각 과목의 핵심 정보(과목명, 교수, 시간, 학점)를 포함
3. 시간표 관련 질문에는 요일과 시간을 명확히 표시
4. 친근하면서도 전문적인 톤 유지
5. 질문이 모호하면 구체적으로 무엇을 원하는지 되묻기"""
    
    st.session_state.chat = model.start_chat(history=[])
    # 첫 메시지로 시스템 프롬프트 전달
    st.session_state.chat.send_message(system_prompt)

# 메인 영역과 사이드바로 나누기
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 채팅")
    
    # 이전 대화 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # 사용자 입력
    if prompt := st.chat_input("예: 월요일에 들을 수 있는 과목 알려줘"):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("🤔 생각 중..."):
                try:
                    # Gemini API 호출
                    response = st.session_state.chat.send_message(prompt)
                    answer = response.text
                    
                    st.write(answer)
                    
                    # 응답 저장
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                except Exception as e:
                    st.error(f"❌ 오류가 발생했습니다: {e}")
                    st.info("💡 API 키를 확인해주세요.")

with col2:
    st.subheader("📚 전체 강좌 목록")
    st.dataframe(courses_df, use_container_width=True, height=400)
    
    # 대화 초기화 버튼
    if st.button("🔄 대화 내역 초기화"):
        st.session_state.messages = []
        system_prompt = f"""당신은 대학교 수강신청을 돕는 친절하고 전문적인 상담 챗봇입니다.
학생들의 질문에 아래 강좌 정보를 바탕으로 정확하게 답변하세요.

{get_course_info()}

답변 시 주의사항:
1. 강좌 정보에 없는 내용은 "해당 정보가 제공되지 않았습니다"라고 답변
2. 여러 과목을 추천할 때는 각 과목의 핵심 정보(과목명, 교수, 시간, 학점)를 포함
3. 시간표 관련 질문에는 요일과 시간을 명확히 표시
4. 친근하면서도 전문적인 톤 유지
5. 질문이 모호하면 구체적으로 무엇을 원하는지 되묻기"""
        st.session_state.chat = model.start_chat(history=[])
        st.session_state.chat.send_message(system_prompt)
        st.rerun()

# 하단 정보
st.divider()
st.caption("💡 팁: '월요일 과목', '3학점 수업', '김철수 교수님 강의' 등으로 질문해보세요!")
st.caption("🤖 Powered by Google Gemini Pro (무료)")