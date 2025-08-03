#!/usr/bin/env python3
"""
Level 0 Prompt Validation Script
Validates YAML prompt files for the Azure Container API project
No AI credentials required - pure syntax and structure validation
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / "src" / "prompts"
LOGS_DIR = PROJECT_ROOT / "test" / "logs"

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_filename = f"level0_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = LOGS_DIR / log_filename

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class PromptValidator:
    """Validates prompt YAML files for correctness and consistency"""

    # Required fields for each prompt type
    REQUIRED_FIELDS = {
        'root': ['version', 'metadata', 'prompts'],
        'metadata': ['author', 'created_at', 'description', 'status'],
        'prompts': ['system', 'user'],
        'llm_config': []  # Optional but if present, validate its structure
    }

    # Valid status values
    VALID_STATUSES = ['active', 'deprecated', 'testing', 'inactive']

    # Version pattern: v{major}.{minor}.{patch}
    VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')

    # Language codes
    LANGUAGE_CODES = ['en', 'zh-TW']

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.validated_files: int = 0
        self.failed_files: int = 0

    def validate_all_prompts(self) -> bool:
        """Validate all prompt files in the prompts directory"""
        logger.info(f"Starting validation of prompts in: {PROMPTS_DIR}")

        # Find all YAML files
        yaml_files = list(PROMPTS_DIR.rglob("*.yaml")) + list(PROMPTS_DIR.rglob("*.yml"))

        if not yaml_files:
            self.errors.append(f"No YAML files found in {PROMPTS_DIR}")
            return False

        logger.info(f"Found {len(yaml_files)} YAML files to validate")

        # Group files by type
        files_by_type: Dict[str, List[Path]] = {}
        for file_path in yaml_files:
            prompt_type = file_path.parent.name
            if prompt_type not in files_by_type:
                files_by_type[prompt_type] = []
            files_by_type[prompt_type].append(file_path)

        # Validate each type
        all_valid = True
        for prompt_type, files in files_by_type.items():
            logger.info(f"\nValidating {prompt_type} prompts ({len(files)} files)...")

            # Check for duplicate versions within type
            self._check_duplicate_versions(files, prompt_type)

            # Validate each file
            for file_path in files:
                if self._validate_prompt_file(file_path, prompt_type):
                    self.validated_files += 1
                else:
                    self.failed_files += 1
                    all_valid = False

        return all_valid

    def _check_duplicate_versions(self, files: List[Path], prompt_type: str) -> Dict[str, List[Path]]:
        """Check for duplicate versions within a prompt type"""
        versions_map: Dict[str, List[Path]] = {}

        for file_path in files:
            try:
                with open(file_path, encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'version' in data:
                        version = data['version']
                        if version not in versions_map:
                            versions_map[version] = []
                        versions_map[version].append(file_path)
            except Exception:  # noqa: S110
                # Skip files that can't be parsed for this check
                pass

        # Report duplicates
        for version, paths in versions_map.items():
            if len(paths) > 1:
                self.warnings.append(
                    f"Duplicate version {version} found in {prompt_type}: "
                    f"{[str(p.name) for p in paths]}"
                )

        return versions_map

    def _validate_prompt_file(self, file_path: Path, prompt_type: str) -> bool:
        """Validate a single prompt YAML file"""
        relative_path = file_path.relative_to(PROJECT_ROOT)
        logger.info(f"Validating: {relative_path}")

        try:
            # Check file exists and is readable
            if not file_path.exists():
                self.errors.append(f"{relative_path}: File does not exist")
                return False

            # Load YAML
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # Check for empty file
            if not content.strip():
                self.errors.append(f"{relative_path}: File is empty")
                return False

            # Parse YAML
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                self.errors.append(f"{relative_path}: Invalid YAML syntax - {e!s}")
                return False

            if not isinstance(data, dict):
                self.errors.append(f"{relative_path}: Root element must be a dictionary")
                return False

            # Validate structure
            valid = True

            # Check required root fields
            for field in self.REQUIRED_FIELDS['root']:
                if field not in data:
                    self.errors.append(f"{relative_path}: Missing required field '{field}'")
                    valid = False

            # Validate version
            if 'version' in data and not self._validate_version(data['version'], relative_path):
                valid = False

            # Validate metadata
            if 'metadata' in data:
                valid &= self._validate_metadata(data['metadata'], relative_path)

            # Validate prompts
            if 'prompts' in data:
                valid &= self._validate_prompts(data['prompts'], relative_path)

            # Validate llm_config if present
            if 'llm_config' in data:
                valid &= self._validate_llm_config(data['llm_config'], relative_path)

            # Check language variant consistency
            valid &= self._validate_language_variant(file_path, data)

            # Validate multi_round_config if present
            if 'multi_round_config' in data:
                valid &= self._validate_multi_round_config(data['multi_round_config'], relative_path)

            if valid:
                self.info.append(f"{relative_path}: Validation passed ✓")

            return valid

        except Exception as e:
            self.errors.append(f"{relative_path}: Unexpected error during validation - {e!s}")
            return False

    def _validate_version(self, version: Any, file_path: Path) -> bool:
        """Validate version format"""
        if not isinstance(version, str):
            self.errors.append(f"{file_path}: Version must be a string, got {type(version).__name__}")
            return False

        if not self.VERSION_PATTERN.match(version):
            self.errors.append(f"{file_path}: Invalid version format '{version}', expected 'X.Y.Z'")
            return False

        return True

    def _validate_metadata(self, metadata: Any, file_path: Path) -> bool:
        """Validate metadata section"""
        if not isinstance(metadata, dict):
            self.errors.append(f"{file_path}: Metadata must be a dictionary")
            return False

        valid = True
        for field in self.REQUIRED_FIELDS['metadata']:
            if field not in metadata:
                self.errors.append(f"{file_path}: Missing metadata field '{field}'")
                valid = False

        # Validate status
        if 'status' in metadata and metadata['status'] not in self.VALID_STATUSES:
            self.errors.append(
                f"{file_path}: Invalid status '{metadata['status']}', "
                f"must be one of {self.VALID_STATUSES}"
            )
            valid = False

        # Validate created_at format
        if 'created_at' in metadata:
            try:
                datetime.fromisoformat(metadata['created_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.warnings.append(
                    f"{file_path}: Invalid created_at format '{metadata['created_at']}', "
                    f"expected ISO format (e.g., 2025-01-08T00:00:00Z)"
                )

        return valid

    def _validate_prompts(self, prompts: Any, file_path: Path) -> bool:
        """Validate prompts section"""
        if not isinstance(prompts, dict):
            self.errors.append(f"{file_path}: Prompts must be a dictionary")
            return False

        valid = True
        for field in self.REQUIRED_FIELDS['prompts']:
            if field not in prompts:
                self.errors.append(f"{file_path}: Missing prompt field '{field}'")
                valid = False
            elif not isinstance(prompts[field], str):
                self.errors.append(f"{file_path}: Prompt field '{field}' must be a string")
                valid = False
            elif not prompts[field].strip():
                self.errors.append(f"{file_path}: Prompt field '{field}' cannot be empty")
                valid = False

        # Check for template variables in user prompt
        if 'user' in prompts and isinstance(prompts['user'], str):
            # Find all template variables
            template_vars = re.findall(r'\{(\w+)\}', prompts['user'])
            if template_vars:
                self.info.append(f"{file_path}: Found template variables: {template_vars}")

        return valid

    def _validate_llm_config(self, llm_config: Any, file_path: Path) -> bool:
        """Validate LLM configuration"""
        if not isinstance(llm_config, dict):
            self.errors.append(f"{file_path}: llm_config must be a dictionary")
            return False

        valid = True

        # Validate common LLM parameters
        numeric_params = ['temperature', 'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty']
        for param in numeric_params:
            if param in llm_config:
                value = llm_config[param]
                if not isinstance(value, (int, float)):
                    self.errors.append(f"{file_path}: llm_config.{param} must be numeric, got {type(value).__name__}")
                    valid = False
                elif param == 'temperature' and not (0 <= value <= 2):
                    self.warnings.append(f"{file_path}: llm_config.temperature={value} is outside typical range [0, 2]")
                elif param in ['top_p', 'frequency_penalty', 'presence_penalty'] and not (-2 <= value <= 2):
                    self.warnings.append(f"{file_path}: llm_config.{param}={value} is outside typical range [-2, 2]")

        # Validate seed if present
        if 'seed' in llm_config and not isinstance(llm_config['seed'], int):
            self.errors.append(f"{file_path}: llm_config.seed must be an integer")
            valid = False

        return valid

    def _validate_language_variant(self, file_path: Path, data: Dict) -> bool:
        """Validate language variant consistency"""
        filename = file_path.name

        # Extract language code from filename (e.g., v1.0.0-en.yaml)
        lang_match = re.search(r'-(' + '|'.join(self.LANGUAGE_CODES) + r')\.ya?ml$', filename)

        if lang_match:
            file_lang = lang_match.group(1)
            # Check if prompts contain the expected language
            if 'prompts' in data:
                system_prompt = data['prompts'].get('system', '')
                user_prompt = data['prompts'].get('user', '')

                # Simple heuristic: Chinese prompts should contain Chinese characters
                if file_lang == 'zh-TW':
                    chinese_chars = re.findall(r'[\u4e00-\u9fff]', system_prompt + user_prompt)
                    if not chinese_chars:
                        self.warnings.append(
                            f"{file_path.relative_to(PROJECT_ROOT)}: File marked as zh-TW but contains no Chinese characters"  # noqa: E501
                        )
                elif file_lang == 'en':
                    # Check for unexpected Chinese characters in English prompts
                    chinese_chars = re.findall(r'[\u4e00-\u9fff]', system_prompt + user_prompt)
                    if chinese_chars:
                        self.warnings.append(
                            f"{file_path.relative_to(PROJECT_ROOT)}: File marked as en but contains Chinese characters"
                        )

        return True

    def _validate_multi_round_config(self, config: Any, file_path: Path) -> bool:
        """Validate multi-round configuration"""
        if not isinstance(config, dict):
            self.errors.append(f"{file_path}: multi_round_config must be a dictionary")
            return False

        valid = True

        # Check enabled flag
        if 'enabled' in config and not isinstance(config['enabled'], bool):
            self.errors.append(f"{file_path}: multi_round_config.enabled must be a boolean")
            valid = False

        # Check numeric parameters
        numeric_params = ['round1_seed', 'round2_seed', 'min_intersection', 'max_keywords_per_round']
        for param in numeric_params:
            if param in config and not isinstance(config[param], (int, float)):
                self.errors.append(f"{file_path}: multi_round_config.{param} must be numeric")
                valid = False

        return valid

    def print_summary(self):
        """Print validation summary"""
        logger.info("\n" + "="*80)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*80)

        logger.info(f"\nFiles validated: {self.validated_files}")
        logger.info(f"Files failed: {self.failed_files}")

        if self.errors:
            logger.error(f"\nERRORS ({len(self.errors)}):")
            for error in self.errors:
                logger.error(f"  ❌ {error}")

        if self.warnings:
            logger.warning(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"  ⚠️  {warning}")

        if self.info:
            logger.info(f"\nINFO ({len(self.info)}):")
            for info in self.info:
                logger.info(f"  ℹ️  {info}")

        if not self.errors:
            logger.info("\n✅ All prompt files passed validation!")
        else:
            logger.error("\n❌ Validation failed with errors!")

        logger.info(f"\nLog file: {log_path}")


def validate_json_files():
    """Also validate any JSON prompt files"""
    json_files = list(PROMPTS_DIR.rglob("*.json"))

    if not json_files:
        logger.info("No JSON prompt files found")
        return True

    logger.info(f"\nValidating {len(json_files)} JSON files...")

    all_valid = True
    for file_path in json_files:
        relative_path = file_path.relative_to(PROJECT_ROOT)
        try:
            with open(file_path, encoding='utf-8') as f:
                json.load(f)
            logger.info(f"  ✓ {relative_path}: Valid JSON")
        except json.JSONDecodeError as e:
            logger.error(f"  ✗ {relative_path}: Invalid JSON - {e!s}")
            all_valid = False
        except Exception as e:
            logger.error(f"  ✗ {relative_path}: Error reading file - {e!s}")
            all_valid = False

    return all_valid


def main():
    """Main entry point"""
    logger.info("Azure Container API - Level 0 Prompt Validation")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Prompts directory: {PROMPTS_DIR}")
    logger.info(f"Log file: {log_path}")

    # Validate YAML prompts
    validator = PromptValidator()
    yaml_valid = validator.validate_all_prompts()
    validator.print_summary()

    # Validate JSON prompts
    json_valid = validate_json_files()

    # Exit with appropriate code
    if yaml_valid and json_valid:
        logger.info("\n🎉 All validations passed!")
        sys.exit(0)
    else:
        logger.error("\n💥 Validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
