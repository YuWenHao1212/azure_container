#!/usr/bin/env python3
"""
Analyze test data characteristics that might affect performance results.
This script examines the actual job descriptions used in performance tests
to identify potential causes for Medium JD performance anomalies.
"""

import json
import re
import statistics
from typing import Any


def analyze_text_characteristics(text: str) -> dict[str, Any]:
    """Analyze various characteristics of text that might affect processing time."""
    return {
        "char_count": len(text),
        "word_count": len(text.split()),
        "line_count": len(text.split('\n')),
        "paragraph_count": len([p for p in text.split('\n\n') if p.strip()]),
        "sentence_count": len(re.split(r'[.!?]+', text)),
        "bullet_points": text.count('-') + text.count('•') + text.count('*'),
        "special_chars": len(re.findall(r'[^\w\s]', text)),
        "uppercase_words": len(re.findall(r'\b[A-Z]{2,}\b', text)),
        "technical_terms": len(re.findall(r'\b(?:API|SQL|AWS|Docker|Kubernetes|CI/CD|Git|REST|JSON|XML|HTTP|HTTPS|NoSQL|PostgreSQL|MongoDB|Redis|FastAPI|Django|Flask|React|TypeScript|JavaScript|Python|Java|Golang|Rust|GraphQL|RabbitMQ|Kafka|EC2|S3|Lambda|RDS)\b', text, re.IGNORECASE)),
        "complexity_score": None  # Will calculate based on other metrics
    }


def calculate_complexity_score(characteristics: dict[str, Any]) -> float:
    """Calculate a complexity score based on text characteristics."""
    score = 0

    # Base score from length
    score += characteristics['char_count'] * 0.01

    # Add complexity for structure
    score += characteristics['bullet_points'] * 2
    score += characteristics['paragraph_count'] * 5
    score += characteristics['sentence_count'] * 1

    # Add complexity for technical content
    score += characteristics['technical_terms'] * 3
    score += characteristics['uppercase_words'] * 1
    score += characteristics['special_chars'] * 0.1

    return round(score, 2)


def get_test_cases() -> list[dict[str, Any]]:
    """Get the same test cases used in performance tests."""
    return [
        {
            "name": "Small JD (200 chars)",
            "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and Django. Must have strong knowledge of microservices architecture, Docker, Kubernetes, and AWS cloud services. Excellent problem-solving skills required."
        },
        {
            "name": "Medium JD (500 chars)",
            "job_description": """We are seeking an experienced Full Stack Developer to join our growing team. The ideal candidate will have:  # noqa: E501
- 5+ years of experience with Python, FastAPI, and Django
- Strong proficiency in React, TypeScript, and modern JavaScript
- Experience with microservices architecture and RESTful APIs
- Hands-on experience with Docker, Kubernetes, and CI/CD pipelines
- Familiarity with AWS or Azure cloud services
- Knowledge of PostgreSQL, MongoDB, and Redis
- Experience with Agile methodologies and version control (Git)
- Excellent communication and problem-solving skills"""
        },
        {
            "name": "Large JD (1000+ chars)",
            "job_description": """Senior Backend Engineer - Python/FastAPI

We are looking for a talented Senior Backend Engineer to join our engineering team. You will be responsible for designing, developing, and maintaining scalable backend services.  # noqa: E501

Key Responsibilities:
- Design and implement RESTful APIs using Python and FastAPI
- Build and maintain microservices architecture
- Optimize database queries and improve system performance
- Implement security best practices and data protection
- Collaborate with frontend developers and DevOps engineers
- Mentor junior developers and conduct code reviews

Requirements:
- 5+ years of backend development experience
- Expert-level Python programming skills
- Strong experience with FastAPI, Django, or Flask
- Proficiency in SQL and NoSQL databases (PostgreSQL, MongoDB, Redis)
- Experience with message queues (RabbitMQ, Kafka)
- Hands-on experience with Docker and Kubernetes
- Familiarity with AWS services (EC2, S3, Lambda, RDS)
- Understanding of software design patterns and SOLID principles
- Experience with CI/CD pipelines and automated testing
- Excellent problem-solving and analytical skills

Nice to have:
- Experience with GraphQL
- Knowledge of Golang or Rust
- Contributions to open-source projects
- AWS certifications"""
        }
    ]


