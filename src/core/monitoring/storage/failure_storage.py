"""
Failure case storage system for monitoring and analysis.
Stores failed JD samples for debugging and improvement.
"""
import asyncio
import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FailureStorage:
    """
    Storage system for failed extraction cases.
    
    Features:
    - Stores failed JD content (limited to 500 characters)
    - Categorizes failure reasons
    - Maintains rolling window of recent failures
    - Provides analysis capabilities
    """
    
    def __init__(self, storage_path: str | None = None, max_storage_size: int = 100):
        """
        Initialize failure storage.
        
        Args:
            storage_path: Path to store failure files
            max_storage_size: Maximum number of failures to keep in memory
        """
        self.storage_path = Path(storage_path or os.getenv("FAILURE_STORAGE_PATH", "/tmp/failed_cases/"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage with size limit
        self.failures = deque(maxlen=max_storage_size)
        self.failure_categories = {
            "language_detection": deque(maxlen=50),
            "keyword_extraction": deque(maxlen=50),
            "validation_error": deque(maxlen=50),
            "api_error": deque(maxlen=50)
        }
        
        # Statistics
        self.stats = {
            "total_failures": 0,
            "failures_by_category": {},
            "failures_by_language": {},
            "common_failure_patterns": {}
        }
        
        # Load existing failures if any
        self._load_existing_failures()
    
    async def store_failure(
        self,
        category: str,
        job_description: str,
        failure_reason: str,
        language: str | None = None,
        additional_info: dict[str, Any] | None = None
    ) -> str:
        """
        Store a failure case.
        
        Args:
            category: Failure category (e.g., "language_detection", "keyword_extraction")
            job_description: The JD that failed (will be truncated to 500 chars)
            failure_reason: Detailed reason for failure
            language: Detected or expected language
            additional_info: Any additional information
        
        Returns:
            Failure ID for reference
        """
        # Truncate JD to 500 characters
        truncated_jd = job_description[:500] if len(job_description) > 500 else job_description
        
        # Generate failure ID
        failure_id = f"{category}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create failure record
        failure_record = {
            "id": failure_id,
            "category": category,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_description": truncated_jd,
            "job_description_length": len(job_description),
            "failure_reason": failure_reason,
            "language": language,
            "additional_info": additional_info or {}
        }
        
        # Store in memory
        self.failures.append(failure_record)
        
        # Store in category-specific queue
        if category in self.failure_categories:
            self.failure_categories[category].append(failure_record)
        
        # Update statistics
        self._update_statistics(failure_record)
        
        # Persist to disk (async)
        asyncio.create_task(self._persist_failure(failure_record))
        
        return failure_id
    
    async def _persist_failure(self, failure_record: dict[str, Any]):
        """Persist failure to disk."""
        try:
            # Create daily directory
            date_dir = self.storage_path / datetime.now(timezone.utc).strftime("%Y%m%d")
            date_dir.mkdir(exist_ok=True)
            
            # Save failure record
            file_path = date_dir / f"{failure_record['id']}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(failure_record, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Log error but don't fail the main process
            from src.core.monitoring_service import monitoring_service
            monitoring_service.track_error(
                error_type="FailurePersistenceError",
                error_message=str(e),
                endpoint="failure_storage"
            )
    
    def _update_statistics(self, failure_record: dict[str, Any]):
        """Update failure statistics."""
        self.stats["total_failures"] += 1
        
        # Update category statistics
        category = failure_record["category"]
        self.stats["failures_by_category"][category] = \
            self.stats["failures_by_category"].get(category, 0) + 1
        
        # Update language statistics
        if failure_record["language"]:
            lang = failure_record["language"]
            self.stats["failures_by_language"][lang] = \
                self.stats["failures_by_language"].get(lang, 0) + 1
    
    def get_recent_failures(
        self,
        category: str | None = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get recent failure cases.
        
        Args:
            category: Filter by category (optional)
            limit: Maximum number of failures to return
        
        Returns:
            List of recent failure records
        """
        if category and category in self.failure_categories:
            failures = list(self.failure_categories[category])
        else:
            failures = list(self.failures)
        
        # Return most recent first
        return failures[-limit:][::-1]
    
    def get_failure_patterns(self) -> dict[str, Any]:
        """
        Analyze and return common failure patterns.
        
        Returns:
            Dictionary containing pattern analysis
        """
        patterns = {
            "by_category": {},
            "by_language": {},
            "common_reasons": {},
            "time_distribution": {}
        }
        
        # Analyze failures by category
        for category, failures in self.failure_categories.items():
            if failures:
                reasons = {}
                for failure in failures:
                    reason = failure["failure_reason"]
                    reasons[reason] = reasons.get(reason, 0) + 1
                
                patterns["by_category"][category] = {
                    "count": len(failures),
                    "top_reasons": sorted(
                        reasons.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:5]
                }
        
        # Analyze failures by language
        language_failures = {}
        for failure in self.failures:
            if failure["language"]:
                lang = failure["language"]
                if lang not in language_failures:
                    language_failures[lang] = []
                language_failures[lang].append(failure)
        
        for lang, failures in language_failures.items():
            patterns["by_language"][lang] = {
                "count": len(failures),
                "avg_jd_length": sum(f["job_description_length"] for f in failures) / len(failures),
                "categories": {}
            }
            
            # Count by category for this language
            for failure in failures:
                cat = failure["category"]
                patterns["by_language"][lang]["categories"][cat] = \
                    patterns["by_language"][lang]["categories"].get(cat, 0) + 1
        
        return patterns
    
    def clear_old_failures(self, days: int = 7):
        """
        Clear failures older than specified days.
        
        Args:
            days: Number of days to keep
        """
        cutoff_date = datetime.now(timezone.utc).timestamp() - (days * 86400)
        
        # Clear from memory
        self.failures = deque(
            (f for f in self.failures 
             if datetime.fromisoformat(f["timestamp"]).timestamp() > cutoff_date),
            maxlen=self.failures.maxlen
        )
        
        # Clear from disk
        for date_dir in self.storage_path.iterdir():
            if date_dir.is_dir():
                try:
                    dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                    if dir_date.timestamp() < cutoff_date:
                        for file in date_dir.iterdir():
                            file.unlink()
                        date_dir.rmdir()
                except ValueError:
                    # Skip non-date directories
                    pass
    
    def _load_existing_failures(self):
        """Load existing failures from disk on startup."""
        try:
            # Load only recent failures (last 2 days)
            cutoff_date = datetime.now(timezone.utc).timestamp() - (2 * 86400)
            
            for date_dir in sorted(self.storage_path.iterdir(), reverse=True):
                if date_dir.is_dir():
                    try:
                        dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                        if dir_date.timestamp() < cutoff_date:
                            break
                        
                        # Load failures from this directory
                        for file in date_dir.iterdir():
                            if file.suffix == '.json':
                                with open(file, encoding='utf-8') as f:
                                    failure = json.load(f)
                                    self.failures.append(failure)
                                    
                                    # Add to category queue
                                    category = failure.get("category")
                                    if category in self.failure_categories:
                                        self.failure_categories[category].append(failure)
                                    
                                    # Update statistics
                                    self._update_statistics(failure)
                    except (ValueError, json.JSONDecodeError):
                        # Skip invalid files
                        pass
        except Exception as e:
            # Log error but continue initialization
            from src.core.monitoring_service import monitoring_service
            monitoring_service.track_error(
                error_type="FailureLoadError",
                error_message=str(e),
                endpoint="failure_storage"
            )
    
    def export_analysis_report(self) -> dict[str, Any]:
        """
        Export a comprehensive analysis report.
        
        Returns:
            Dictionary containing full analysis
        """
        return {
            "summary": {
                "total_failures": self.stats["total_failures"],
                "failures_by_category": self.stats["failures_by_category"],
                "failures_by_language": self.stats["failures_by_language"]
            },
            "patterns": self.get_failure_patterns(),
            "recent_failures": {
                category: self.get_recent_failures(category, 5)
                for category in self.failure_categories
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Global failure storage instance
failure_storage = FailureStorage()