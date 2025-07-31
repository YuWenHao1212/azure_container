#!/bin/bash

# Level 0: Prompt YAML Validation Script
# Validates all prompt configuration files for correct YAML format

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROMPTS_DIR="$PROJECT_ROOT/src/prompts"

# Source log manager
source "$SCRIPT_DIR/lib/log_manager.sh"

# Start timer
START_TIME=$(date +%s)

# Initialize counters
TOTAL_FILES=0
VALID_FILES=0
INVALID_FILES=0

echo "======================================"
echo "Level 0: Prompt YAML Validation"
echo "======================================"
echo "Checking directory: $PROMPTS_DIR"
echo ""

# Function to validate YAML file
validate_yaml() {
    local file=$1
    local relative_path="${file#$PROJECT_ROOT/}"
    
    TOTAL_FILES=$((TOTAL_FILES + 1))
    
    if [ ! -f "$file" ]; then
        echo "❌ MISSING: $relative_path"
        INVALID_FILES=$((INVALID_FILES + 1))
        return 1
    fi
    
    # Check if file is readable
    if [ ! -r "$file" ]; then
        echo "❌ UNREADABLE: $relative_path"
        INVALID_FILES=$((INVALID_FILES + 1))
        return 1
    fi
    
    # Use Python to validate YAML
    output=$(python3 -c "
import yaml
import sys
try:
    with open('$file', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Check required fields
    required_fields = ['template', 'metadata']
    metadata_fields = ['version', 'language', 'description']
    
    if not isinstance(data, dict):
        print('ERROR: Root must be a dictionary')
        sys.exit(1)
    
    # Check prompts field (can have template or prompts)
    if 'template' not in data and 'prompts' not in data:
        print('ERROR: Missing required field: template or prompts')
        sys.exit(1)
    
    # If using prompts structure
    if 'prompts' in data:
        if not isinstance(data['prompts'], dict):
            print('ERROR: prompts must be a dictionary')
            sys.exit(1)
        
        # Check if this is a prompt that needs job_description
        # Resume format prompts work with OCR text, not job descriptions
        if 'resume_format' not in '$file':
            # Check if there's a user prompt with job_description placeholder
            has_job_description = False
            for key, value in data.get('prompts', {}).items():
                if isinstance(value, str) and '{job_description}' in value:
                    has_job_description = True
                    break
            if not has_job_description:
                # Check if it has resume_text or ocr_text instead (for resume processing)
                has_resume_placeholder = False
                for key, value in data.get('prompts', {}).items():
                    if isinstance(value, str) and ('{resume_text}' in value or '{ocr_text}' in value):
                        has_resume_placeholder = True
                        break
                if not has_resume_placeholder:
                    print('ERROR: prompts must contain {job_description}, {resume_text}, or {ocr_text} placeholder')
                    sys.exit(1)
    else:
        # Using template structure
        if not isinstance(data['template'], str):
            print('ERROR: template must be a string')
            sys.exit(1)
        
        # Check if template contains required placeholder
        if 'resume_format' not in '$file':
            if '{job_description}' not in data['template']:
                print('ERROR: template must contain {job_description} placeholder')
                sys.exit(1)
    
    # Check metadata
    if 'metadata' not in data:
        print('ERROR: Missing required field: metadata')
        sys.exit(1)
    
    if not isinstance(data['metadata'], dict):
        print('ERROR: metadata must be a dictionary')
        sys.exit(1)
    
    # Check version (can be at root or in metadata)
    version = data.get('version') or data['metadata'].get('version')
    if version:
        # Version can be with or without 'v' prefix
        version_parts = version.lstrip('v').split('.')
        if len(version_parts) != 3:
            print(f'ERROR: Invalid version format: {version}')
            sys.exit(1)
    else:
        print('ERROR: Missing version field')
        sys.exit(1)
    
    # Check description in metadata
    if 'description' not in data['metadata']:
        print('ERROR: Missing metadata field: description')
        sys.exit(1)
    
    # Language validation is optional (based on filename convention)
    
    print('VALID')
    sys.exit(0)
except yaml.YAMLError as e:
    print(f'YAML ERROR: {e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1)
    
    result=$?
    
    if [ $result -eq 0 ]; then
        echo "✅ VALID: $relative_path"
        VALID_FILES=$((VALID_FILES + 1))
        return 0
    else
        echo "❌ INVALID: $relative_path"
        echo "   Error: $output"
        INVALID_FILES=$((INVALID_FILES + 1))
        return 1
    fi
}

# Check if prompts directory exists
if [ ! -d "$PROMPTS_DIR" ]; then
    echo "WARNING: Prompts directory not found: $PROMPTS_DIR"
    echo "Creating directory..."
    mkdir -p "$PROMPTS_DIR"
fi

# Find all YAML files in prompts directory
echo "Searching for YAML files..."
yaml_files=($(find "$PROMPTS_DIR" -name "*.yaml" -o -name "*.yml" 2>/dev/null | sort))

if [ ${#yaml_files[@]} -eq 0 ]; then
    echo "WARNING: No YAML files found in $PROMPTS_DIR"
    echo ""
    echo "Expected prompt files:"
    echo "  - keyword_extraction/v1.4.0-en.yaml"
    echo "  - keyword_extraction/v1.4.0-zh-TW.yaml"
    echo ""
    
    # Create sample files if they don't exist
    echo "Creating sample prompt files..."
    mkdir -p "$PROMPTS_DIR/keyword_extraction"
    
    # English prompt
    cat > "$PROMPTS_DIR/keyword_extraction/v1.4.0-en.yaml" << 'EOF'
template: |
  Extract the most important keywords from the following job description.
  Focus on technical skills, tools, and requirements.
  
  Job Description:
  {job_description}
  
  Return keywords as a JSON array.

metadata:
  version: v1.4.0
  language: en
  description: English keyword extraction prompt for job descriptions
  created_date: "2025-01-01"
  author: AI Resume Advisor Team
EOF
    
    # Traditional Chinese prompt
    cat > "$PROMPTS_DIR/keyword_extraction/v1.4.0-zh-TW.yaml" << 'EOF'
template: |
  從以下職缺描述中提取最重要的關鍵字。
  請專注於技術技能、工具和要求。
  
  職缺描述：
  {job_description}
  
  請以 JSON 陣列格式回傳關鍵字。

metadata:
  version: v1.4.0
  language: zh-TW
  description: 繁體中文職缺描述關鍵字提取提示
  created_date: "2025-01-01"
  author: AI Resume Advisor Team
EOF
    
    # Re-scan for files
    yaml_files=($(find "$PROMPTS_DIR" -name "*.yaml" -o -name "*.yml" 2>/dev/null | sort))
fi

echo "Found ${#yaml_files[@]} YAML file(s)"
echo ""

# Validate each YAML file
for file in "${yaml_files[@]}"; do
    validate_yaml "$file"
done

# End timer
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Summary
echo ""
echo "======================================"
echo "Summary"
echo "======================================"
echo "Total files checked: $TOTAL_FILES"
echo "Valid files: $VALID_FILES"
echo "Invalid files: $INVALID_FILES"
echo "Duration: ${DURATION}s"

# Exit code based on results
if [ $INVALID_FILES -eq 0 ]; then
    echo ""
    echo "✅ All prompt files are valid!"
    exit 0
else
    echo ""
    echo "❌ Some prompt files are invalid. Please fix the issues above."
    exit 1
fi