import anthropic
from typing import List, Dict, Any, Tuple
from course_manager import CourseManager

# --- Modular Imports ---
import course_recommender
import schedule_generator
import schedule_ranker

# --- Controller Functions ---

def recommend_courses(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    claude_client: anthropic.Anthropic,
    desired_credits: int = 18
) -> List[str]:
    """
    Controller function to delegate course recommendation.
    """
    return course_recommender.recommend_courses(
        user_info, course_manager, claude_client, desired_credits
    )

def recommend_veritas_course(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    claude_client: anthropic.Anthropic,
    taken_courses: List[str] = None
) -> List[str]:
    """
    Controller function to delegate Veritas course recommendation.
    """
    recommendations = course_recommender.recommend_veritas_course(
        user_info, course_manager, claude_client, taken_courses
    )
    print(f"DEBUG: Recommendations from recommender: {recommendations}")
    return recommendations

def recommend_jiseong_courses(
    user_info: Dict[str, Any],
    course_manager: CourseManager,
    claude_client: anthropic.Anthropic,
    jiseong_type: str
) -> List[str]:
    """
    Controller function to delegate Jiseong course recommendation.
    """
    return course_recommender.recommend_jiseong_courses(
        user_info, course_manager, claude_client, jiseong_type
    )

def generate_schedules(
    course_names: List[str],
    course_manager: CourseManager,
    max_schedules: int = 10
) -> List[List[Dict[str, Any]]]:
    """
    Controller function to delegate schedule generation.
    """
    return schedule_generator.generate_schedules(
        course_names, course_manager, max_schedules
    )

def rank_schedules(
    schedules: List[List[Dict[str, Any]]],
    preferences: str,
    claude_client: anthropic.Anthropic
) -> Tuple[Dict[str, Any], str]:
    """
    Controller function to delegate schedule ranking.
    """
    return schedule_ranker.rank_schedules(
        schedules, preferences, claude_client
    )