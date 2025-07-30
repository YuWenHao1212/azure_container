"""
Prompt Management API Endpoints.
Provides endpoints for querying prompt versions across different tasks.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from src.core.simple_prompt_manager import prompt_manager
from src.models.response import (
    UnifiedResponse,
    create_error_response,
    create_success_response,
)

# Setup logging
logger = logging.getLogger(__name__)

# Create router for prompt management endpoints
router = APIRouter()


@router.get(
    "/prompts/version",
    response_model=UnifiedResponse,
    summary="Get active prompt version for any task",
    description="Get the currently active prompt version and configuration details for specified task",
    tags=["Prompt Management"]
)
async def get_prompt_version(
    task: str = Query(..., description="Task name (e.g., 'keyword_extraction', 'resume_analysis', etc.)"),
    language: str | None = Query(None, description="Language code (e.g., 'en', 'zh-TW'). If not specified, returns info for all languages.")
) -> UnifiedResponse:
    """
    Get active prompt version information for any task.
    
    This is a generic endpoint that can query prompt versions for any task,
    not just keyword extraction. As new features are added, they can use
    this same endpoint.
    
    Parameters:
    - task: Task name (required)
    - language: Language code (optional)
    
    Returns:
    - Task name
    - Active prompt version details per language
    - Available versions
    - Prompt configuration
    """
    try:
        # If language is specified, get info for that language
        if language:
            from src.services.unified_prompt_service import get_unified_prompt_service
            prompt_service = get_unified_prompt_service()
            
            # Check if this is a valid task by trying to list versions
            available_versions = []
            try:
                # For keyword_extraction, use the unified prompt service
                if task == "keyword_extraction":
                    available_versions = prompt_service.list_versions(language)
                    active_version = prompt_service.get_active_version(language)
                else:
                    # For other tasks, use the simple prompt manager
                    available_versions = prompt_manager.list_versions(task)
                    active_version = prompt_manager.get_active_version(task)
                    
                # If no versions found, task doesn't exist
                if not available_versions:
                    raise ValueError(f"Task '{task}' not found")
            except Exception as e:
                logger.warning(f"Task '{task}' not found or error listing versions: {e}")
                raise ValueError(f"Task '{task}' not found")
            
            # Get prompt config for active version if exists
            prompt_info = {}
            if active_version and task == "keyword_extraction":
                try:
                    config = prompt_service.get_prompt_config(language, active_version)
                    prompt_info = {
                        "version": config.version,
                        "status": config.metadata.status,
                        "author": config.metadata.author,
                        "description": config.metadata.description,
                        "created_at": config.metadata.created_at,
                        "llm_config": {
                            "temperature": config.llm_config.temperature,
                            "max_tokens": config.llm_config.max_tokens,
                            "seed": getattr(config.llm_config, 'seed', None),
                            "top_p": getattr(config.llm_config, 'top_p', None)
                        }
                    }
                except Exception as e:
                    logger.warning(f"Failed to load prompt config: {e}")
            
            response_data = {
                "task": task,
                "language": language,
                "active_version": active_version,
                "available_versions": available_versions,
                "prompt_info": prompt_info,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # No language specified - return info for all supported languages
            response_data = {
                "task": task,
                "languages": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # For keyword_extraction, check multiple languages
            if task == "keyword_extraction":
                from src.services.unified_prompt_service import (
                    get_unified_prompt_service,
                )
                prompt_service = get_unified_prompt_service()
                
                for lang in ["en", "zh-TW"]:
                    try:
                        active_version = prompt_service.get_active_version(lang)
                        available_versions = prompt_service.list_versions(lang)
                        response_data["languages"][lang] = {
                            "active_version": active_version,
                            "available_versions": available_versions
                        }
                    except Exception as e:
                        logger.warning(f"Error getting versions for {lang}: {e}")
            else:
                # For other tasks, just list versions without language
                try:
                    available_versions = prompt_manager.list_versions(task)
                    active_version = prompt_manager.get_active_version(task)
                    response_data["active_version"] = active_version
                    response_data["available_versions"] = available_versions
                except Exception:
                    raise ValueError(f"Task '{task}' not found")
        
        logger.info(f"Retrieved prompt version info for task={task}")
        return create_success_response(response_data)
        
    except ValueError as e:
        logger.warning(f"Invalid request: {str(e)}")
        error_response = create_error_response(
            code="INVALID_TASK",
            message="無效的任務名稱",
            details=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"Failed to get prompt version: {str(e)}")
        error_response = create_error_response(
            code="PROMPT_VERSION_ERROR",
            message="無法取得提示版本資訊",
            details=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.dict()
        )


@router.get(
    "/prompts/tasks",
    response_model=UnifiedResponse,
    summary="List all available tasks with prompts",
    description="Get a list of all tasks that have prompt configurations",
    tags=["Prompt Management"]
)
async def list_prompt_tasks() -> UnifiedResponse:
    """
    List all available tasks that have prompt configurations.
    
    Returns:
    - List of task names
    - Brief info about each task
    """
    try:
        # Get all subdirectories in prompts directory
        prompts_dir = prompt_manager.prompts_dir
        tasks = []
        
        if prompts_dir.exists():
            for task_dir in prompts_dir.iterdir():
                if task_dir.is_dir() and not task_dir.name.startswith('.'):
                    # Check if it has any prompt files
                    yaml_files = list(task_dir.glob("*.yaml"))
                    if yaml_files:
                        tasks.append({
                            "name": task_dir.name,
                            "prompt_count": len(yaml_files),
                            "has_multilingual": any("-" in f.stem for f in yaml_files)
                        })
        
        response_data = {
            "tasks": tasks,
            "total_tasks": len(tasks),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Listed {len(tasks)} prompt tasks")
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Failed to list prompt tasks: {str(e)}")
        error_response = create_error_response(
            code="LIST_TASKS_ERROR",
            message="無法列出提示任務",
            details=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.dict()
        )