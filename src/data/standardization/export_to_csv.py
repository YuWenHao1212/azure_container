#!/usr/bin/env python3
"""
Export standardization dictionaries to CSV format for easy editing in Excel.

Usage:
    python export_to_csv.py                     # Export all dictionaries
    python export_to_csv.py --file skills.yaml  # Export specific file
    python export_to_csv.py --output my_export  # Custom output directory
"""

import argparse
import csv
import sys
from datetime import datetime
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


def export_dictionary_to_csv(yaml_file: Path, output_dir: Path) -> tuple[bool, str]:
    """
    Export a single dictionary YAML file to CSV.
    
    Returns:
        Tuple of (success, message)
    """
    # Load YAML data
    data = load_yaml_file(yaml_file)
    if not data:
        return False, f"Failed to load {yaml_file}"
    
    # Prepare CSV filename
    base_name = yaml_file.stem
    csv_filename = output_dir / f"{base_name}.csv"
    
    # Extract all mappings
    rows = []
    for category, mappings in data.items():
        if isinstance(mappings, dict):
            for original, standardized in mappings.items():
                rows.append({
                    'Category': category,
                    'Original': original,
                    'Standardized': standardized,
                    'Notes': ''  # Empty field for user notes
                })
    
    # Write to CSV
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['Category', 'Original', 'Standardized', 'Notes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(rows)
        
        return True, f"Exported {len(rows)} entries to {csv_filename}"
    
    except Exception as e:
        return False, f"Error writing CSV: {e}"


def export_patterns_to_csv(yaml_file: Path, output_dir: Path) -> tuple[bool, str]:
    """
    Export patterns YAML file to CSV with special handling.
    
    Returns:
        Tuple of (success, message)
    """
    # Load YAML data
    data = load_yaml_file(yaml_file)
    if not data:
        return False, f"Failed to load {yaml_file}"
    
    # Prepare CSV filename
    csv_filename = output_dir / "patterns.csv"
    
    # Extract all patterns
    rows = []
    for category, patterns in data.items():
        if isinstance(patterns, list):
            for pattern_info in patterns:
                if isinstance(pattern_info, dict):
                    rows.append({
                        'Category': category,
                        'Pattern': pattern_info.get('pattern', ''),
                        'Replacement': pattern_info.get('replacement', ''),
                        'Type': pattern_info.get('type', ''),
                        'Description': pattern_info.get('description', ''),
                        'Notes': ''  # Empty field for user notes
                    })
    
    # Write to CSV
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['Category', 'Pattern', 'Replacement', 'Type', 'Description', 'Notes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(rows)
        
        return True, f"Exported {len(rows)} patterns to {csv_filename}"
    
    except Exception as e:
        return False, f"Error writing CSV: {e}"


def create_summary_file(output_dir: Path, results: list[tuple[str, bool, str]]) -> None:
    """Create a summary file with export information."""
    summary_file = output_dir / "export_summary.txt"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("Keyword Standardization Dictionary Export Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Output Directory: {output_dir}\n\n")
        
        f.write("Export Results:\n")
        f.write("-" * 30 + "\n")
        
        success_count = 0
        for filename, success, message in results:
            status = "✓" if success else "✗"
            f.write(f"{status} {filename}: {message}\n")
            if success:
                success_count += 1
        
        f.write(f"\nTotal: {success_count}/{len(results)} files exported successfully\n")
        
        # Add instructions
        f.write("\n" + "=" * 50 + "\n")
        f.write("Instructions for Editing:\n")
        f.write("-" * 30 + "\n")
        f.write("1. Open CSV files in Excel or Google Sheets\n")
        f.write("2. Edit the 'Standardized' column to update mappings\n")
        f.write("3. Add new rows at the bottom with appropriate Category\n")
        f.write("4. Use the 'Notes' column for comments (will be ignored on import)\n")
        f.write("5. DO NOT modify the 'Original' column for existing entries\n")
        f.write("6. DO NOT change column headers\n")
        f.write("\nTo import changes back:\n")
        f.write("   python import_from_csv.py --input <this_directory>\n")


def main():
    """Main function to handle command line arguments and orchestrate export."""
    parser = argparse.ArgumentParser(
        description='Export standardization dictionaries to CSV format'
    )
    parser.add_argument(
        '--file', 
        type=str, 
        help='Export specific YAML file only'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default='csv_export',
        help='Output directory name (default: csv_export)'
    )
    
    args = parser.parse_args()
    
    # Setup paths
    script_dir = Path(__file__).parent
    output_dir = script_dir / args.output
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = output_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Exporting to: {output_dir}")
    print("-" * 50)
    
    results = []
    
    if args.file:
        # Export specific file
        yaml_file = script_dir / args.file
        if not yaml_file.exists():
            print(f"Error: File {args.file} not found")
            return 1
        
        if args.file == 'patterns.yaml':
            success, message = export_patterns_to_csv(yaml_file, output_dir)
        else:
            success, message = export_dictionary_to_csv(yaml_file, output_dir)
        
        results.append((args.file, success, message))
        print(f"{'✓' if success else '✗'} {message}")
    
    else:
        # Export all files
        files_to_export = [
            ('skills.yaml', False),
            ('positions.yaml', False),
            ('tools.yaml', False),
            ('patterns.yaml', True)  # True indicates special handling
        ]
        
        for filename, is_pattern in files_to_export:
            yaml_file = script_dir / filename
            if yaml_file.exists():
                if is_pattern:
                    success, message = export_patterns_to_csv(yaml_file, output_dir)
                else:
                    success, message = export_dictionary_to_csv(yaml_file, output_dir)
                
                results.append((filename, success, message))
                print(f"{'✓' if success else '✗'} {message}")
            else:
                message = f"File not found: {filename}"
                results.append((filename, False, message))
                print(f"✗ {message}")
    
    # Create summary file
    create_summary_file(output_dir, results)
    print("-" * 50)
    print(f"✓ Export summary saved to: {output_dir / 'export_summary.txt'}")
    
    # Final summary
    success_count = sum(1 for _, success, _ in results if success)
    print(f"\nExport completed: {success_count}/{len(results)} files exported successfully")
    print(f"Output directory: {output_dir}")
    
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())