def analyze_all_test_cases():
    """Analyze all test cases and identify potential performance factors."""
    print("=" * 80)
    print("TEST DATA ANALYSIS - PERFORMANCE IMPACT INVESTIGATION")
    print("=" * 80)
    print()

    test_cases = get_test_cases()
    analysis_results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['name']}")
        print("-" * 60)

        text = test_case['job_description']
        characteristics = analyze_text_characteristics(text)
        characteristics['complexity_score'] = calculate_complexity_score(characteristics)

        # Print analysis
        print(f"Text Length: {characteristics['char_count']} characters")
        print(f"Word Count: {characteristics['word_count']} words")
        print(f"Line Count: {characteristics['line_count']} lines")
        print(f"Paragraph Count: {characteristics['paragraph_count']} paragraphs")
        print(f"Sentence Count: {characteristics['sentence_count']} sentences")
        print(f"Bullet Points: {characteristics['bullet_points']}")
        print(f"Technical Terms: {characteristics['technical_terms']}")
        print(f"Uppercase Words: {characteristics['uppercase_words']}")
        print(f"Special Characters: {characteristics['special_chars']}")
        print(f"Complexity Score: {characteristics['complexity_score']}")

        # Store for comparison
        analysis_results.append({
            'name': test_case['name'],
            'characteristics': characteristics
        })

        print()

    # Comparative analysis
    print("=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)

    # Extract metrics for comparison
    char_counts = [r['characteristics']['char_count'] for r in analysis_results]
    complexity_scores = [r['characteristics']['complexity_score'] for r in analysis_results]
    [r['characteristics']['technical_terms'] for r in analysis_results]
    [r['characteristics']['bullet_points'] for r in analysis_results]

    print("\nMetric Comparison:")
    print(f"{'Test Case':<20} {'Chars':<8} {'Complex':<8} {'Tech':<6} {'Bullets':<8} {'Expected Perf':<12}")
    print("-" * 70)

    for result in analysis_results:
        name = result['name'].split(' (')[0]  # Shorten name
        chars = result['characteristics']['char_count']
        complex_score = result['characteristics']['complexity_score']
        tech = result['characteristics']['technical_terms']
        bullets = result['characteristics']['bullet_points']

        # Predict expected performance based on complexity
        if complex_score < 50:
            expected = "Fast"
        elif complex_score < 100:
            expected = "Medium"
        else:
            expected = "Slow"

        print(f"{name:<20} {chars:<8} {complex_score:<8} {tech:<6} {bullets:<8} {expected:<12}")

    # Identify anomalies
    print("\n" + "=" * 80)
    print("ANOMALY DETECTION")
    print("=" * 80)

    print("\nPotential Performance Issues:")

    # Check if Medium JD has unexpected characteristics
    medium_idx = 1  # Medium JD is second in the list
    medium_result = analysis_results[medium_idx]
    small_result = analysis_results[0]
    large_result = analysis_results[2]

    medium_chars = medium_result['characteristics']

    issues_found = []

    # Check for structural complexity
    if medium_chars['bullet_points'] > small_result['characteristics']['bullet_points'] + large_result['characteristics']['bullet_points']:
        issues_found.append(f"❌ Medium JD has unusually high bullet points: {medium_chars['bullet_points']}")

    # Check for line breaks and formatting
    if medium_chars['line_count'] > medium_chars['char_count'] / 50:  # Threshold for line density
        issues_found.append(f"❌ Medium JD has high line density: {medium_chars['line_count']} lines for {medium_chars['char_count']} chars")

    # Check for special characters
    special_ratio = medium_chars['special_chars'] / medium_chars['char_count']
    if special_ratio > 0.1:  # More than 10% special characters
        issues_found.append(f"❌ Medium JD has high special character ratio: {special_ratio:.2%}")

    # Check complexity vs size mismatch
    complexity_per_char = medium_chars['complexity_score'] / medium_chars['char_count']
    small_complexity_per_char = small_result['characteristics']['complexity_score'] / small_result['characteristics']['char_count']
    large_complexity_per_char = large_result['characteristics']['complexity_score'] / large_result['characteristics']['char_count']

    if complexity_per_char > max(small_complexity_per_char, large_complexity_per_char) * 1.5:
        issues_found.append(f"❌ Medium JD has disproportionally high complexity density: {complexity_per_char:.4f}")

    if issues_found:
        for issue in issues_found:
            print(issue)
    else:
        print("✅ No obvious structural anomalies found in Medium JD")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS FOR INVESTIGATION")
    print("=" * 80)

    print("\n1. TEST METHODOLOGY ISSUES TO CHECK:")
    print("   - Timing measurement precision and consistency")
    print("   - Request ordering effects (is Medium always tested second?)")
    print("   - Caching or warm-up effects between requests")
    print("   - Statistical variance and sample size")

    print("\n2. API PROCESSING ISSUES TO CHECK:")
    print("   - LLM tokenization differences for structured vs unstructured text")
    print("   - Prompt processing complexity for bullet-point format")
    print("   - Model attention patterns on formatted text")
    print("   - Memory allocation patterns for different text structures")

    print("\n3. CONTROLLED EXPERIMENTS TO RUN:")
    print("   - Test same content with different formatting")
    print("   - Test Medium JD content as plain text (remove bullet points)")
    print("   - Test randomized order of test cases")
    print("   - Isolate individual requests without batching")

    # Save analysis results
    with open('test/performance/test_data_analysis.json', 'w') as f:
        json.dump({
            'analysis_timestamp': '2025-08-01',
            'test_cases': analysis_results,
            'anomalies': issues_found,
            'summary': {
                'char_counts': char_counts,
                'complexity_scores': complexity_scores,
                'avg_complexity': statistics.mean(complexity_scores),
                'complexity_variance': statistics.variance(complexity_scores) if len(complexity_scores) > 1 else 0
            }
        }, f, indent=2)

    print("\n📊 Analysis results saved to: test/performance/test_data_analysis.json")

    return analysis_results


if __name__ == "__main__":
    analyze_all_test_cases()
