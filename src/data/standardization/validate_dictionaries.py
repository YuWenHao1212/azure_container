#!/usr/bin/env python3
"""
Validate standardization dictionaries for duplicates, conflicts, and other issues.
"""

import sys
from collections import defaultdict
from pathlib import Path

import yaml


def load_yaml_file(filepath: Path) -> dict:
    """Load and parse a YAML file."""
    try:
        with open(filepath, encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}


def extract_mappings(data: dict) -> dict[str, str]:
    """Extract all mappings from nested YAML structure."""
    mappings = {}
    for _category, items in data.items():
        if isinstance(items, dict):
            for original, standardized in items.items():
                # Store with lowercase key for consistency
                mappings[original.lower()] = standardized
        elif isinstance(items, list):
            # Skip pattern files
            continue
    return mappings


def check_duplicates(all_dicts: dict[str, dict[str, str]]) -> list[str]:
    """Check for duplicate keys across dictionaries."""
    issues = []
    seen_keys = {}

    for dict_name, mappings in all_dicts.items():
        for key, value in mappings.items():
            if key in seen_keys:
                # Only flag as issue if they map to different values
                if seen_keys[key][1] != value:
                    issues.append(
                        f"Duplicate key '{key}' maps to '{seen_keys[key][1]}' in {seen_keys[key][0]} "
                        f"but '{value}' in {dict_name}"
                    )
            else:
                seen_keys[key] = (dict_name, value)

    return issues


def check_conflicts(combined: dict[str, str]) -> list[str]:
    """Check for conflicting standardizations (different keys mapping to same value)."""
    issues = []
    reverse_map = defaultdict(list)

    for original, standardized in combined.items():
        reverse_map[standardized.lower()].append(original)

    for standardized, originals in reverse_map.items():
        # SIM102: Combine nested if statements using 'and'
        if (len(originals) > 1 and
            not all(orig.replace(' ', '').replace('-', '').replace('_', '') ==
                   originals[0].replace(' ', '').replace('-', '').replace('_', '')
                   for orig in originals)):
            # This might be intentional (e.g., multiple variations mapping to same standard)
            # Only flag if they're very different
                issues.append(
                    f"Multiple different terms map to '{standardized}': {', '.join(originals)}"
                )

    return issues


def check_circular_references(combined: dict[str, str]) -> list[str]:
    """Check for circular references (A->B and B->A)."""
    issues = []

    for key, value in combined.items():
        # Check if the standardized value is also a key
        value_lower = value.lower()
        if value_lower in combined and value_lower != key:
            target = combined[value_lower]
            if target.lower() == key:
                issues.append(f"Circular reference: '{key}' -> '{value}' -> '{target}'")

    return issues


def check_self_references(combined: dict[str, str]) -> list[str]:
    """Check for self-references (key maps to itself)."""
    issues = []

    for key, value in combined.items():
        # Only flag if the key and value are exactly the same (case-insensitive)
        # Not if they differ only in case (e.g., "github" -> "GitHub" is OK)
        if key == value.lower() and key == value:
            issues.append(f"Self-reference: '{key}' maps to '{value}'")

    return issues


def get_statistics(all_dicts: dict[str, dict[str, str]]) -> dict[str, int]:
    """Get statistics about the dictionaries."""
    stats = {}
    total = 0

    for dict_name, mappings in all_dicts.items():
        count = len(mappings)
        stats[dict_name] = count
        total += count

    stats['total'] = total
    return stats


def validate_patterns(patterns_file: Path) -> tuple[int, list[str]]:
    """Validate pattern file structure and regex patterns."""
    import re

    data = load_yaml_file(patterns_file)
    pattern_count = 0
    issues = []

    for category, patterns in data.items():
        if isinstance(patterns, list):
            for pattern_info in patterns:
                if isinstance(pattern_info, dict):
                    pattern_count += 1

                    # Check required fields
                    if 'pattern' not in pattern_info:
                        issues.append(f"Pattern in {category} missing 'pattern' field")
                        continue

                    # Validate regex
                    try:
                        re.compile(pattern_info['pattern'])
                    except re.error as e:
                        issues.append(
                            f"Invalid regex in {category}: '{pattern_info['pattern']}' - {e}"
                        )

    return pattern_count, issues


def main():
    """Run validation on all dictionary files."""
    # Get the data directory
    data_dir = Path(__file__).parent

    print("Keyword Standardization Dictionary Validation")
    print("=" * 60)

    # Load all dictionaries
    dict_files = {
        'skills': data_dir / 'skills.yaml',
        'positions': data_dir / 'positions.yaml',
        'tools': data_dir / 'tools.yaml'
    }

    all_dicts = {}
    for name, filepath in dict_files.items():
        if filepath.exists():
            data = load_yaml_file(filepath)
            all_dicts[name] = extract_mappings(data)
            print(f"✓ Loaded {name}.yaml")
        else:
            print(f"✗ Missing {name}.yaml")

    # Combine all dictionaries
    combined = {}
    for mappings in all_dicts.values():
        combined.update(mappings)

    print("\nStatistics:")
    print("-" * 30)
    stats = get_statistics(all_dicts)
    for name, count in stats.items():
        print(f"  {name}: {count} entries")

    # Run validations
    print("\nValidation Results:")
    print("-" * 30)

    all_issues = []

    # Check duplicates
    duplicates = check_duplicates(all_dicts)
    if duplicates:
        print(f"\n❌ Found {len(duplicates)} duplicate keys:")
        for issue in duplicates[:5]:  # Show first 5
            print(f"   - {issue}")
        if len(duplicates) > 5:
            print(f"   ... and {len(duplicates) - 5} more")
        all_issues.extend(duplicates)
    else:
        print("✓ No duplicate keys found")

    # Check conflicts
    conflicts = check_conflicts(combined)
    if conflicts:
        print(f"\n⚠️  Found {len(conflicts)} potential conflicts:")
        for issue in conflicts[:5]:  # Show first 5
            print(f"   - {issue}")
        if len(conflicts) > 5:
            print(f"   ... and {len(conflicts) - 5} more")
        # Conflicts might be intentional, so we don't add to all_issues
    else:
        print("✓ No conflicting mappings found")

    # Check circular references
    circular = check_circular_references(combined)
    if circular:
        print(f"\n❌ Found {len(circular)} circular references:")
        for issue in circular:
            print(f"   - {issue}")
        all_issues.extend(circular)
    else:
        print("✓ No circular references found")

    # Check self-references
    self_refs = check_self_references(combined)
    if self_refs:
        print(f"\n❌ Found {len(self_refs)} self-references:")
        for issue in self_refs:
            print(f"   - {issue}")
        all_issues.extend(self_refs)
    else:
        print("✓ No self-references found")

    # Validate patterns
    patterns_file = data_dir / 'patterns.yaml'
    if patterns_file.exists():
        pattern_count, pattern_issues = validate_patterns(patterns_file)
        print(f"\n✓ Validated {pattern_count} patterns")
        if pattern_issues:
            print(f"❌ Found {len(pattern_issues)} pattern issues:")
            for issue in pattern_issues:
                print(f"   - {issue}")
            all_issues.extend(pattern_issues)

    # Summary
    print("\n" + "=" * 60)
    if all_issues:
        print(f"❌ Validation completed with {len(all_issues)} issues")
        return 1
    else:
        print("✅ All validations passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
