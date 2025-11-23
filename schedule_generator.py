import pandas as pd
from course_manager import CourseManager
from typing import List, Dict, Any, Tuple
from itertools import product
import re

def _check_conflict(schedule: List[Dict[str, Any]]) -> bool:
    """Helper function to check for time conflicts in a schedule."""
    all_slots = []
    for course in schedule:
        # Ensure 'time_slots' key exists and is iterable
        if 'time_slots' in course and isinstance(course['time_slots'], list):
            all_slots.extend(course['time_slots'])

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
        
        # Regex to match 'Day/Day HH:MM-HH:MM' or 'Day HH:MM-HH:MM'
        match_eng = re.match(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:/(Mon|Tue|Wed|Thu|Fri|Sat|Sun))? (\d{2}):(\d{2})-(\d{2}):(\d{2})', time_str)
        if match_eng:
            days = [match_eng.group(1)]
            if match_eng.group(2): # If there's a second day (e.g., Mon/Wed)
                days.append(match_eng.group(2))
            
            start_h, start_m, end_h, end_m = int(match_eng.group(3)), int(match_eng.group(4)), int(match_eng.group(5)), int(match_eng.group(6))
            
            start_total_min = start_h * 60 + start_m
            end_total_min = end_h * 60 + end_m
            
            for day in days:
                slots.append((day, start_total_min, end_total_min))
        else:
            # Fallback for Korean format if it exists in other data
            parts_kor = re.findall(r'([월화수목금토일])(\d{2}):(\d{2})~(\d{2}):(\d{2})', str(time_str))
            for day, start_h, start_m, end_h, end_m in parts_kor:
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
