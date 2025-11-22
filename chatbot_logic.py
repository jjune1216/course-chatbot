import pandas as pd
from course_manager import CourseManager
import google.generativeai as genai
from typing import List, Dict, Any, Tuple
from itertools import product
import re

# --- Course Recommendation ---

def recommend_courses(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    genai_model: genai.GenerativeModel,
    desired_credits: int = 18
) -> List[str]:
    """
    Recommends courses based on user interests, including required courses.
    """
    major = user_info.get('major', '')
    year = user_info.get('year', 1)
    interests = user_info.get('interests', '')

    # 1. Get required and all available courses
    required_course_names = course_manager.get_required_course_names(major, year)
    all_courses_df = course_manager.get_all_courses()

    # Calculate credits for required courses
    required_courses_df = all_courses_df[all_courses_df['name'].isin(required_course_names)]
    required_credits = required_courses_df['credits'].sum()
    
    credits_to_recommend = desired_credits - required_credits
    num_courses_to_recommend = max(1, round(credits_to_recommend / 3)) # Assuming average 3 credits per course

    # 2. Filter available electives
    available_electives_df = all_courses_df[~all_courses_df['name'].isin(required_course_names)]
    
    # Filter by recommended year
    available_electives_df = available_electives_df[available_electives_df['recommended_year'].apply(lambda years: year in years)]

    # Simple heuristic to get relevant courses for the prompt
    major_dept_name = major.replace('학과', '').replace('학부', '')
    relevant_courses_df = available_electives_df[
        available_electives_df['department'].str.contains(major_dept_name, na=False) |
        (available_electives_df['type'] == '교양')
    ]
    
    if len(relevant_courses_df) > 200:
        relevant_courses_df = relevant_courses_df.sample(n=200, random_state=1)

    electives_info = "\n".join(
        f"- {row['name']} (구분: {row['type']}, 학점: {row['credits']})"
        for _, row in relevant_courses_df.iterrows()
    )

    # 3. Construct and send prompt to Gemini
    prompt = f"""
    학생의 정보는 다음과 같습니다:
    - 전공: {major}
    - 학년: {year}
    - 총 수강 희망 학점: {desired_credits}
    - 관심분야: "{interests}"

    학생은 다음 과목들을 반드시 수강해야 합니다 (총 {required_credits}학점): {', '.join(required_course_names)}
    
    부족한 학점을 채우기 위해, 아래 목록에서 학생의 관심분야에 맞춰 과목을 {num_courses_to_recommend}개 추천해주세요.
    
    아래는 수강 가능한 선택 과목 및 교양 과목 목록입니다:
    {electives_info}

    결과는 추천하는 과목의 이름만 쉼표(,)로 구분하여 한 줄로 응답해주세요.
    """
    
    try:
        response = genai_model.generate_content(prompt)
        recommended_electives = [name.strip() for name in response.text.strip().split(',')]
    except Exception as e:
        print(f"Error during course recommendation: {e}")
        recommended_electives = []

    # 4. Combine and return
    final_course_list = list(dict.fromkeys(required_course_names + recommended_electives))
    return final_course_list

def recommend_veritas_course(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    genai_model: genai.GenerativeModel
) -> str:
    """
    Interactively helps the user choose a Veritas course.
    """
    # This function will need a more conversational implementation in app.py
    # For now, let's design a prompt that can return a recommendation.
    veritas_courses = course_manager.get_veritas_courses()
    veritas_info = "\n".join(
        f"- {row['name']} (학점: {row['credits']})"
        for _, row in veritas_courses.iterrows()
    )

    prompt = f"""
    학생의 관심분야는 다음과 같습니다: "{user_info.get('interests', '특별한 관심사 없음')}"    
    아래는 수강 가능한 베리타스 교양 과목 목록입니다.
    {veritas_info}
    
    학생의 관심분야와 가장 잘 맞을 것 같은 베리타스 과목을 하나만 추천하고, 그 이유를 설명해주세요.
    """
    try:
        response = genai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"베리타스 과목 추천 중 오류가 발생했습니다: {e}"

def answer_schedule_question(
    user_question: str,
    course_manager: CourseManager,
    genai_model: genai.GenerativeModel
) -> str:
    """
    Answers general questions about course scheduling.
    """
    # This is a general purpose Q&A function.
    # We can provide the model with some context about the available data.
    prompt = f"""
    당신은 수강신청 전문가입니다. 다음 질문에 대해 친절하고 자세하게 답변해주세요.

    질문: "{user_question}"
    """
    try:
        response = genai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"질문 답변 중 오류가 발생했습니다: {e}"


