import pandas as pd
from course_manager import CourseManager
import anthropic
from typing import List, Dict, Any
import re

def recommend_courses(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    claude_client: anthropic.Anthropic,
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

    # 3. Construct and send prompt to Claude
    prompt = f"""
    학생의 정보는 다음과 같습니다:
    - 전공: {major}
    - 학년: {year}
    - 총 수강 희망 학점: {desired_credits}
    - 관심분야: \"{interests}\"\n
    학생은 다음 과목들을 반드시 수강해야 합니다 (총 {required_credits}학점): {', '.join(required_course_names)}
    
    부족한 학점을 채우기 위해, 아래 목록에서 학생의 관심분야에 맞춰 과목을 {num_courses_to_recommend}개 추천해주세요.
    
    **반드시 아래 목록에 있는 과목 중에서만 추천해야 합니다.** 목록에 없는 과목을 만들지 마세요.
    
    아래는 수강 가능한 선택 과목 및 교양 과목 목록입니다:
    {electives_info}

    결과는 추천하는 과목의 이름만 쉼표(,)로 구분하여 한 줄로 응답해주세요. (예: '자료구조', '운영체제', '컴퓨터네트워크')
    """
    
    try:
        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        # Improved parsing and validation
        raw_recommendations = [rec.strip() for rec in response.content[0].text.replace("'", "").replace('"', '').split(',')]
        valid_course_names = set(relevant_courses_df['name'])
        recommended_electives = []
        for rec in raw_recommendations:
            if not rec: continue
            for valid_name in valid_course_names:
                if rec in valid_name:
                    recommended_electives.append(valid_name)
                    break
        recommended_electives = list(dict.fromkeys(recommended_electives)) # Make unique
    except Exception as e:
        print(f"Error during course recommendation: {e}")
        recommended_electives = []

    # 4. Combine and return
    final_course_list = list(dict.fromkeys(required_course_names + recommended_electives))
    return final_course_list

def recommend_jiseong_courses(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    claude_client: anthropic.Anthropic,
    jiseong_type: str
) -> List[str]:
    """
    Recommends 5 Jiseong courses of a specific type based on user interests.
    """
    jiseong_courses = course_manager.get_jiseong_courses(jiseong_type)
    jiseong_info = "\n".join(
        f"- {row['name']} (학점: {row['credits']})"
        for _, row in jiseong_courses.iterrows()
    )

    prompt = f"""
    학생의 관심분야는 다음과 같습니다: "{user_info.get('interests', '특별한 관심사 없음')}"    
    아래는 수강 가능한 '{jiseong_type}' 교양 과목 목록입니다.
    {jiseong_info}
    
    학생의 관심분야와 가장 잘 맞을 것 같은 과목을 5개 추천해주세요.
    **반드시 위 목록에 있는 과목 중에서만 추천해야 합니다.** 목록에 없는 과목을 만들지 마세요.
    결과는 추천하는 과목의 이름만 쉼표(,)로 구분하여 한 줄로 응답해주세요. (예: '과목명1', '과목명2', '과목명3', '과목명4', '과목명5')
    """
    try:
        print(f"DEBUG (jiseong): Initial jiseong_courses df shape: {jiseong_courses.shape}")
        print(f"DEBUG (jiseong): Prompt info: {jiseong_info[:500]}...")
        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        print(f"DEBUG (jiseong): Claude raw response: {response.content[0].text}")
        # Improved parsing and validation
        raw_recommendations = [rec.strip() for rec in response.content[0].text.replace("'", "").replace('"', '').split(',')]
        print(f"DEBUG (jiseong): Parsed raw_recommendations: {raw_recommendations}")
        
        valid_course_names = set(jiseong_courses['name'])
        recommended_courses = []
        for rec in raw_recommendations:
            if not rec: continue
            for valid_name in valid_course_names:
                if rec in valid_name:
                    recommended_courses.append(valid_name)
                    break # Move to the next recommendation once a match is found
        
        recommended_courses = list(dict.fromkeys(recommended_courses)) # Make unique
        print(f"DEBUG (jiseong): Final validated recommendations: {recommended_courses}")
        return recommended_courses
    except Exception as e:
        print(f"Error during Jiseong course recommendation: {e}")
        return []

def recommend_veritas_course(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    claude_client: anthropic.Anthropic,
    taken_courses: List[str] = None
) -> List[str]:
    """
    Recommends 5 Veritas courses based on user interests.
    """
    veritas_courses = course_manager.get_veritas_courses()

    # Filter out courses the user has already taken
    if taken_courses:
        veritas_courses = veritas_courses[~veritas_courses['name'].isin(taken_courses)]
    
    veritas_info = "\n".join(
        f"- {row['name']} (학점: {row['credits']})"
        for _, row in veritas_courses.iterrows()
    )
    print(f"DEBUG: Veritas courses passed to Claude: {veritas_info}")

    prompt = f"""
    학생의 관심분야는 다음과 같습니다: "{user_info.get('interests', '특별한 관심사 없음')}"    
    아래는 수강 가능한 베리타스 교양 과목 목록입니다.
    {veritas_info}
    
    학생의 관심분야와 가장 잘 맞을 것 같은 베리타스 과목을 5개 추천해주세요.
    **반드시 위 목록에 있는 과목 중에서만 추천해야 합니다.** 목록에 없는 과목을 만들지 마세요.
    결과는 추천하는 과목의 이름만 쉼표(,)로 구분하여 한 줄로 응답해주세요. (예: '과목명1', '과목명2', '과목명3', '과목명4', '과목명5')
    """
    try:
        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        print(f"DEBUG: Claude response: {response.content[0].text}")
        # Improved parsing and validation
        raw_recommendations = [rec.strip() for rec in response.content[0].text.replace("'", "").replace('"', '').split(',')]
        valid_course_names = set(veritas_courses['name'])
        recommended_courses = []
        for rec in raw_recommendations:
            if not rec: continue
            for valid_name in valid_course_names:
                if rec in valid_name:
                    recommended_courses.append(valid_name)
                    break
        recommended_courses = list(dict.fromkeys(recommended_courses)) # Make unique
        return recommended_courses
    except Exception as e:
        print(f"Error during Veritas course recommendation: {e}")
        return []


