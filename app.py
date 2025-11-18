import streamlit as st
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import os
from data_manager import CourseDataManager

# --- 1. 초기 설정 및 데이터 로딩 ---

# API 키 로드
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 페이지 기본 설정
st.set_page_config(page_title="수강신청 도우미", page_icon="🎓", layout="wide")

# 데이터 매니저 초기화 (캐시 사용)
@st.cache_resource
def get_data_manager():
    dm = CourseDataManager(file_path="courses.csv")
    return dm

data_manager = get_data_manager()
all_courses_df = data_manager.get_all_courses()

# --- 2. 사이드바 필터 ---

st.sidebar.header("🔍 강좌 필터")

# 필터 값 초기화
if 'filters' not in st.session_state:
    st.session_state.filters = {
        '교과목명': '',
        '교과구분': [],
        '학년': [],
        'preferred_free_day': None,
        'prefer_morning': None # None: 무관, True: 오전, False: 오후
    }

# 필터 위젯
course_name_filter = st.sidebar.text_input(
    "과목명 검색", 
    st.session_state.filters['교과목명']
)

course_type_options = sorted(all_courses_df['교과구분'].unique())
course_type_filter = st.sidebar.multiselect(
    "교과 구분",
    options=course_type_options,
    default=st.session_state.filters['교과구분']
)

grade_options = sorted(all_courses_df['학년'].dropna().unique())
grade_filter = st.sidebar.multiselect(
    "학년",
    options=grade_options,
    default=st.session_state.filters['학년']
)

free_day_filter = st.sidebar.selectbox(
    "희망 공강 요일",
    options=[None, '월', '화', '수', '목', '금', '토', '일'],
    format_func=lambda x: '선택 안 함' if x is None else f"{x}요일",
    index=0
)

morning_pref_filter = st.sidebar.radio(
    "수업 시간 선호",
    options=[None, True, False],
    format_func=lambda x: '무관' if x is None else ('오전' if x else '오후'),
    index=0
)

# 필터 적용 버튼
if st.sidebar.button("적용", use_container_width=True):
    st.session_state.filters['교과목명'] = course_name_filter
    st.session_state.filters['교과구분'] = course_type_filter
    st.session_state.filters['학년'] = grade_filter
    st.session_state.filters['preferred_free_day'] = free_day_filter
    st.session_state.filters['prefer_morning'] = morning_pref_filter
    st.rerun()

# 필터된 데이터프레임 생성
filtered_df = data_manager.filter_courses(st.session_state.filters)

# --- 3. 메인 화면 구성 ---

st.title("🎓 수강신청 도우미 챗봇")
st.write("좌측 사이드바에서 필터를 적용하여 강좌를 검색하고, 아래 챗봇에게 질문해보세요!")

# 필터된 강좌 목록 표시
st.subheader(f"📚 강좌 목록 ({len(filtered_df)}개)")
st.dataframe(filtered_df, use_container_width=True, height=400)

st.divider()

# --- 4. 챗봇 기능 ---

st.subheader("💬 챗봇에게 질문하기")

def get_course_info_for_prompt(df: pd.DataFrame) -> str:
    """필터링된 DataFrame을 모델 프롬프트에 넣기 좋은 텍스트로 변환"""
    if df.empty:
        return "현재 조건에 맞는 강좌가 없습니다. 필터를 조정해보세요."
    
    # 너무 많은 정보를 한 번에 보내지 않도록 상위 20개만 우선 표시
    df_head = df.head(20)
    course_text = "=== 현재 필터링된 강좌 목록 (최대 20개) ===\n\n"
    for _, row in df_head.iterrows():
        course_text += (
            f"- 과목명: {row.get('교과목명', 'N/A')}\n"
            f"  - 교수: {row.get('주담당교수', 'N/A')}\n"
            f"  - 시간: {row.get('수업교시', 'N/A')}\n"
            f"  - 학점: {row.get('학점', 'N/A')}\n"
            f"  - 구분: {row.get('교과구분', 'N/A')}\n"
            f"  - 학년: {row.get('학년', 'N/A')}\n\n"
        )
    if len(df) > 20:
        course_text += f"... 외 {len(df) - 20}개의 강좌가 더 있습니다."
    return course_text

# Gemini 모델 및 채팅 기록 초기화
if "chat" not in st.session_state or st.session_state.get('filters_changed', False):
    model = genai.GenerativeModel('gemini-1.5-flash')
    system_prompt = f"""당신은 대학교 수강신청을 돕는 친절하고 전문적인 상담 챗봇입니다.
학생들의 질문에 아래의 필터링된 강좌 목록을 바탕으로 정확하게 답변하세요.

{get_course_info_for_prompt(filtered_df)}

답변 시 주의사항:
1. 목록에 없는 정보는 "해당 정보가 제공되지 않았습니다" 또는 "필터된 목록에는 없습니다"라고 답변하세요.
2. 여러 과목을 추천할 때는 각 과목의 핵심 정보(과목명, 교수, 시간)를 명확히 요약해주세요.
3. 친근하면서도 전문적인 톤을 유지하고, 학생의 질문 의도를 파악하여 답변하세요.
4. 만약 조건에 맞는 과목이 없다면, 사이드바의 필터를 조절해보라고 안내해주세요.
"""
    st.session_state.chat = model.start_chat(history=[{'role': 'user', 'parts': [system_prompt]}, {'role': 'model', 'parts': ["안녕하세요! 수강신청에 대해 무엇을 도와드릴까요? 사이드바의 필터로 강좌를 검색한 후 질문해주세요."]}])
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 수강신청에 대해 무엇을 도와드릴까요? 사이드바의 필터로 강좌를 검색한 후 질문해주세요."}]
    st.session_state.filters_changed = False


# 이전 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("예: 이 중에서 아침 수업만 알려줘"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 답변을 생성 중입니다..."):
            try:
                response = st.session_state.chat.send_message(prompt)
                answer = response.text
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {e}")

# 대화 초기화 버튼
if st.sidebar.button("🔄 대화 초기화", use_container_width=True):
    st.session_state.filters_changed = True
    st.rerun()
