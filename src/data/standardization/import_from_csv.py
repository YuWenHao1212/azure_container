#!/usr/bin/env python3
"""
Import standardization dictionaries from CSV format back to YAML.

Usage:
    python import_from_csv.py --input csv_export/20250702_100000
    python import_from_csv.py --input my_edits --dry-run
    python import_from_csv.py --input updates --backup
"""

import argparse
import csv
import shutil
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def backup_existing_files(data_dir: Path) -> bool:
    """Create backup of existing YAML files."""
    backup_dir = data_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        backup_dir.mkdir(exist_ok=True)

        for yaml_file in data_dir.glob("*.yaml"):
            shutil.copy2(yaml_file, backup_dir / yaml_file.name)
            print(f"  Backed up {yaml_file.name}")

        print(f"✓ Backup created at: {backup_dir}")
        return True

    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return False


def load_csv_dictionary(csv_file: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """
    Load dictionary data from CSV file.

    Returns:
        Tuple of (category_dict, warnings)
    """
    category_dict = OrderedDict()
    warnings = []
    row_count = 0

    try:
        with open(csv_file, encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                row_count += 1

                # Extract fields
                category = row.get('Category', '').strip()
                original = row.get('Original', '').strip()
                standardized = row.get('Standardized', '').strip()

                # Validate row
                if not category:
                    warnings.append(f"Row {row_num}: Missing category")
                    continue

                if not original:
                    warnings.append(f"Row {row_num}: Missing original value")
                    continue

                if not standardized:
                    warnings.append(f"Row {row_num}: Missing standardized value")
                    continue

                # Add to dictionary
                if category not in category_dict:
                    category_dict[category] = OrderedDict()

                # Check for duplicates
                if original in category_dict[category]:
                    warnings.append(
                        f"Row {row_num}: Duplicate key '{original}' in category '{category}'"
                    )

                category_dict[category][original] = standardized

        return category_dict, warnings

    except Exception as e:
        warnings.append(f"Error reading CSV: {e}")
        return {}, warnings


def load_csv_patterns(csv_file: Path) -> tuple[dict[str, list[dict]], list[str]]:
    """
    Load pattern data from CSV file.

    Returns:
        Tuple of (category_dict, warnings)
    """
    category_dict = OrderedDict()
    warnings = []
    row_count = 0

    try:
        with open(csv_file, encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                row_count += 1

                # Extract fields
                category = row.get('Category', '').strip()
                pattern = row.get('Pattern', '').strip()
                replacement = row.get('Replacement', '').strip()
                pattern_type = row.get('Type', '').strip()
                description = row.get('Description', '').strip()

                # Validate row
                if not category:
                    warnings.append(f"Row {row_num}: Missing category")
                    continue

                if not pattern:
                    warnings.append(f"Row {row_num}: Missing pattern")
                    continue

                # Validate regex
                import re
                try:
                    re.compile(pattern)
                except re.error as e:
                    warnings.append(f"Row {row_num}: Invalid regex pattern: {e}")
                    continue

                # Build pattern entry
                pattern_entry = {
                    'pattern': pattern,
                    'replacement': replacement,
                    'type': pattern_type,
                    'description': description
                }

                # Add to dictionary
                if category not in category_dict:
                    category_dict[category] = []

                category_dict[category].append(pattern_entry)

        return category_dict, warnings

    except Exception as e:
        warnings.append(f"Error reading CSV: {e}")
        return {}, warnings


def validate_import_data(
    new_data: dict[str, Any],
    existing_file: Path
) -> list[str]:
    """
    Validate imported data against existing structure.

    Returns:
        List of validation warnings
    """
    warnings = []

    # Load existing data for comparison
    if existing_file.exists():
        try:
            with open(existing_file, encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or {}
        except:
            existing_data = {}

        # Check for removed categories
        for category in existing_data:
            if category not in new_data:
                warnings.append(f"Category '{category}' exists in YAML but not in CSV")

    return warnings


def write_yaml_file(
    data: dict[str, Any],
    output_file: Path,
    file_type: str = 'dictionary'
) -> bool:
    """Write data to YAML file with proper formatting."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Add header comments
            f.write(f"# Keyword Standardization Dictionary - {output_file.stem.title()}\n")
            f.write(f"# Imported from CSV: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total entries: {sum(len(v) for v in data.values())}\n\n")

            # Write data with proper formatting
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=1000  # Prevent line wrapping
            )

        return True

    except Exception as e:
        print(f"Error writing YAML: {e}")
        return False


def generate_import_report(
    input_dir: Path,
    results: list[tuple[str, bool, str, list[str]]],
    dry_run: bool
) -> None:
    """Generate detailed import report."""
    report_file = input_dir / "import_report.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("CSV Import Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Import Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Input Directory: {input_dir}\n")
        f.write(f"Mode: {'DRY RUN' if dry_run else 'ACTUAL IMPORT'}\n\n")

        f.write("Import Results:\n")
        f.write("-" * 30 + "\n")

        for filename, success, message, warnings in results:
            status = "✓" if success else "✗"
            f.write(f"\n{status} {filename}:\n")
            f.write(f"   {message}\n")

            if warnings:
                f.write("   Warnings:\n")
                for warning in warnings[:10]:  # Limit to first 10
                    f.write(f"   - {warning}\n")
                if len(warnings) > 10:
                    f.write(f"   ... and {len(warnings) - 10} more warnings\n")

        # Summary statistics
        f.write("\n" + "=" * 50 + "\n")
        f.write("Summary:\n")
        success_count = sum(1 for _, success, _, _ in results if success)
        f.write(f"- Files processed: {len(results)}\n")
        f.write(f"- Successful imports: {success_count}\n")
        f.write(f"- Total warnings: {sum(len(w) for _, _, _, w in results)}\n")

        if dry_run:
            f.write("\nThis was a DRY RUN. No files were modified.\n")
            f.write("To perform actual import, run without --dry-run flag.\n")


def main():
    """Main function to handle command line arguments and orchestrate import."""
    parser = argparse.ArgumentParser(
        description='Import standardization dictionaries from CSV format'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input directory containing CSV files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate without making changes'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before importing'
    )

    args = parser.parse_args()

    # Setup paths
    script_dir = Path(__file__).parent
    input_dir = script_dir / args.input

    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' not found")
        return 1

    print(f"Importing from: {input_dir}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'ACTUAL IMPORT'}")
    print("-" * 50)

    # Create backup if requested
    if args.backup and not args.dry_run:
        if not backup_existing_files(script_dir):
            print("Backup failed. Import cancelled.")
            return 1
        print()

    results = []

    # Process each file type
    file_mappings = [
        ('skills.csv', 'skills.yaml', 'dictionary'),
        ('positions.csv', 'positions.yaml', 'dictionary'),
        ('tools.csv', 'tools.yaml', 'dictionary'),
        ('patterns.csv', 'patterns.yaml', 'patterns')
    ]

    for csv_filename, yaml_filename, file_type in file_mappings:
        csv_file = input_dir / csv_filename
        yaml_file = script_dir / yaml_filename

        if not csv_file.exists():
            message = f"CSV file not found: {csv_filename}"
            results.append((csv_filename, False, message, []))
            print(f"✗ {message}")
            continue

        # Load CSV data
        if file_type == 'patterns':
            data, warnings = load_csv_patterns(csv_file)
        else:
            data, warnings = load_csv_dictionary(csv_file)

        if not data:
            message = f"No data loaded from {csv_filename}"
            results.append((csv_filename, False, message, warnings))
            print(f"✗ {message}")
            continue

        # Validate
        validation_warnings = validate_import_data(data, yaml_file)
        warnings.extend(validation_warnings)

        # Count entries
        if file_type == 'patterns':
            entry_count = sum(len(patterns) for patterns in data.values())
        else:
            entry_count = sum(len(mappings) for mappings in data.values())

        # Write or simulate
        if args.dry_run:
            success = True
            message = f"Would import {entry_count} entries from {csv_filename}"
        else:
            success = write_yaml_file(data, yaml_file, file_type)
            if success:
                message = f"Imported {entry_count} entries to {yaml_filename}"
            else:
                message = f"Failed to write {yaml_filename}"

        results.append((csv_filename, success, message, warnings))

        # Print result
        print(f"{'✓' if success else '✗'} {message}")
        if warnings:
            print(f"   ⚠ {len(warnings)} warnings")

    # Generate report
    generate_import_report(input_dir, results, args.dry_run)
    print("-" * 50)
    print(f"✓ Import report saved to: {input_dir / 'import_report.txt'}")

    # Final summary
    success_count = sum(1 for _, success, _, _ in results if success)
    total_warnings = sum(len(w) for _, _, _, w in results)

    print(f"\nImport completed: {success_count}/{len(results)} files processed successfully")
    if total_warnings > 0:
        print(f"⚠ Total warnings: {total_warnings}")

    if args.dry_run:
        print("\nThis was a DRY RUN. No files were modified.")
        print("To perform actual import, run without --dry-run flag.")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
