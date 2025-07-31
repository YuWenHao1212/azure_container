"""Course Category Mapping Utilities"""

CATEGORY_MAPPING = {
    "Tech": [
        "Computer Science",
        "Data Science",
        "Information Technology",
        "Software Development",
        "Mobile and Web Development",
        "Engineering",
        "Cloud Computing",
        "Cybersecurity",
        "Machine Learning",
        "Artificial Intelligence"
    ],
    "Non-Tech": [
        "Business",
        "Arts and Humanities",
        "Language Learning",
        "Health",
        "Personal Development",
        "Social Sciences",
        "Math and Logic",
        "Physical Science and Engineering",
        "Marketing",
        "Leadership and Management"
    ]
}

def get_category_filter(category: str) -> list[str]:
    """
    取得分類過濾清單

    Args:
        category: "Tech" 或 "Non-Tech"

    Returns:
        對應的具體分類清單
    """
    if category in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[category]
    return []

def categorize_course(course_category: str) -> str:
    """判斷課程屬於 Tech 或 Non-Tech"""
    if not course_category:
        return ""

    for main_cat, sub_cats in CATEGORY_MAPPING.items():
        if course_category in sub_cats:
            return main_cat

    # 預設判斷邏輯
    tech_keywords = ["tech", "data", "computer", "software", "coding"]
    if any(keyword in course_category.lower() for keyword in tech_keywords):
        return "Tech"

    return "Non-Tech"
