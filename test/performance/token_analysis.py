#!/usr/bin/env python3
"""
Token analysis for different text formats to understand LLM processing complexity.
This tool analyzes how different text structures affect tokenization.
"""

import json
from typing import Any

import tiktoken


def analyze_tokenization(text: str, model_name: str = "gpt-4") -> dict[str, Any]:
    """Analyze tokenization characteristics of text."""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # Fallback to cl100k_base for GPT-4 family
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text)
    token_strings = [encoding.decode([token]) for token in tokens]

    # Count different types of tokens
    formatting_tokens = sum(1 for t in token_strings if t in ['-', '\n', '•', '*', ':', ';'])
    whitespace_tokens = sum(1 for t in token_strings if t.isspace())
    punctuation_tokens = sum(1 for t in token_strings if not t.isalnum() and not t.isspace())
    word_tokens = sum(1 for t in token_strings if any(c.isalnum() for c in t))

    return {
        "total_tokens": len(tokens),
        "characters": len(text),
        "chars_per_token": len(text) / len(tokens) if tokens else 0,
        "formatting_tokens": formatting_tokens,
        "whitespace_tokens": whitespace_tokens,
        "punctuation_tokens": punctuation_tokens,
        "word_tokens": word_tokens,
        "formatting_ratio": formatting_tokens / len(tokens) if tokens else 0,
        "token_strings": token_strings[:20],  # First 20 tokens for inspection
        "tokens": tokens[:20]  # First 20 token IDs
    }


