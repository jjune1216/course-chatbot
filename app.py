from course_manager import CourseManager
import chatbot_logic
import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import re
import anthropic

# --- 2. Initial Setup ---
load_dotenv()
# Configure Anthropic client, API key will be read from ANTHROPIC_API_KEY environment variable

st.title("🎓 AI 수강신청 도우미")

# --- 3. State Management and Initialization ---
@st.cache_resource
def get_course_manager():
    return CourseManager()

@st.cache_resource
def get_claude_client():
    return anthropic.Anthropic()

course_manager = get_course_manager()
claude_client = get_claude_client()

# Initialize session state variables
if "stage" not in st.session_state:
    st.session_state.stage = "welcome"
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 당신의 수강신청을 도와드릴 AI 도우미입니다. 전공과 학년을 알려주시겠어요? (예: 컴퓨터공학부 2학년)"}]
    st.session_state.user_info = {'taken_courses': []}
    st.session_state.recommended_courses = []

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
        major_match = re.search(r'(\S+)(?:학과|학부)', prompt)
        year_match = re.search(r'(\d)\s*학년', prompt)
        
        if major_match and year_match:
            st.session_state.user_info['major'] = major_match.group(0)
            st.session_state.user_info['year'] = int(year_match.group(1))
            
            response_text = f"네, {st.session_state.user_info['major']} {st.session_state.user_info['year']}학년이시군요! 수강 계획을 세우기 위해 몇 가지 질문을 드릴게요. 우선, '베리타스' 교양을 수강한 적이 있으신가요?"
            st.session_state.stage = "ask_veritas"
        else:
            response_text = "전공과 학년을 정확히 인식하지 못했어요. '컴퓨터공학부 2학년'과 같은 형식으로 다시 말씀해주시겠어요?"
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: ASK_VERITAS ---
    elif st.session_state.stage == "ask_veritas":
        if "아니오" in prompt or "아니" in prompt:
            response_text = "베리타스 교양은 [베리타스 교양에 대한 설명]. 어떤 분야에 관심이 있으신가요?"
            st.session_state.stage = "get_veritas_interests"
        else:
            response_text = "어떤 베리타스 과목을 수강하셨나요? 쉼표(,)로 구분하여 알려주세요."
            st.session_state.stage = "get_taken_veritas"
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GET_TAKEN_VERITAS ---
    elif st.session_state.stage == "get_taken_veritas":
        taken_courses = [course.strip() for course in prompt.split(',')]
        st.session_state.user_info['taken_courses'].extend(taken_courses)
        response_text = "네, 알겠습니다. 다음으로 '지성의 열쇠' 영역에 대해 질문드릴게요. '문화 해석과 상상' 영역의 과목을 수강한 적이 있으신가요?"
        st.session_state.stage = "ask_jiseong_culture"
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GET_VERITAS_INTERESTS ---
    elif st.session_state.stage == "get_veritas_interests":
        st.session_state.user_info['interests'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("베리타스 교양과목을 추천 중입니다..."):
                recommendations = chatbot_logic.recommend_veritas_course(
                    st.session_state.user_info, 
                    course_manager, 
                    claude_client,
                    st.session_state.user_info.get('taken_courses', [])
                )
                print(f"DEBUG: Recommendations in app: {recommendations}")
                st.session_state.user_info['last_recommendations'] = recommendations
                response_text = f"관심사를 바탕으로 다음과 같은 베리타스 교양과목을 추천드려요:\n\n- " + "\n- ".join(recommendations)
                response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
            st.session_state.stage = "ask_satisfaction_veritas"
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
    
    # --- Stage: ASK_SATISFACTION_VERITAS ---
    elif st.session_state.stage == "ask_satisfaction_veritas":
        if "다른 추천" in prompt:
            with st.chat_message("assistant"):
                with st.spinner("다른 베리타스 교양과목을 추천 중입니다..."):
                    recommendations = chatbot_logic.recommend_veritas_course(
                        st.session_state.user_info, 
                        course_manager, 
                        claude_client,
                        st.session_state.user_info.get('taken_courses', [])
                    )
                    st.session_state.user_info['last_recommendations'] = recommendations
                    response_text = f"새로운 추천 목록입니다:\n\n- " + "\n- ".join(recommendations)
                    response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.rerun()
        else:
            st.session_state.recommended_courses.extend([prompt])
            response_text = "네, 알겠습니다. 다음으로 '지성의 열쇠' 영역에 대해 질문드릴게요. '문화 해석과 상상' 영역의 과목을 수강한 적이 있으신가요?"
            st.session_state.stage = "ask_jiseong_culture"
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()

    # --- Stage: ASK_JISEONG_CULTURE ---
    elif st.session_state.stage == "ask_jiseong_culture":
        if "아니오" in prompt or "아니" in prompt:
            response_text = "[문화 해석과 상상에 대한 설명]. 어떤 분야에 관심이 있으신가요?"
            st.session_state.stage = "get_jiseong_culture_interests"
        else:
            st.session_state.recommended_courses.extend([prompt])
            response_text = "네, 알겠습니다. 다음으로 '역사적 탐구와 철학적 사유' 영역의 과목을 수강한 적이 있으신가요?"
            st.session_state.stage = "ask_jiseong_history"
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GET_JISEONG_CULTURE_INTERESTS ---
    elif st.session_state.stage == "get_jiseong_culture_interests":
        st.session_state.user_info['interests'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("문화 해석과 상상 교양과목을 추천 중입니다..."):
                recommendations = chatbot_logic.recommend_jiseong_courses(st.session_state.user_info, course_manager, claude_client, "문화 해석과 상상")
                st.session_state.user_info['last_recommendations'] = recommendations
                response_text = f"관심사를 바탕으로 다음과 같은 과목을 추천드려요:\n\n- " + "\n- ".join(recommendations)
                response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
                st.session_state.stage = "ask_satisfaction_jiseong_culture"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: ASK_SATISFACTION_JISEONG_CULTURE ---
    elif st.session_state.stage == "ask_satisfaction_jiseong_culture":
        if "다른 추천" in prompt:
            with st.chat_message("assistant"):
                with st.spinner("다른 교양과목을 추천 중입니다..."):
                    recommendations = chatbot_logic.recommend_jiseong_courses(st.session_state.user_info, course_manager, claude_client, "문화 해석과 상상")
                    st.session_state.user_info['last_recommendations'] = recommendations
                    response_text = f"새로운 추천 목록입니다:\n\n- " + "\n- ".join(recommendations)
                    response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.rerun()
        else:
            st.session_state.recommended_courses.extend([prompt])
            response_text = "네, 알겠습니다. 다음으로 '역사적 탐구와 철학적 사유' 영역의 과목을 수강한 적이 있으신가요?"
            st.session_state.stage = "ask_jiseong_history"
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()

    # --- Stage: ASK_JISEONG_HISTORY ---
    elif st.session_state.stage == "ask_jiseong_history":
        if "아니오" in prompt or "아니" in prompt:
            response_text = "[역사적 탐구와 철학적 사유에 대한 설명]. 어떤 분야에 관심이 있으신가요?"
            st.session_state.stage = "get_jiseong_history_interests"
        else:
            st.session_state.recommended_courses.extend([prompt])
            response_text = "네, 알겠습니다. 다음으로 '인간의 이해와 사회 분석' 영역의 과목을 수강한 적이 있으신가요?"
            st.session_state.stage = "ask_jiseong_society"
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GET_JISEONG_HISTORY_INTERESTS ---
    elif st.session_state.stage == "get_jiseong_history_interests":
        st.session_state.user_info['interests'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("역사적 탐구와 철학적 사유 교양과목을 추천 중입니다..."):
                recommendations = chatbot_logic.recommend_jiseong_courses(st.session_state.user_info, course_manager, claude_client, "역사적 탐구와 철학적 사유")
                st.session_state.user_info['last_recommendations'] = recommendations
                response_text = f"관심사를 바탕으로 다음과 같은 과목을 추천드려요:\n\n- " + "\n- ".join(recommendations)
                response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
                st.session_state.stage = "ask_satisfaction_jiseong_history"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: ASK_SATISFACTION_JISEONG_HISTORY ---
    elif st.session_state.stage == "ask_satisfaction_jiseong_history":
        if "다른 추천" in prompt:
            with st.chat_message("assistant"):
                with st.spinner("다른 교양과목을 추천 중입니다..."):
                    recommendations = chatbot_logic.recommend_jiseong_courses(st.session_state.user_info, course_manager, claude_client, "역사적 탐구와 철학적 사유")
                    st.session_state.user_info['last_recommendations'] = recommendations
                    response_text = f"새로운 추천 목록입니다:\n\n- " + "\n- ".join(recommendations)
                    response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.rerun()
        else:
            st.session_state.recommended_courses.extend([prompt])
            response_text = "네, 알겠습니다. 다음으로 '인간의 이해와 사회 분석' 영역의 과목을 수강한 적이 있으신가요?"
            st.session_state.stage = "ask_jiseong_society"
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()

    # --- Stage: ASK_JISEONG_SOCIETY ---
    elif st.session_state.stage == "ask_jiseong_society":
        if "아니오" in prompt or "아니" in prompt:
            response_text = "[인간의 이해와 사회 분석에 대한 설명]. 어떤 분야에 관심이 있으신가요?"
            st.session_state.stage = "get_jiseong_society_interests"
        else:
            st.session_state.recommended_courses.extend([prompt])
            response_text = "네, 알겠습니다. 이제 전체적인 추천을 위해 몇 학점 정도 수강하고 싶으신가요?"
            st.session_state.stage = "get_credits"
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GET_JISEONG_SOCIETY_INTERESTS ---
    elif st.session_state.stage == "get_jiseong_society_interests":
        st.session_state.user_info['interests'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("인간의 이해와 사회 분석 교양과목을 추천 중입니다..."):
                recommendations = chatbot_logic.recommend_jiseong_courses(st.session_state.user_info, course_manager, claude_client, "인간의 이해와 사회 분석")
                st.session_state.user_info['last_recommendations'] = recommendations
                response_text = f"관심사를 바탕으로 다음과 같은 과목을 추천드려요:\n\n- " + "\n- ".join(recommendations)
                response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
                st.session_state.stage = "ask_satisfaction_jiseong_society"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: ASK_SATISFACTION_JISEONG_SOCIETY ---
    elif st.session_state.stage == "ask_satisfaction_jiseong_society":
        if "다른 추천" in prompt:
            with st.chat_message("assistant"):
                with st.spinner("다른 교양과목을 추천 중입니다..."):
                    recommendations = chatbot_logic.recommend_jiseong_courses(st.session_state.user_info, course_manager, claude_client, "인간의 이해와 사회 분석")
                    st.session_state.user_info['last_recommendations'] = recommendations
                    response_text = f"새로운 추천 목록입니다:\n\n- " + "\n- ".join(recommendations)
                    response_text += "\n\n이 중에 마음에 드는 과목이 있나요? 과목 이름을 알려주시거나, 다른 과목을 추천받고 싶으시면 '다른 추천'이라고 말씀해주세요."
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.rerun()
        else:
            st.session_state.recommended_courses.extend([prompt])
            response_text = "네, 알겠습니다. 이제 전체적인 추천을 위해 몇 학점 정도 수강하고 싶으신가요?"
            st.session_state.stage = "get_credits"
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()

    # --- Stage: GET_CREDITS ---
    elif st.session_state.stage == "get_credits":
        credits_match = re.search(r'(\d+)', prompt)
        if credits_match:
            st.session_state.user_info['desired_credits'] = int(credits_match.group(1))
        else:
            st.session_state.user_info['desired_credits'] = 18 # Default value
        
        with st.chat_message("assistant"):
            with st.spinner("관심분야와 학점에 맞춰 과목을 추천 중입니다..."):
                final_recommendations = chatbot_logic.recommend_courses(
                    st.session_state.user_info, 
                    course_manager, 
                    claude_client, 
                    st.session_state.user_info.get('desired_credits', 18)
                )
                st.session_state.user_info['final_recommendations'] = final_recommendations
                
                response_text = f"수강 희망 학점을 고려하여 다음과 같은 과목들을 추천드렸어요:\n- " + "\n- ".join(final_recommendations)
                response_text += "\n\n이 과목들 중에서 수강하고 싶은 과목들을 모두 알려주세요. 제가 시간표를 만들어 드릴게요."
                st.session_state.stage = "select_final_courses"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- Stage: SELECT_FINAL_COURSES ---
    elif st.session_state.stage == "select_final_courses":
        st.session_state.user_info['selected_courses'] = [course.strip() for course in prompt.split(',')]
        response_text = "네, 알겠습니다. 시간표에 대한 특별한 선호사항이 있다면 알려주세요. (예: '금요일은 비워주세요', '아침 수업이 좋아요')"
        st.session_state.stage = "generate_schedules"
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # --- Stage: GENERATE_SCHEDULES ---
    elif st.session_state.stage == "generate_schedules":
        st.session_state.user_info['preferences'] = prompt
        with st.chat_message("assistant"):
            with st.spinner("시간표를 생성하고 분석 중입니다..."):
                generated = chatbot_logic.generate_schedules(
                    st.session_state.user_info['selected_courses'],
                    course_manager,
                    max_schedules=10
                )
            
            if not generated:
                response_text = "이런, 선택하신 과목들로는 시간표를 만들 수가 없네요. 과목을 변경하거나 다른 조건으로 다시 시도해볼까요?"
                st.session_state.stage = "select_final_courses"
            else:
                with st.spinner("최적의 시간표를 고르고 있습니다..."):
                    best_schedule, explanation = chatbot_logic.rank_schedules(
                        generated,
                        st.session_state.user_info['preferences'],
                        claude_client
                    )
                    
                    if best_schedule:
                        schedule_df = pd.DataFrame(best_schedule)
                        schedule_display = schedule_df[['name', 'schedule']].to_markdown(index=False)
                        response_text = f"**당신을 위한 최적의 시간표를 찾았어요!**\n\n{explanation}\n\n"
                        response_text += f"### 추천 시간표\n{schedule_display}"
                        st.session_state.stage = "done"
                    else:
                        response_text = "시간표를 랭킹하는 데 실패했습니다. 다시 시도해주세요."
                        st.session_state.stage = "select_final_courses"

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

# --- 5. Restart Button Logic ---
if st.session_state.stage == "done":
    if st.button("처음부터 다시 시작하기"):
        st.session_state.clear()
        st.rerun()