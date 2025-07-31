#!/usr/bin/env python3
"""
Analyze keyword standardization usage and generate statistics.

Usage:
    python analyze_usage.py                    # Analyze all dictionaries
    python analyze_usage.py --detailed         # Show detailed statistics
    python analyze_usage.py --find "python"    # Find specific keyword
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml


def load_yaml_file(filepath: Path) -> dict:
    """Load and parse a YAML file."""
    try:
        with open(filepath, encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}


def analyze_dictionary(yaml_file: Path) -> dict[str, any]:
    """Analyze a single dictionary file."""
    data = load_yaml_file(yaml_file)

    stats = {
        'filename': yaml_file.name,
        'categories': {},
        'total_entries': 0,
        'unique_standardized': set(),
        'max_variants': ('', 0),  # (standardized_form, count)
        'single_variants': [],    # Standardized forms with only 1 variant
        'popular_targets': Counter(),  # Most common standardized forms
    }

    # Reverse mapping: standardized -> [originals]
    reverse_map = defaultdict(list)

    # Process each category
    for category, mappings in data.items():
        if isinstance(mappings, dict):
            stats['categories'][category] = len(mappings)
            stats['total_entries'] += len(mappings)

            for original, standardized in mappings.items():
                stats['unique_standardized'].add(standardized)
                reverse_map[standardized].append(original)
                stats['popular_targets'][standardized] += 1

    # Find max variants
    for standardized, originals in reverse_map.items():
        if len(originals) > stats['max_variants'][1]:
            stats['max_variants'] = (standardized, len(originals))

        if len(originals) == 1:
            stats['single_variants'].append(standardized)

    stats['unique_standardized'] = len(stats['unique_standardized'])

    return stats


def analyze_patterns(yaml_file: Path) -> dict[str, any]:
    """Analyze patterns file."""
    data = load_yaml_file(yaml_file)

    stats = {
        'filename': yaml_file.name,
        'categories': {},
        'total_patterns': 0,
        'pattern_types': Counter(),
        'complex_patterns': [],  # Patterns with special regex features
    }

    # Process each category
    for category, patterns in data.items():
        if isinstance(patterns, list):
            stats['categories'][category] = len(patterns)
            stats['total_patterns'] += len(patterns)

            for pattern_info in patterns:
                if isinstance(pattern_info, dict):
                    pattern_type = pattern_info.get('type', 'unknown')
                    stats['pattern_types'][pattern_type] += 1

                    # Check pattern complexity
                    pattern_str = pattern_info.get('pattern', '')
                    if any(char in pattern_str for char in ['(', '[', '{', '*', '+', '?']):
                        stats['complex_patterns'].append({
                            'pattern': pattern_str,
                            'description': pattern_info.get('description', '')
                        })

    return stats


def find_keyword(keyword: str, data_dir: Path) -> list[tuple[str, str, str]]:
    """
    Find a keyword across all dictionaries.

    Returns:
        List of (file, original_form, standardized_form) tuples
    """
    results = []
    keyword_lower = keyword.lower()

    # Search in dictionary files
    for yaml_file in ['skills.yaml', 'positions.yaml', 'tools.yaml']:
        filepath = data_dir / yaml_file
        if filepath.exists():
            data = load_yaml_file(filepath)

            for _category, mappings in data.items():
                if isinstance(mappings, dict):
                    for original, standardized in mappings.items():
                        if (keyword_lower in original.lower() or
                            keyword_lower in standardized.lower()):
                            results.append((yaml_file, original, standardized))

    return results


def check_conflicts(data_dir: Path) -> dict[str, list[tuple[str, str, str]]]:
    """
    Check for potential conflicts across dictionaries.

    Returns:
        Dictionary of conflicts: original -> [(file, category, standardized)]
    """
    conflicts = defaultdict(list)

    # Load all mappings
    all_mappings = {}
    for yaml_file in ['skills.yaml', 'positions.yaml', 'tools.yaml']:
        filepath = data_dir / yaml_file
        if filepath.exists():
            data = load_yaml_file(filepath)

            for category, mappings in data.items():
                if isinstance(mappings, dict):
                    for original, standardized in mappings.items():
                        if original in all_mappings:
                            # Potential conflict
                            if all_mappings[original][2] != standardized:
                                conflicts[original].append(all_mappings[original])
                                conflicts[original].append((yaml_file, category, standardized))
                        else:
                            all_mappings[original] = (yaml_file, category, standardized)

    return dict(conflicts)


def generate_summary_report(stats_list: list[dict], conflicts: dict, detailed: bool) -> None:
    """Generate and print summary report."""
    print("\n" + "=" * 70)
    print("KEYWORD STANDARDIZATION ANALYSIS REPORT")
    print("=" * 70 + "\n")

    # Overall statistics
    total_entries = sum(s.get('total_entries', 0) for s in stats_list)
    total_unique = sum(s.get('unique_standardized', 0) for s in stats_list)

    print("📊 Overall Statistics:")
    print(f"   Total mappings: {total_entries}")
    print(f"   Unique standardized forms: {total_unique}")
    print(f"   Average variants per form: {total_entries / total_unique if total_unique else 0:.2f}")

    # File-by-file summary
    print("\n📁 File Summary:")
    print("-" * 70)
    print(f"{'File':<20} {'Entries':<10} {'Categories':<12} {'Unique Forms':<15}")
    print("-" * 70)

    for stats in stats_list:
        if 'total_entries' in stats:  # Dictionary file
            print(f"{stats['filename']:<20} "
                  f"{stats['total_entries']:<10} "
                  f"{len(stats['categories']):<12} "
                  f"{stats['unique_standardized']:<15}")
        else:  # Pattern file
            print(f"{stats['filename']:<20} "
                  f"{stats['total_patterns']:<10} "
                  f"{len(stats['categories']):<12} "
                  f"(patterns)")

    # Most mapped terms
    print("\n🎯 Top 10 Most Mapped Terms:")
    all_targets = Counter()
    for stats in stats_list:
        if 'popular_targets' in stats:
            all_targets.update(stats['popular_targets'])

    for term, count in all_targets.most_common(10):
        print(f"   {term:<30} → {count} variants")

    # Pattern statistics
    for stats in stats_list:
        if 'pattern_types' in stats:
            print("\n🔧 Pattern Statistics:")
            for ptype, count in stats['pattern_types'].most_common():
                print(f"   {ptype:<25} : {count} patterns")

    # Conflicts
    if conflicts:
        print(f"\n⚠️  Potential Conflicts Found: {len(conflicts)}")
        if detailed:
            for original, mappings in list(conflicts.items())[:5]:
                print(f"\n   '{original}' maps to:")
                for file, category, standardized in mappings:
                    print(f"      → '{standardized}' in {file}/{category}")
            if len(conflicts) > 5:
                print(f"\n   ... and {len(conflicts) - 5} more conflicts")
    else:
        print("\n✅ No conflicts found across dictionaries")

    # Detailed category breakdown
    if detailed:
        print("\n📂 Detailed Category Breakdown:")
        for stats in stats_list:
            if stats.get('categories'):
                print(f"\n   {stats['filename']}:")
                for category, count in sorted(stats['categories'].items(),
                                            key=lambda x: x[1], reverse=True):
                    print(f"      {category:<30} : {count} entries")

        # Single-variant mappings
        print("\n🔍 Potential Redundant Mappings:")
        redundant_count = 0
        for stats in stats_list:
            if 'single_variants' in stats:
                redundant_count += len(stats['single_variants'])

        print(f"   Found {redundant_count} standardized forms with only 1 variant")
        print("   (These might be unnecessary if original = standardized)")

    print("\n" + "=" * 70)


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description='Analyze keyword standardization usage'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed statistics'
    )
    parser.add_argument(
        '--find',
        type=str,
        help='Find specific keyword across all dictionaries'
    )

    args = parser.parse_args()

    # Setup paths
    data_dir = Path(__file__).parent

    # If finding specific keyword
    if args.find:
        print(f"\n🔍 Searching for '{args.find}'...")
        results = find_keyword(args.find, data_dir)

        if results:
            print(f"\nFound {len(results)} matches:")
            print("-" * 70)
            print(f"{'File':<20} {'Original':<25} {'Standardized':<25}")
            print("-" * 70)
            for file, original, standardized in results:
                print(f"{file:<20} {original:<25} → {standardized:<25}")
        else:
            print(f"No matches found for '{args.find}'")

        return 0

    # Analyze all files
    print("Analyzing standardization dictionaries...")

    stats_list = []

    # Analyze dictionary files
    for filename in ['skills.yaml', 'positions.yaml', 'tools.yaml']:
        filepath = data_dir / filename
        if filepath.exists():
            print(f"  ✓ Analyzing {filename}...")
            stats = analyze_dictionary(filepath)
            stats_list.append(stats)

    # Analyze patterns file
    patterns_file = data_dir / 'patterns.yaml'
    if patterns_file.exists():
        print("  ✓ Analyzing patterns.yaml...")
        stats = analyze_patterns(patterns_file)
        stats_list.append(stats)

    # Check for conflicts
    print("  ✓ Checking for conflicts...")
    conflicts = check_conflicts(data_dir)

    # Generate report
    generate_summary_report(stats_list, conflicts, args.detailed)

    return 0


if __name__ == "__main__":
    sys.exit(main())