def compare_formatting_variants():
    """Compare different formatting variants of the Medium JD."""

    # Original Medium JD
    original_medium = """We are seeking an experienced Full Stack Developer to join our growing team. The ideal candidate will have:  # noqa: E501
- 5+ years of experience with Python, FastAPI, and Django
- Strong proficiency in React, TypeScript, and modern JavaScript
- Experience with microservices architecture and RESTful APIs
- Hands-on experience with Docker, Kubernetes, and CI/CD pipelines
- Familiarity with AWS or Azure cloud services
- Knowledge of PostgreSQL, MongoDB, and Redis
- Experience with Agile methodologies and version control (Git)
- Excellent communication and problem-solving skills"""

    # Create variants
    variants = {
        "Original (with bullets)": original_medium,

        "Plain text (commas)": original_medium.replace('\n- ', ', ').replace('\n', ' '),

        "Single line": ' '.join(original_medium.split()),

        "No dashes": original_medium.replace('- ', ''),

        "Semicolon separated": original_medium.replace('\n- ', '; ').replace('\n', ' '),

        "Numbers instead": original_medium.replace('- ', '1. '),

        "Minimal formatting": """We are seeking an experienced Full Stack Developer to join our growing team. The ideal candidate will have 5+ years of experience with Python, FastAPI, and Django, strong proficiency in React, TypeScript, and modern JavaScript, experience with microservices architecture and RESTful APIs, hands-on experience with Docker, Kubernetes, and CI/CD pipelines, familiarity with AWS or Azure cloud services, knowledge of PostgreSQL, MongoDB, and Redis, experience with Agile methodologies and version control (Git), and excellent communication and problem-solving skills."""
    }

    print("=" * 80)
    print("TOKEN ANALYSIS FOR DIFFERENT TEXT FORMATS")
    print("=" * 80)
    print("Analyzing how different formatting affects tokenization complexity...\n")

    results = {}

    for variant_name, text in variants.items():
        print(f"Analyzing: {variant_name}")
        print("-" * 50)

        analysis = analyze_tokenization(text)
        results[variant_name] = analysis

        print(f"Text length: {analysis['characters']} characters")
        print(f"Total tokens: {analysis['total_tokens']}")
        print(f"Chars per token: {analysis['chars_per_token']:.2f}")
        print(f"Formatting tokens: {analysis['formatting_tokens']} ({analysis['formatting_ratio']:.1%})")
        print(f"Word tokens: {analysis['word_tokens']}")
        print(f"Punctuation tokens: {analysis['punctuation_tokens']}")

        # Show first few tokens for inspection
        print(f"First 10 tokens: {analysis['token_strings'][:10]}")
        print()

    # Comparative analysis
    print("=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)

    print(f"{'Variant':<25} {'Tokens':<8} {'C/T':<6} {'Fmt%':<6} {'Complexity':<10}")
    print("-" * 70)

    for variant_name, analysis in results.items():
        tokens = analysis['total_tokens']
        chars_per_token = analysis['chars_per_token']
        fmt_ratio = analysis['formatting_ratio']

        # Calculate complexity score
        complexity = tokens * (1 + fmt_ratio * 2)  # Higher weight for formatting tokens

        variant_short = variant_name[:24]
        print(f"{variant_short:<25} {tokens:<8} {chars_per_token:<6.2f} {fmt_ratio:<6.1%} {complexity:<10.1f}")

    # Predictions
    print("\n" + "=" * 80)
    print("PERFORMANCE PREDICTIONS")
    print("=" * 80)

    print("Based on token analysis, expected performance ranking (fastest to slowest):")

    # Sort by complexity score
    complexity_scores = [(name, analysis['total_tokens'] * (1 + analysis['formatting_ratio'] * 2))
                        for name, analysis in results.items()]
    complexity_scores.sort(key=lambda x: x[1])

    for i, (variant_name, score) in enumerate(complexity_scores, 1):
        print(f"{i}. {variant_name} (complexity: {score:.1f})")

    # Hypothesis testing
    print("\n" + "=" * 80)
    print("HYPOTHESIS VALIDATION")
    print("=" * 80)

    original_analysis = results["Original (with bullets)"]
    plain_analysis = results["Plain text (commas)"]
    minimal_analysis = results["Minimal formatting"]

    print("Testing hypothesis: 'Bullet points cause processing overhead'")
    print()

    original_complexity = original_analysis['total_tokens'] * (1 + original_analysis['formatting_ratio'] * 2)
    plain_complexity = plain_analysis['total_tokens'] * (1 + plain_analysis['formatting_ratio'] * 2)
    minimal_complexity = minimal_analysis['total_tokens'] * (1 + minimal_analysis['formatting_ratio'] * 2)

    print(f"Original (bullets): {original_complexity:.1f} complexity")
    print(f"Plain text: {plain_complexity:.1f} complexity")
    print(f"Minimal format: {minimal_complexity:.1f} complexity")

    if original_complexity > plain_complexity * 1.1:
        print("\n✅ HYPOTHESIS SUPPORTED: Bullet formatting adds significant complexity")
        reduction = ((original_complexity - plain_complexity) / original_complexity) * 100
        print(f"   Expected performance improvement: {reduction:.1f}% by removing bullets")
    elif original_complexity > minimal_complexity * 1.1:
        print("\n⚠️  HYPOTHESIS PARTIALLY SUPPORTED: Some formatting impact detected")
    else:
        print("\n❌ HYPOTHESIS NOT SUPPORTED: Formatting has minimal token impact")
        print("   Root cause may be elsewhere (prompt processing, model attention, etc.)")

    # Save results
    with open('test/performance/token_analysis_results.json', 'w') as f:
        json.dump({
            'analysis_results': results,
            'complexity_ranking': complexity_scores,
            'hypothesis_test': {
                'original_complexity': original_complexity,
                'plain_complexity': plain_complexity,
                'minimal_complexity': minimal_complexity,
                'formatting_overhead_percent': ((original_complexity - plain_complexity) / original_complexity) * 100 if original_complexity > 0 else 0
            }
        }, f, indent=2)

    print("\n📊 Token analysis results saved to: test/performance/token_analysis_results.json")

    return results


def analyze_all_test_cases():
    """Analyze tokenization for all original test cases."""

    test_cases = [
        {
            "name": "Small JD",
            "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and Django. Must have strong knowledge of microservices architecture, Docker, Kubernetes, and AWS cloud services. Excellent problem-solving skills required."
        },
        {
            "name": "Medium JD",
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
            "name": "Large JD",
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

    print("\n" + "=" * 80)
    print("TOKEN ANALYSIS FOR ALL TEST CASES")
    print("=" * 80)

    for test_case in test_cases:
        print(f"\nAnalyzing: {test_case['name']}")
        print("-" * 40)

        analysis = analyze_tokenization(test_case['job_description'])

        print(f"Characters: {analysis['characters']}")
        print(f"Tokens: {analysis['total_tokens']}")
        print(f"Chars/Token: {analysis['chars_per_token']:.2f}")
        print(f"Formatting ratio: {analysis['formatting_ratio']:.1%}")
        print(f"Complexity score: {analysis['total_tokens'] * (1 + analysis['formatting_ratio'] * 2):.1f}")


if __name__ == "__main__":
    print("🔍 TOKEN ANALYSIS FOR PERFORMANCE INVESTIGATION")
    print("📊 Analyzing how text formatting affects LLM tokenization")

    # Analyze formatting variants
    compare_formatting_variants()

    # Analyze original test cases
    analyze_all_test_cases()

    print("\n✅ Token analysis complete!")
    print("📋 Use results to validate formatting hypothesis and guide optimization")
