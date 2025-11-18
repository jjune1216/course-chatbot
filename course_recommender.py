import pandas as pd
from data_manager import CourseDataManager
import google.generativeai as genai
from typing import List

def recommend_courses(
    major: str, 
    year: int, 
    interests: str, 
    data_manager: CourseDataManager, 
    genai_model: genai.GenerativeModel
) -> List[str]:
    """
    Recommends courses for a student based on their major, year, and interests.

    Args:
        major (str): The student's major.
        year (int): The student's academic year.
        interests (str): A text description of the student's interests.
        data_manager (CourseDataManager): An instance of the data manager.
        genai_model (genai.GenerativeModel): An instance of the Gemini model.

    Returns:
        List[str]: A list of recommended course names, including required courses.
    """
    # 1. Get required courses
    required_courses_df = data_manager.get_required_courses(major, year)
    required_course_names = required_courses_df['course_name'].tolist()

    # 2. Get all available courses for context
    all_courses_df = data_manager.get_all_courses()
    
    # Create a simplified list for the prompt (to save tokens and improve clarity)
    available_electives_df = all_courses_df[
        ~all_courses_df['교과목명'].isin(required_course_names)
    ]
    
    # Further filter to relevant departments if possible (simple version)
    # This is a heuristic to reduce the number of courses sent to the model
    major_dept_name = major.replace('학과', '').replace('학부', '')
    relevant_courses_df = available_electives_df[
        available_electives_df['개설학과'].str.contains(major_dept_name, na=False) |
        (available_electives_df['교과구분'] == '교양')
    ]
    
    # Limit to a reasonable number to avoid an overly long prompt
    if len(relevant_courses_df) > 200:
        relevant_courses_df = relevant_courses_df.sample(n=200, random_state=1)

    # Format for the prompt
    electives_info = "\n".join(
        f"- {row['교과목명']} (구분: {row['교과구분']}, 학년: {row['학년']})"
        for _, row in relevant_courses_df.iterrows()
    )

    # 3. Construct the prompt for the AI
    prompt = f"""
    학생의 정보는 다음과 같습니다:
    - 전공: {major}
    - 학년: {year}
    - 관심분야: "{interests}"

    학생은 다음 과목들을 반드시 수강해야 합니다 (전공 필수 등):
    {', '.join(required_course_names)}

    아래는 수강 가능한 선택 과목 및 교양 과목 목록입니다:
    {electives_info}

    위 정보를 바탕으로, 학생의 관심분야에 맞춰 추가로 수강할 만한 과목을 5개만 추천해주세요.
    결과는 추천하는 과목의 이름만 쉼표(,)로 구분하여 한 줄로 응답해주세요. 
    예시: 경영학원론,마케팅원론,재무관리,회계원리,경제학개론
    """

    # 4. Call the AI model
    try:
        response = genai_model.generate_content(prompt)
        recommended_electives_str = response.text.strip()
        recommended_electives = [name.strip() for name in recommended_electives_str.split(',')]
    except Exception as e:
        print(f"Error during course recommendation: {e}")
        recommended_electives = []

    # 5. Combine required and recommended courses
    final_course_list = required_course_names + recommended_electives
    
    # Remove duplicates just in case
    final_course_list = list(dict.fromkeys(final_course_list))
    
    return final_course_list

if __name__ == '__main__':
    # This is an example, requires API key to be set up
    # from dotenv import load_dotenv
    # import os
    # load_dotenv()
    # genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    # print("--- Testing Course Recommender ---")
    # dm = CourseDataManager()
    # model = genai.GenerativeModel('gemini-1.5-flash')
    
    # test_major = '컴퓨터공학부'
    # test_year = 2
    # test_interests = "인공지능과 데이터 분석에 관심이 많아요."
    
    # recommendations = recommend_courses(test_major, test_year, test_interests, dm, model)
    
    # print(f"Major: {test_major}, Year: {test_year}")
    # print(f"Interests: {test_interests}")
    # print("\nFinal Recommended Courses:")
    # print(recommendations)
    pass
