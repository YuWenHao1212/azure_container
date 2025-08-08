"""
Utility functions for gap analysis operations.

These functions were extracted from gap_analysis.py (V1) to be shared
between different implementations and avoid code duplication.
"""
import logging
import re
from typing import Any

from src.services.text_processing import convert_markdown_to_html


def clean_and_process_lines(section_content: str | None) -> list[str]:
    """
    Clean and process text lines into HTML list items.

    Args:
        section_content: Raw text content

    Returns:
        List of HTML-formatted lines
    """
    lines = []
    if section_content:
        for line in section_content.strip().splitlines():
            # Remove bullet points and numbering
            text = re.sub(r'^\s*[-*•]\s*', '', line.strip())
            text = re.sub(r'^\s*\d+\.\s*', '', text)
            if text:
                lines.append(convert_markdown_to_html(text))
    return lines


def parse_skill_development_priorities(skill_content: str) -> list[dict[str, str]]:
    """
    Parse skill development priorities from formatted string.

    Expected format: SKILL_N::SkillName::CATEGORY::Description

    Args:
        skill_content: Raw skill content

    Returns:
        List of skill dictionaries
    """
    skills = []
    if not skill_content:
        return skills

    lines = skill_content.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line or '::' not in line:
            continue

        parts = line.split('::', 3)
        if len(parts) >= 4:
            skill_id, skill_name, category, description = parts

            # Skip if skill_name is empty
            if not skill_name.strip():
                continue

            # Validate category
            category = category.upper()
            if category not in ['TECHNICAL', 'NON_TECHNICAL']:
                category = 'TECHNICAL'  # Default

            skills.append({
                "skill_name": skill_name.strip(),
                "skill_category": category,
                "description": description.strip()
            })

    return skills


def parse_gap_response(content: str) -> dict[str, Any]:
    """
    Parse LLM gap analysis response from XML format.

    Args:
        content: Raw LLM response with XML tags

    Returns:
        Parsed gap analysis dictionary
    """
    # Extract each section using regex
    cs = re.search(r'<core_strengths>(.*?)</core_strengths>', content, re.S)
    kg = re.search(r'<key_gaps>(.*?)</key_gaps>', content, re.S)
    qi = re.search(r'<quick_improvements>(.*?)</quick_improvements>', content, re.S)
    oa = re.search(r'<overall_assessment>(.*?)</overall_assessment>', content, re.S)
    sdp = re.search(r'<skill_development_priorities>(.*?)</skill_development_priorities>', content, re.S)

    # Process each section
    strengths = clean_and_process_lines(cs.group(1) if cs else None)
    gaps = clean_and_process_lines(kg.group(1) if kg else None)
    improvements = clean_and_process_lines(qi.group(1) if qi else None)

    # Process overall assessment (paragraph format)
    assessment_text = ''
    if oa:
        raw_assessment = oa.group(1).strip()
        logging.info(f"[GAP_ANALYSIS] Raw assessment length: {len(raw_assessment)}")

        if raw_assessment:
            # Log FULL assessment for debugging (not just preview)
            logging.info(f"[GAP_ANALYSIS] Raw assessment FULL content: {raw_assessment!r}")

            # Join lines
            joined_text = ' '.join(line.strip() for line in raw_assessment.splitlines() if line.strip())
            logging.info(f"[GAP_ANALYSIS] Joined text length: {len(joined_text)}")
            logging.debug(f"[GAP_ANALYSIS] Joined text FULL: {joined_text!r}")

            # Convert to HTML
            assessment_text = convert_markdown_to_html(joined_text)
            logging.info(f"[GAP_ANALYSIS] HTML converted length: {len(assessment_text)}")
            logging.debug(f"[GAP_ANALYSIS] HTML converted FULL: {assessment_text!r}")

            # Fallback if conversion resulted in empty
            if not assessment_text and joined_text:
                logging.warning("[GAP_ANALYSIS] Markdown conversion resulted in empty text, using raw content")
                assessment_text = joined_text
        else:
            logging.warning("[GAP_ANALYSIS] Overall assessment tag found but content is empty")
            # Provide a default message instead of empty
            assessment_text = "Unable to generate overall assessment. Please review the strengths and gaps above."
    else:
        logging.warning("[GAP_ANALYSIS] Overall assessment tag not found in response")
        # Provide a default message
        assessment_text = "Overall assessment not available. Please refer to the detailed analysis above."

    # Process skill development priorities
    skill_queries = []
    if sdp:
        try:
            skill_content = sdp.group(1).strip()
            logging.info(f"Processing skill content: {len(skill_content)} characters")
            skill_queries = parse_skill_development_priorities(skill_content)
            logging.info(f"Parsed {len(skill_queries)} skills")
        except Exception as e:
            logging.error(f"Error processing skill_development_priorities: {e}")
            skill_queries = []

    return {
        "strengths": strengths,
        "gaps": gaps,
        "improvements": improvements,
        "assessment": assessment_text,
        "skill_queries": skill_queries
    }


