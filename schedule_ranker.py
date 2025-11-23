import pandas as pd
import anthropic
from typing import List, Dict, Any, Tuple
import re

def rank_schedules(
    schedules: List[List[Dict[str, Any]]],
    preferences: str,
    claude_client: anthropic.Anthropic
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
        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        lines = response.content[0].text.strip().split('\n')
        best_schedule_num = int(re.search(r'\d+', lines[0]).group(0))
        explanation = "\n".join(lines[1:]).strip()

        if 1 <= best_schedule_num <= len(schedules):
            return schedules[best_schedule_num - 1], explanation
        else:
            return schedules[0], "AI 추천 분석 실패. 첫 번째 시간표를 기본 추천합니다."
    except Exception as e:
        print(f"Error during schedule ranking: {e}")
        return schedules[0], "AI 추천 중 오류 발생. 첫 번째 시간표를 기본 추천합니다."

