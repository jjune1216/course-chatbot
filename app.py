import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re

# --- 1. Modular Imports ---
from data_manager import CourseDataManager
from course_recommender import recommend_courses
from schedule_generator import generate_schedules
from schedule_ranker import rank_schedules

# --- 2. Initial Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

st.title("🎓 AI 수강신청 도우미")

# --- 3. State Management and Initialization ---
@st.cache_resource
def get_data_manager():
    return CourseDataManager()

@st.cache_resource
def get_gemini_model():
    return genai.GenerativeModel('gemini-1.5-flash')

data_manager = get_data_manager()
model = get_gemini_model()

# Initialize session state variables
if "stage" not in st.session_state:
    st.session_state.stage = "welcome"
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 당신의 수강신청을 도와드릴 AI 도우미입니다. 전공과 학년을 알려주시겠어요? (예: 컴퓨터공학부 2학년)"}]
    st.session_state.user_info = {}
    st.session_state.schedules = []
    st.session_state.final_schedule = None
    st.session_state.final_explanation = ""

# --- 4. Main Conversational Logic ---

# Display prior chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input based on conversation stage
if prompt := st.chat_input("메시지를 입력하세요..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Stage: WELCOME (Get Major/Year) ---
    if st.session_state.stage == "welcome":
        with st.chat_message("assistant"):
            with st.spinner("정보를 분석 중입니다..."):
                # Basic parsing for major and year
                major_match = re.search(r'(\S+)(?:학과|학부)', prompt)
                year_match = re.search(r'(\d)\s*학년', prompt)
                
                if major_match and year_match:
                    st.session_state.user_info['major'] = major_match.group(0)
                    st.session_state.user_info['year'] = int(year_match.group(1))
                    
                    response_text = f"네, {st.session_state.user_info['major']} {st.session_state.user_info['year']}학년이시군요! 어떤 분야나 과목에 관심이 있으신가요? (예: '인공지능이랑 웹 개발에 관심있어요', '교양 위주로 듣고 싶어요')"
                    st.session_state.stage = "get_interests"
                else:
                    response_text = "전공과 학년을 정확히 인식하지 못했어요. '컴퓨터공학부 2학년'과 같은 형식으로 다시 말씀해주시겠어요?"
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: GET_INTERESTS (Recommend Courses) ---
    elif st.session_state.stage == "get_interests":
        st.session_state.user_info['interests'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("관심분야에 맞춰 과목을 추천 중입니다... (1/3)"):
                recommended_names = recommend_courses(
                    st.session_state.user_info['major'],
                    st.session_state.user_info['year'],
                    st.session_state.user_info['interests'],
                    data_manager,
                    model
                )
                st.session_state.user_info['recommended_courses'] = recommended_names
                
                response_text = f"관심사를 바탕으로 다음과 같은 과목들을 추천드렸어요:\n- " + "\n- ".join(recommended_names)
                response_text += "\n\n어떤 스타일의 시간표를 선호하시나요? (예: '금요일은 비워주세요', '아침 수업이 좋아요', '수업 사이에 시간이 없으면 좋겠어요')"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.stage = "get_preferences"

    # --- Stage: GET_PREFERENCES (Generate and Rank Schedules) ---
    elif st.session_state.stage == "get_preferences":
        st.session_state.user_info['preferences'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("시간표를 생성하고 분석 중입니다... (2/3)"):
                generated = generate_schedules(
                    st.session_state.user_info['recommended_courses'],
                    data_manager,
                    max_schedules=10 # Limit to 10 to avoid excessive processing
                )
                st.session_state.schedules = generated

            if not generated:
                response_text = "이런, 추천된 과목들로는 시간표를 만들 수가 없네요. 추천 과목 수를 줄이거나 다른 과목으로 다시 시도해볼까요?"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.stage = "error" # Or loop back
            else:
                with st.spinner("최적의 시간표를 고르고 있습니다... (3/3)"):
                    best_schedule, explanation = rank_schedules(
                        generated,
                        st.session_state.user_info['preferences'],
                        model
                    )
                    st.session_state.final_schedule = best_schedule
                    st.session_state.final_explanation = explanation

                    # Format the final schedule for display
                    schedule_df = pd.DataFrame(best_schedule)
                    schedule_display = schedule_df[['교과목명', '주담당교수', '수업교시']].to_markdown(index=False)

                    response_text = f"**당신을 위한 최적의 시간표를 찾았어요!**\n\n{st.session_state.final_explanation}\n\n"
                    response_text += f"### 추천 시간표\n{schedule_display}"
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.session_state.stage = "done"
                    st.button("처음부터 다시 시작하기")

# --- 5. Restart Button Logic ---
if st.session_state.stage == "done":
    if st.button("처음부터 다시 시작하기"):
        st.session_state.clear()
        st.rerun()