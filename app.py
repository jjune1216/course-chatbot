import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import pandas as pd
import re

# --- 1. Modular Imports ---
from course_manager import CourseManager
from chatbot_logic import (
    recommend_courses,
    recommend_veritas_course,
    answer_schedule_question,
    generate_schedules,
    rank_schedules,
)

# --- 2. Initial Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

st.title("🎓 AI 수강신청 도우미 (Refactored)")

# --- 3. State Management and Initialization ---
@st.cache_resource
def get_course_manager():
    return CourseManager()

@st.cache_resource
def get_gemini_model():
    return genai.GenerativeModel('gemini-1.5-pro-latest')

course_manager = get_course_manager()
model = get_gemini_model()

# Initialize session state variables
if "stage" not in st.session_state:
    st.session_state.stage = "welcome"
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 당신의 수강신청을 도와드릴 AI 도우미입니다. 전공과 학년을 알려주시겠어요? (예: 컴퓨터공학부 2학년)"}]
    st.session_state.user_info = {}

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
        # Basic parsing for major and year
        major_match = re.search(r'(\S+)(?:학과|학부)', prompt)
        year_match = re.search(r'(\d)\s*학년', prompt)
        
        if major_match and year_match:
            st.session_state.user_info['major'] = major_match.group(0)
            st.session_state.user_info['year'] = int(year_match.group(1))
            
            response_text = f"네, {st.session_state.user_info['major']} {st.session_state.user_info['year']}학년이시군요! 무엇을 도와드릴까요?\n\n1. **과목 추천받기** (관심분야를 알려주세요)\n2. **베리타스 교양과목 추천받기**\n3. **수강신청 관련 질문하기**"
            st.session_state.stage = "main_menu"
        else:
            response_text = "전공과 학년을 정확히 인식하지 못했어요. '컴퓨터공학부 2학년'과 같은 형식으로 다시 말씀해주시겠어요?"
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: MAIN_MENU (User selects an action) ---
    elif st.session_state.stage == "main_menu":
        st.session_state.user_info['last_request'] = prompt
        
        # Simple keyword-based routing
        if "과목 추천" in prompt or "1" in prompt:
            response_text = "어떤 분야나 과목에 관심이 있으신가요? (예: '인공지능이랑 웹 개발에 관심있어요')"
            st.session_state.stage = "get_course_interests"
        elif "베리타스" in prompt or "2" in prompt:
            response_text = "베리타스 교양과목에 대해 특별히 고려하는 점이 있나요? (예: '철학적인 주제였으면 좋겠어요', '과학 관련된 게 좋아요')"
            st.session_state.stage = "get_veritas_interests"
        elif "질문" in prompt or "3" in prompt:
            response_text = "수강신청에 대해 어떤 점이 궁금하신가요?"
            st.session_state.stage = "answer_question"
        else:
            response_text = "죄송하지만, 어떤 요청인지 이해하지 못했어요. '과목 추천', '베리타스 추천', '질문하기' 중에서 선택해주세요."
            
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GET_COURSE_INTERESTS ---
    elif st.session_state.stage == "get_course_interests":
        st.session_state.user_info['interests'] = prompt
        response_text = "알겠습니다. 몇 학점 정도 수강하고 싶으신가요? (예: 18학점)"
        st.session_state.stage = "get_credits"
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GET_CREDITS ---
    elif st.session_state.stage == "get_credits":
        # Basic parsing for credits
        import re
        credits_match = re.search(r'(\d+)', prompt)
        if credits_match:
            st.session_state.user_info['desired_credits'] = int(credits_match.group(1))
        else:
            st.session_state.user_info['desired_credits'] = 18 # Default value
        
        with st.chat_message("assistant"):
            with st.spinner("관심분야와 학점에 맞춰 과목을 추천 중입니다..."):
                recommended = recommend_courses(
                    st.session_state.user_info, 
                    course_manager, 
                    model, 
                    st.session_state.user_info.get('desired_credits', 18)
                )
                st.session_state.user_info['recommended_courses'] = recommended
                
                response_text = f"관심사와 학점을 고려하여 다음과 같은 과목들을 추천드렸어요:\n- " + "\n- ".join(recommended)
                response_text += "\n\n이 과목들로 시간표를 만들어볼까요? 시간표에 대한 특별한 선호사항이 있다면 알려주세요. (예: '금요일은 비워주세요', '아침 수업이 좋아요')"
                st.session_state.stage = "generate_schedules"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: GET_VERITAS_INTERESTS ---
    elif st.session_state.stage == "get_veritas_interests":
        st.session_state.user_info['interests'] = prompt # Store veritas interests
        with st.chat_message("assistant"):
            with st.spinner("베리타스 교양과목을 추천 중입니다..."):
                recommendation = recommend_veritas_course(st.session_state.user_info, course_manager, model)
                response_text = recommendation
                st.session_state.stage = "ask_satisfaction_veritas"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: ANSWER_QUESTION ---
    elif st.session_state.stage == "answer_question":
        with st.chat_message("assistant"):
            with st.spinner("질문에 대한 답변을 생성 중입니다..."):
                answer = answer_schedule_question(prompt, course_manager, model)
                response_text = answer
                st.session_state.stage = "main_menu" # Loop back to main menu
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: GENERATE_SCHEDULES ---
    elif st.session_state.stage == "generate_schedules":
        st.session_state.user_info['preferences'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("시간표를 생성하고 분석 중입니다..."):
                generated = generate_schedules(
                    st.session_state.user_info['recommended_courses'],
                    course_manager,
                    max_schedules=10
                )
            
            if not generated:
                response_text = "이런, 추천된 과목들로는 시간표를 만들 수가 없네요. 추천 과목을 변경하거나 다른 조건으로 다시 시도해볼까요?"
                st.session_state.stage = "main_menu" # Loop back
            else:
                with st.spinner("최적의 시간표를 고르고 있습니다..."):
                    best_schedule, explanation = rank_schedules(
                        generated,
                        st.session_state.user_info['preferences'],
                        model
                    )
                    
                    if best_schedule:
                        # Format the final schedule for display
                        schedule_df = pd.DataFrame(best_schedule)
                        schedule_display = schedule_df[['name', 'schedule']].to_markdown(index=False)
                        response_text = f"**당신을 위한 최적의 시간표를 찾았어요!**\n\n{explanation}\n\n"
                        response_text += f"### 추천 시간표\n{schedule_display}"
                        st.session_state.stage = "done"
                    else:
                        response_text = "시간표를 랭킹하는 데 실패했습니다. 다시 시도해주세요."
                        st.session_state.stage = "main_menu"

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: ASK_SATISFACTION (Generic satisfaction check) ---
    # This is a concept. A full implementation would require more states
    # and more complex logic to handle "yes/no" and follow-ups.
    elif st.session_state.stage == "ask_satisfaction_veritas":
        if "네" in prompt or "좋아요" in prompt:
             response_text = "다행이네요! 다른 도움이 필요하시면 언제든지 말씀해주세요."
             st.session_state.stage = "main_menu"
        else:
             response_text = "그렇군요. 어떤 점이 아쉬우셨나요? 더 나은 추천을 위해 다시 시도해볼게요. 어떤 주제에 관심있으세요?"
             st.session_state.stage = "get_veritas_interests"
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

# --- 5. Restart Button Logic ---
if st.session_state.stage == "done":
    if st.button("처음부터 다시 시작하기"):
        st.session_state.clear()
        st.rerun()