def format_gap_analysis_html(parsed_response: dict[str, Any]) -> dict[str, Any]:
    """
    Format parsed gap analysis into HTML structure.

    Args:
        parsed_response: Parsed gap analysis data

    Returns:
        HTML formatted gap analysis
    """
    # Convert lists to HTML ordered lists with fallback for empty lists
    def format_list_with_fallback(items: list[str], field_name: str) -> str:
        if items:
            return '<ol>' + ''.join(f'<li>{item}</li>' for item in items) + '</ol>'
        else:
            logging.warning(f"[GAP_ANALYSIS] {field_name} is empty")
            return f'<ol><li>Unable to analyze {field_name.lower().replace("_", " ")}. Please try again.</li></ol>'

    core_strengths = format_list_with_fallback(parsed_response.get('strengths', []), 'core_strengths')
    key_gaps = format_list_with_fallback(parsed_response.get('gaps', []), 'key_gaps')
    quick_improvements = format_list_with_fallback(parsed_response.get('improvements', []), 'quick_improvements')

    # Overall assessment is already in paragraph format
    assessment = parsed_response.get('assessment', '')
    if assessment and assessment not in [
        "",
        "Unable to generate overall assessment. Please review the strengths and gaps above.",
        "Overall assessment not available. Please refer to the detailed analysis above."
    ]:
        overall_assessment = f'<p>{assessment}</p>'
    else:
        logging.warning("[GAP_ANALYSIS] Empty or default overall assessment detected in formatting")
        overall_assessment = (
            '<p>Unable to generate a comprehensive assessment. '
            'Please review the individual sections above for detailed analysis.</p>'
        )

    # Log the final HTML output
    logging.info(f"[GAP_ANALYSIS_HTML] Final OverallAssessment HTML: {overall_assessment[:200]!r}...")

    # Log if we're still producing empty result
    if overall_assessment == '<p></p>':
        logging.error("[GAP_ANALYSIS] CRITICAL: Still producing empty <p></p> for OverallAssessment!")
        logging.error(f"[GAP_ANALYSIS] Assessment value was: {assessment!r}")

    return {
        "CoreStrengths": core_strengths,
        "KeyGaps": key_gaps,
        "QuickImprovements": quick_improvements,
        "OverallAssessment": overall_assessment,
        "SkillSearchQueries": parsed_response['skill_queries']
    }


def check_for_empty_fields(formatted_response: dict[str, Any]) -> list[str]:
    """
    Check if any gap analysis fields are empty or contain only default messages.

    Args:
        formatted_response: The formatted gap analysis response

    Returns:
        List of field names that are empty or contain default values
    """
    empty_fields = []

    # Define what constitutes "empty" for each field
    field_checks = {
        "CoreStrengths": (
            formatted_response.get("CoreStrengths"),
            ["<ol></ol>", "<ol><li>Unable to analyze core strengths. Please try again.</li></ol>"]
        ),
        "KeyGaps": (
            formatted_response.get("KeyGaps"),
            ["<ol></ol>", "<ol><li>Unable to analyze key gaps. Please try again.</li></ol>"]
        ),
        "QuickImprovements": (
            formatted_response.get("QuickImprovements"),
            ["<ol></ol>", "<ol><li>Unable to analyze quick improvements. Please try again.</li></ol>"]
        ),
        "OverallAssessment": (
            formatted_response.get("OverallAssessment"),
            [
                "<p></p>",
                "<p>Unable to generate a comprehensive assessment. "
                "Please review the individual sections above for detailed analysis.</p>",
                "<p>Unable to generate overall assessment. Please review the strengths and gaps above.</p>",
                "<p>Overall assessment not available. Please refer to the detailed analysis above.</p>"
            ]
        ),
        "SkillSearchQueries": (
            formatted_response.get("SkillSearchQueries"),
            []
        )
    }

    # Check each field
    for field_name, (value, empty_values) in field_checks.items():
        if field_name == "SkillSearchQueries":
            # For skill queries, check if it's an empty list
            if not value or len(value) == 0:
                empty_fields.append(field_name)
        else:
            # For other fields, check against known empty values
            if not value or value in empty_values:
                empty_fields.append(field_name)

    return empty_fields