# --- Schedule Generation and Ranking ---

def _check_conflict(schedule: List[Dict[str, Any]]) -> bool:
    """Helper function to check for time conflicts in a schedule."""
    all_slots = []
    for course in schedule:
        all_slots.extend(course.get('time_slots', []))

    for i in range(len(all_slots)):
        for j in range(i + 1, len(all_slots)):
            day1, start1, end1 = all_slots[i]
            day2, start2, end2 = all_slots[j]
            if day1 == day2 and max(start1, start2) < min(end1, end2):
                return True
    return False

def _parse_time_slot(schedule_list: List[str]) -> List[Tuple[str, int, int]]:
    """Helper function to parse schedule strings."""
    slots = []
    if not isinstance(schedule_list, list):
        return slots
    for time_str in schedule_list:
        if pd.isna(time_str) or not time_str:
            continue
        # Assuming format like '월(10:00~11:50)' or 'Mon 10:00-11:50'
        # This regex is more robust to variations.
        parts = re.findall(r'([월화수목금토일])(\d{2}):(\d{2})~(\d{2}):(\d{2})', str(time_str))
        for day, start_h, start_m, end_h, end_m in parts:
            start_total_min = int(start_h) * 60 + int(start_m)
            end_total_min = int(end_h) * 60 + int(end_m)
            slots.append((day, start_total_min, end_total_min))
    return slots

def generate_schedules(
    course_names: List[str],
    course_manager: CourseManager,
    max_schedules: int = 10
) -> List[List[Dict[str, Any]]]:
    """
    Generates all possible non-conflicting schedules.
    """
    all_courses_df = course_manager.get_all_courses()
    courses_to_schedule = {}

    for name in course_names:
        course_sections = all_courses_df[all_courses_df['name'].str.contains(name, na=False)]
        if not course_sections.empty:
            courses_to_schedule[name] = []
            for _, section in course_sections.iterrows():
                time_slots = _parse_time_slot(section['schedule'])
                if time_slots:
                    courses_to_schedule[name].append({
                        'name': section['name'],
                        'schedule': section['schedule'],
                        'time_slots': time_slots
                    })

    if not courses_to_schedule:
        return []

    section_combinations = product(*(courses_to_schedule[name] for name in courses_to_schedule.keys()))
    
    valid_schedules = []
    for schedule_candidate in section_combinations:
        if not _check_conflict(schedule_candidate):
            valid_schedules.append(list(schedule_candidate))
            if len(valid_schedules) >= max_schedules:
                break
    return valid_schedules

def rank_schedules(
    schedules: List[List[Dict[str, Any]]],
    preferences: str,
    genai_model: genai.GenerativeModel
) -> Tuple[Dict[str, Any], str]:
    """
    Ranks schedules based on user preferences.
    """
    if not schedules:
        return None, "추천할 수 있는 시간표를 생성하지 못했습니다."

    schedules_text = ""
    for i, schedule in enumerate(schedules, 1):
        schedules_text += f"--- 시간표 {i} ---\n"
        for course in schedule:
            # The schedule is a list of strings, join them for display
            schedule_str = ", ".join(course['schedule'])
            schedules_text += f"- {course['name']}: {schedule_str}\n"
        schedules_text += "\n"

    prompt = f"""
    학생의 시간표 선호도는 다음과 같습니다: "{preferences}"
    아래는 생성된 {len(schedules)}개의 가능한 시간표 목록입니다.
    {schedules_text}
    위 선호도에 가장 잘 맞는 시간표를 딱 하나만 골라주세요.
    응답은 다음 형식으로만 작성해주세요:
    - 첫째 줄에는 가장 적합한 시간표의 번호를 숫자로만 적어주세요. (예: 3)
    - 둘째 줄부터는 그 시간표를 추천하는 이유를 간략하게 설명해주세요.
    """

    try:
        response = genai_model.generate_content(prompt)
        lines = response.text.strip().split('\n')
        best_schedule_num = int(re.search(r'\d+', lines[0]).group(0))
        explanation = "\n".join(lines[1:]).strip()

        if 1 <= best_schedule_num <= len(schedules):
            return schedules[best_schedule_num - 1], explanation
        else:
            return schedules[0], "AI 추천 분석 실패. 첫 번째 시간표를 기본 추천합니다."
    except Exception as e:
        print(f"Error during schedule ranking: {e}")
        return schedules[0], "AI 추천 중 오류 발생. 첫 번째 시간표를 기본 추천합니다."