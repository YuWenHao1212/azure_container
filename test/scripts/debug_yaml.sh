#!/bin/bash

# Debug script to find which YAML file is causing the issue

PROMPTS_DIR="/Users/yuwenhao/Documents/GitHub/azure_container/src/prompts"

echo "Testing YAML files individually..."

for file in $(find "$PROMPTS_DIR" -name "*.yaml" -o -name "*.yml" | sort); do
    echo -n "Testing: $file ... "
    
    python3 -c "
import yaml
import sys
try:
    with open('$file', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    print('OK')
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓"
    else
        echo "✗"
        break
    fi
done