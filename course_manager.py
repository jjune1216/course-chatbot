import re
import json
import pandas as pd
from typing import List, Dict, Any

class CourseManager:
    """
    Manages all course and requirement data from the JSON files.
    """

    def __init__(self, courses_file: str = 'data/courses.json', requirements_file: str = 'data/requirements.json'):
        """
        Initializes the CourseManager by loading both course and requirement data.
        """
        self.courses_df = self._load_courses(courses_file)
        self.requirements_data = self._load_requirements(requirements_file)

    def _load_courses(self, file_path: str) -> pd.DataFrame:
        """Loads the main course data from JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            # Basic preprocessing
            df['credits'] = pd.to_numeric(df['credits'], errors='coerce')
            return df
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
            return pd.DataFrame()
        except Exception as e:
            print(f"An error occurred while loading the courses JSON file: {e}")
            return pd.DataFrame()

    def _load_requirements(self, file_path: str) -> Dict:
        """Loads the graduation requirements from JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
            return {}
        except Exception as e:
            print(f"An error occurred while loading the requirements JSON file: {e}")
            return {}

    def get_all_courses(self) -> pd.DataFrame:
        """Returns the entire DataFrame of all available courses."""
        return self.courses_df

    def get_veritas_courses(self) -> pd.DataFrame:
        """Returns a DataFrame of all Veritas courses."""
        if self.courses_df.empty:
            return pd.DataFrame()
        veritas_courses = self.courses_df[self.courses_df['type'] == '베리타스']
        print(f"DEBUG: Found {len(veritas_courses)} Veritas courses.")
        return veritas_courses

    def get_jiseong_courses(self, jiseong_type: str) -> pd.DataFrame:
        """Returns a DataFrame of all Jiseong courses of a specific type."""
        if self.courses_df.empty:
            return pd.DataFrame()

        # Mapping from app-facing strings to the data's keys_category
        category_mapping = {
            "문화 해석과 상상": ["문화 해석과 상상"],
            "역사적 탐구와 철학적 사유": ["역사적 탐구와 철학적 사유"],
            "인간의 이해와 사회 분석": ["인간의 이해와 사회 분석"]
        }

        target_categories = category_mapping.get(jiseong_type)

        if target_categories is not None:
            return self.courses_df[
                (self.courses_df['type'] == '지성의 열쇠') &
                (self.courses_df['keys_category'].isin(target_categories))
            ]
        else:
            # Fallback for any unmapped types
            return pd.DataFrame()

    def get_required_course_names(self, major: str, year: int) -> List[str]:
        """
        Gets a list of required course names for a given major and year.
        This is a simplified implementation and may need to be expanded.
        """
        required_names = []
        if not self.requirements_data:
            return required_names

        grad_reqs = self.requirements_data.get("graduation_requirements", {})

        # 1. General Education
        gen_ed = grad_reqs.get("general_education", {})
        if "writing" in gen_ed:
            required_names.extend(gen_ed["writing"].get("courses", []))
        if "basic_science_math" in gen_ed:
            required_names.extend(gen_ed["basic_science_math"].get("mandatory_courses", []))

        # 2. Major Requirements
        major_reqs = grad_reqs.get("major", {})
        # This part is tricky as the major name in the app might not directly
        # map to the keys in the JSON. For now, we assume a simple case.
        # This logic should be improved for a real application.
        if "mandatory_major (전필)" in major_reqs:
            required_names.extend(major_reqs["mandatory_major (전필)"].get("course_names", []))
        
        return list(dict.fromkeys(required_names)) # Return unique course names

    def get_course_details(self, course_name: str) -> pd.Series:
        """
        Retrieves the full details for a specific course by its name.
        Returns the first match found.
        """
        if self.courses_df.empty:
            return None
        
        course_series = self.courses_df[self.courses_df['name'] == course_name]
        
        if not course_series.empty:
            return course_series.iloc[0]
        return None
