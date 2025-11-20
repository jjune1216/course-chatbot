from typing import List, Dict, Any, Tuple
import google.generativeai as genai
import re

def rank_schedules(
    schedules: List[List[Dict[str, Any]]],
    preferences: str,
    genai_model: genai.GenerativeModel
) -> Tuple[Dict[str, Any], str]:
    """
    Ranks a list of schedules based on user preferences using an AI model.

    Args:
        schedules (List[List[Dict[str, Any]]]): A list of valid schedules.
        preferences (str): A text description of the user's schedule preferences.
        genai_model (genai.GenerativeModel): An instance of the Gemini model.

    Returns:
        A tuple containing the best schedule (as a dictionary) and the AI's explanation.
        Returns (None, "Error message") if something goes wrong.
    """
    if not schedules:
        return None, "추천할 수 있는 시간표를 생성하지 못했습니다. 다른 과목 조합으로 시도해보세요."

    # 1. Format the schedules for the prompt
    schedules_text = ""
    for i, schedule in enumerate(schedules, 1):
        schedules_text += f"--- 시간표 {i} ---\n"
        for course in schedule:
            schedules_text += f"- {course['교과목명']}: {course['수업교시']}\n"
        schedules_text += "\n"

    # 2. Construct the prompt
    prompt = f"""
    학생의 시간표 선호도는 다음과 같습니다:
    "{preferences}"

    아래는 생성된 {len(schedules)}개의 가능한 시간표 목록입니다.

    {schedules_text}

    위 선호도에 가장 잘 맞는 시간표를 딱 하나만 골라주세요.
    
    응답은 다음 형식으로만 작성해주세요:
    - 첫째 줄에는 가장 적합한 시간표의 번호를 숫자로만 적어주세요. (예: 3)
    - 둘째 줄부터는 그 시간표를 추천하는 이유를 간략하게 설명해주세요.
    """

    # 3. Call the AI model
    try:
        response = genai_model.generate_content(prompt)
        
        # 4. Parse the response
        lines = response.text.strip().split('\n')
        
        best_schedule_num = 0
        explanation = "AI가 추천 이유를 생성하지 못했습니다."

        # Find the schedule number
        for line in lines:
            match = re.search(r'\d+', line)
            if match:
                best_schedule_num = int(match.group(0))
                break
        
        # Get the explanation (everything after the first line)
        if len(lines) > 1:
            explanation = "\n".join(lines[1:]).strip()

        if 1 <= best_schedule_num <= len(schedules):
            best_schedule = schedules[best_schedule_num - 1]
            return best_schedule, explanation
        else:
            # If parsing fails, default to the first schedule
            return schedules[0], "AI의 추천을 분석하지 못했습니다. 첫 번째 시간표를 기본으로 추천합니다."

    except Exception as e:
        print(f"Error during schedule ranking: {e}")
        # Default to returning the first schedule in case of an error
        return schedules[0], "AI 추천 중 오류가 발생하여 첫 번째 시간표를 기본으로 추천합니다."

if __name__ == '__main__':
    print("--- Testing Schedule Ranker ---")
    # This is a mock example and does not call the real API
    
    # Mock schedules
    mock_schedules = [
        [ # Schedule 1 (Friday class)
            {'교과목명': '프로그래밍기초', '수업교시': '월(10:00~11:50)/수(10:00~11:50)'},
            {'교과목명': '자료구조', '수업교시': '화(13:00~14:50)/목(13:00~14:50)'},
            {'교과목명': '경영학원론', '수업교시': '금(09:00~11:50)'},
        ],
        [ # Schedule 2 (No Friday class, all morning)
            {'교과목명': '프로그래밍기초', '수업교시': '월(09:00~10:50)/수(09:00~10:50)'},
            {'교과목명': '자료구조', '수업교시': '화(10:00~11:50)/목(10:00~11:50)'},
            {'교과목명': '사회학개론', '수업교시': '월(11:00~12:50)'},
        ]
    ]
    
    # Mock preferences
    user_prefs = "금요일은 공강이었으면 좋겠고, 가급적 오전에 수업이 몰려있으면 좋겠어요."

    # Mock model response
    class MockModel:
        def generate_content(self, prompt):
            class MockResponse:
                text = "2\n\n금요일에 수업이 없고 모든 강의가 오전에 배치되어 있어 학생의 선호도와 가장 일치합니다."
            return MockResponse()

    best_sched, reason = rank_schedules(mock_schedules, user_prefs, MockModel())
    
    print(f"User Preferences: \"{user_prefs}\"")
    print("\n--- Best Schedule Recommended ---")
    for course in best_sched:
        print(f"- {course['교과목명']}: {course['수업교시']}")
    
    print("\n--- Reason ---")
    print(reason)
