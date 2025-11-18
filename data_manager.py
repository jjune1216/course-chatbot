import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Any

class CourseDataManager:
    """
    Manages course data from a CSV file.
    Provides methods to load and filter course information.
    """

    def __init__(self, file_path: str = 'courses.csv'):
        """
        Initializes the CourseDataManager.

        Args:
            file_path (str): The path to the course CSV file.
        """
        self.df = self._load_courses(file_path)

    def _load_courses(self, file_path: str) -> pd.DataFrame:
        """
        Loads and preprocesses course data from the specified CSV file.
        It expects the actual data to start from the 3rd row.
        """
        try:
            df = pd.read_csv(file_path, skiprows=2, encoding='utf-8')
            df.dropna(subset=['교과목명'], inplace=True)
            df = df[df['수업교시'].notna()]
            df = df[df['수업교시'] != '']
            return df
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
            return pd.DataFrame()
        except Exception as e:
            print(f"An error occurred while loading the CSV file: {e}")
            return pd.DataFrame()

    def _parse_time_slot(self, time_str: str) -> List[Tuple[str, int, int]]:
        """
        Parses a time string like '월(10:00~12:50)' into a list of tuples.
        Returns: [('Day', start_minute, end_minute)]
        """
        slots = []
        if pd.isna(time_str) or time_str == '':
            return slots
        
        time_parts = str(time_str).split('/')
        
        for part in time_parts:
            match = re.match(r'([월화수목금토일])\((\d{1,2}):(\d{2})~(\d{1,2}):(\d{2})\)', part.strip())
            if match:
                day = match.group(1)
                start_hour, start_min = int(match.group(2)), int(match.group(3))
                end_hour, end_min = int(match.group(4)), int(match.group(5))
                
                start_total_min = start_hour * 60 + start_min
                end_total_min = end_hour * 60 + end_min
                
                slots.append((day, start_total_min, end_total_min))
        
        return slots

    def _get_all_time_slots(self, course: pd.Series) -> List[Tuple[str, int, int]]:
        """Returns all time slots for a given course."""
        time_str = course['수업교시']
        return self._parse_time_slot(time_str)

    def _get_course_time_range(self, course: pd.Series) -> Tuple[int, int]:
        """Returns the earliest start time and latest end time for a course in minutes from midnight."""
        slots = self._get_all_time_slots(course)
        if not slots:
            return (0, 0)
        
        start_times = [start for _, start, _ in slots]
        end_times = [end for _, _, end in slots]
        
        return (min(start_times), max(end_times))

    def get_all_courses(self) -> pd.DataFrame:
        """Returns the entire DataFrame of courses."""
        return self.df

    def filter_courses(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Filters courses based on a dictionary of criteria.
        
        Args:
            filters (Dict[str, Any]): A dictionary of filter criteria.
                Example:
                {
                    '교과구분': ['전선', '교양'],
                    '학년': '1학년',
                    '교과목명': 'AI',
                    '주담당교수': '김철수',
                    'prefer_morning': True,
                    'excluded_courses': ['물리학'],
                    'preferred_free_day': '금'
                }
        """
        if self.df.empty:
            return self.df

        filtered_df = self.df.copy()

        for key, value in filters.items():
            if value is None:
                continue

            if key in filtered_df.columns:
                if isinstance(value, list):
                    filtered_df = filtered_df[filtered_df[key].isin(value)]
                elif isinstance(value, str):
                    filtered_df = filtered_df[filtered_df[key].str.contains(value, case=False, na=False)]
                else:
                    filtered_df = filtered_df[filtered_df[key] == value]
            
            elif key == 'prefer_morning':
                def is_morning(course):
                    start_time, _ = self._get_course_time_range(course)
                    return start_time < 720 # 12:00 PM in minutes
                
                if value:
                    filtered_df = filtered_df[filtered_df.apply(is_morning, axis=1)]
                else:
                    filtered_df = filtered_df[~filtered_df.apply(is_morning, axis=1)]

            elif key == 'excluded_courses' and isinstance(value, list):
                for course_name in value:
                    filtered_df = filtered_df[~filtered_df['교과목명'].str.contains(course_name, na=False)]
            
            elif key == 'preferred_free_day' and isinstance(value, str):
                def has_class_on_day(course):
                    slots = self._get_all_time_slots(course)
                    return any(day == value for day, _, _ in slots)
                
                filtered_df = filtered_df[~filtered_df.apply(has_class_on_day, axis=1)]

        return filtered_df.reset_index(drop=True)

if __name__ == '__main__':
    # Example usage of the updated CourseDataManager
    data_manager = CourseDataManager('courses.csv')
    all_courses = data_manager.get_all_courses()
    print(f"--- Loaded {len(all_courses)} courses ---")
    
    # --- Example 1: Filter by course type and year ---
    print("\n--- Filter 1: '교양' courses for '1학년' ---")
    filtered_1 = data_manager.filter_courses(filters={'교과구분': ['교양'], '학년': '1학년'})
    print(f"Found {len(filtered_1)} courses.")
    print(filtered_1[['교과목명', '학년', '교과구분']].head())

    # --- Example 2: Filter for morning classes with a keyword ---
    print("\n--- Filter 2: Morning classes with '컴퓨터' in the name ---")
    filtered_2 = data_manager.filter_courses(filters={'교과목명': '컴퓨터', 'prefer_morning': True})
    print(f"Found {len(filtered_2)} courses.")
    print(filtered_2[['교과목명', '수업교시']].head())

    # --- Example 3: Exclude certain courses and prefer no classes on Friday ---
    print("\n--- Filter 3: No classes on Friday, excluding '물리학' ---")
    filtered_3 = data_manager.filter_courses(filters={'preferred_free_day': '금', 'excluded_courses': ['물리학']})
    print(f"Found {len(filtered_3)} courses.")
    # Verify no courses are on Friday
    has_friday_class = filtered_3['수업교시'].str.contains('금').any()
    print(f"Has Friday classes after filter: {has_friday_class}")
    print(filtered_3[['교과목명', '수업교시']].head())