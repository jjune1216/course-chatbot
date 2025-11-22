import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Any

class CourseDataManager:
    """
    Manages course data from CSV files.
    Provides methods to load, filter, and access course information.
    """

    def __init__(self, courses_file: str = 'data/courses.csv', required_file: str = 'data/required_courses.csv'):
        """
        Initializes the CourseDataManager by loading both course and requirement data.
        """
        self.df = self._load_courses(courses_file)
        self.required_df = self._load_required_courses(required_file)

    def _load_courses(self, file_path: str) -> pd.DataFrame:
        """Loads and preprocesses the main course data file."""
        try:
            df = pd.read_csv(file_path, skiprows=2, encoding='utf-8')
            df.dropna(subset=['교과목명'], inplace=True)
            df = df[df['수업교시'].notna()]
            df = df[df['수업교시'] != '']
            # Convert '학점' to numeric, coercing errors
            df['학점'] = pd.to_numeric(df['학점'], errors='coerce')
            return df
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
            return pd.DataFrame()
        except Exception as e:
            print(f"An error occurred while loading the courses CSV file: {e}")
            return pd.DataFrame()

    def _load_required_courses(self, file_path: str) -> pd.DataFrame:
        """Loads the required courses data file."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            # Convert 'year' to numeric
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            return df
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
            return pd.DataFrame()
        except Exception as e:
            print(f"An error occurred while loading the required courses CSV file: {e}")
            return pd.DataFrame()

    def get_required_courses(self, major: str, year: int) -> pd.DataFrame:
        """
        Gets required courses for a given major and year.
        
        Args:
            major (str): The student's major.
            year (int): The student's year.
            
        Returns:
            pd.DataFrame: A DataFrame of required courses.
        """
        if self.required_df.empty:
            return pd.DataFrame()
        
        # Filter by major and year
        # It will include courses for the given year and all previous years
        major_reqs = self.required_df[
            (self.required_df['major'].str.contains(major, case=False, na=False)) &
            (self.required_df['year'] <= year)
        ]
        return major_reqs

    def _parse_time_slot(self, time_str: str) -> List[Tuple[str, int, int]]:
        """Parses a time string into a list of (Day, start_minute, end_minute) tuples."""
        slots = []
        if pd.isna(time_str) or time_str == '':
            return slots
        
        time_parts = str(time_str).split('/')
        
        for part in time_parts:
            match = re.match(r'([월화수목금토일])\((\d{1,2}):(\d{2})~(\d{1,2}):(\d{2})\)', part.strip())
            if match:
                day, start_hour, start_min, end_hour, end_min = match.groups()
                start_total_min = int(start_hour) * 60 + int(start_min)
                end_total_min = int(end_hour) * 60 + int(end_min)
                slots.append((day, start_total_min, end_total_min))
        
        return slots

    def get_all_time_slots(self, course: pd.Series) -> List[Tuple[str, int, int]]:
        """Returns all time slots for a given course series."""
        time_str = course['수업교시']
        return self._parse_time_slot(time_str)

    def get_all_courses(self) -> pd.DataFrame:
        """Returns the entire DataFrame of all available courses."""
        return self.df

    def filter_courses(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Filters the main course list based on a dictionary of criteria."""
        if self.df.empty:
            return self.df

        filtered_df = self.df.copy()

        for key, value in filters.items():
            if value is None or (isinstance(value, list) and not value):
                continue

            if key in filtered_df.columns:
                if isinstance(value, list):
                    filtered_df = filtered_df[filtered_df[key].isin(value)]
                elif isinstance(value, str):
                    filtered_df = filtered_df[filtered_df[key].str.contains(value, case=False, na=False)]
                else:
                    filtered_df = filtered_df[filtered_df[key] == value]
            
        return filtered_df.reset_index(drop=True)

if __name__ == '__main__':
    # Example usage of the updated CourseDataManager
    data_manager = CourseDataManager()
    
    if not data_manager.required_df.empty:
        print("--- Testing Required Courses ---")
        major = '컴퓨터공학부'
        year = 2
        req_courses = data_manager.get_required_courses(major, year)
        print(f"Required courses for {major}, Year {year}:")
        print(req_courses)
    else:
        print("Could not load required courses.")

    if not data_manager.df.empty:
        print("\n--- Testing Course Filtering ---")
        filters = {'교과목명': '컴퓨터'}
        filtered = data_manager.filter_courses(filters)
        print(f"Found {len(filtered)} courses with '{filters['교과목명']}' in the name.")
        print(filtered[['교과목명', '주담당교수', '수업교시']].head())
    else:
        print("Could not load main course list.")