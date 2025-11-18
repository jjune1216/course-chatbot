import pandas as pd
from data_manager import CourseDataManager
from typing import List, Dict, Any
from itertools import product

def check_conflict(schedule: List[Dict[str, Any]]) -> bool:
    """
    Checks if there are any time conflicts within a given schedule.

    Args:
        schedule (List[Dict[str, Any]]): A list of course objects, 
                                         where each course has a 'time_slots' key.

    Returns:
        bool: True if there is a conflict, False otherwise.
    """
    all_slots = []
    for course in schedule:
        all_slots.extend(course['time_slots'])

    for i in range(len(all_slots)):
        for j in range(i + 1, len(all_slots)):
            day1, start1, end1 = all_slots[i]
            day2, start2, end2 = all_slots[j]

            if day1 == day2:
                # Check for overlap: not (end1 <= start2 or end2 <= start1)
                if max(start1, start2) < min(end1, end2):
                    return True  # Conflict found
    return False

def generate_schedules(
    course_names: List[str], 
    data_manager: CourseDataManager,
    max_schedules: int = 10
) -> List[List[Dict[str, Any]]]:
    """
    Generates all possible non-conflicting schedules from a list of course names.

    Args:
        course_names (List[str]): A list of course names to schedule.
        data_manager (CourseDataManager): An instance of the data manager.
        max_schedules (int): The maximum number of schedules to generate.

    Returns:
        A list of valid schedules. Each schedule is a list of course dictionaries.
    """
    # 1. Get all course offerings for the desired course names
    all_available_courses = data_manager.get_all_courses()
    
    # Create a dictionary to hold all sections for each course name
    courses_to_schedule = {}
    for name in course_names:
        # Find all rows that match the course name
        course_sections = all_available_courses[all_available_courses['교과목명'].str.contains(name, na=False)]
        
        if not course_sections.empty:
            courses_to_schedule[name] = []
            for _, section in course_sections.iterrows():
                time_slots = data_manager.get_all_time_slots(section)
                if time_slots:  # Only consider sections with defined times
                    courses_to_schedule[name].append({
                        '교과목명': section['교과목명'],
                        '강좌번호': section['강좌번호'],
                        '주담당교수': section['주담당교수'],
                        '수업교시': section['수업교시'],
                        'time_slots': time_slots
                    })

    # Remove courses that had no valid sections
    valid_course_names = list(courses_to_schedule.keys())
    if not valid_course_names:
        return []

    # 2. Use itertools.product to create all combinations of sections
    section_combinations = product(*(courses_to_schedule[name] for name in valid_course_names))

    # 3. Filter combinations to find valid, non-conflicting schedules
    valid_schedules = []
    for schedule_candidate in section_combinations:
        if not check_conflict(schedule_candidate):
            valid_schedules.append(list(schedule_candidate))
            if len(valid_schedules) >= max_schedules:
                break  # Stop once we reach the limit

    return valid_schedules

if __name__ == '__main__':
    print("--- Testing Schedule Generator ---")
    dm = CourseDataManager()
    
    # Example course list (required + recommended)
    test_courses = ['프로그래밍기초', '자료구조', '경영학원론', '사회학개론']
    
    print(f"Attempting to generate schedules for: {test_courses}")
    
    generated_schedules = generate_schedules(test_courses, dm, max_schedules=5)
    
    if not generated_schedules:
        print("\nNo valid schedules could be generated.")
    else:
        print(f"\nSuccessfully generated {len(generated_schedules)} valid schedules.")
        for i, schedule in enumerate(generated_schedules, 1):
            print(f"\n--- Schedule {i} ---")
            total_credits = 0
            for course in schedule:
                print(f"  - {course['교과목명']} ({course['강좌번호']}): {course['수업교시']}")
            print("-" * 20)
