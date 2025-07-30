"""
User-Agent parser for tracking request sources.
Identifies client types: Bubble.io, curl, Python scripts, browsers, etc.
"""
import re
from typing import Any


def parse_user_agent(user_agent: str) -> dict[str, Any]:
    """
    Parse User-Agent string to identify client type and details.
    
    Args:
        user_agent: User-Agent header string
        
    Returns:
        Dictionary with client_type, client_details, and is_api_client
    """
    if not user_agent:
        return {
            "client_type": "unknown",
            "client_details": "No User-Agent provided",
            "is_api_client": True,
            "is_browser": False
        }
    
    user_agent_lower = user_agent.lower()
    
    # Bubble.io detection
    if "bubble" in user_agent_lower:
        return {
            "client_type": "bubble.io",
            "client_details": "Bubble.io platform",
            "is_api_client": True,
            "is_browser": False
        }
    
    # curl detection
    if user_agent_lower.startswith("curl/"):
        version = user_agent.split("/")[1].split()[0] if "/" in user_agent else "unknown"
        return {
            "client_type": "curl",
            "client_details": f"curl {version}",
            "is_api_client": True,
            "is_browser": False
        }
    
    # Python requests library
    if "python-requests" in user_agent_lower:
        version = re.search(r'python-requests/([\d.]+)', user_agent_lower)
        version_str = version.group(1) if version else "unknown"
        return {
            "client_type": "python-requests",
            "client_details": f"Python requests library {version_str}",
            "is_api_client": True,
            "is_browser": False
        }
    
    # Python urllib
    if "python-urllib" in user_agent_lower or "python/3" in user_agent_lower:
        return {
            "client_type": "python-script",
            "client_details": "Python script (urllib or similar)",
            "is_api_client": True,
            "is_browser": False
        }
    
    # Postman
    if "postman" in user_agent_lower:
        return {
            "client_type": "postman",
            "client_details": "Postman API client",
            "is_api_client": True,
            "is_browser": False
        }
    
    # Insomnia
    if "insomnia" in user_agent_lower:
        return {
            "client_type": "insomnia",
            "client_details": "Insomnia REST client",
            "is_api_client": True,
            "is_browser": False
        }
    
    # HTTPie
    if "httpie" in user_agent_lower:
        return {
            "client_type": "httpie",
            "client_details": "HTTPie command line client",
            "is_api_client": True,
            "is_browser": False
        }
    
    # Node.js / Axios
    if "node-fetch" in user_agent_lower or "axios" in user_agent_lower:
        return {
            "client_type": "nodejs",
            "client_details": "Node.js HTTP client",
            "is_api_client": True,
            "is_browser": False
        }
    
    # Browsers
    browsers = {
        "chrome": "Chrome",
        "safari": "Safari",
        "firefox": "Firefox",
        "edge": "Edge",
        "opera": "Opera"
    }
    
    for key, name in browsers.items():
        if key in user_agent_lower:
            # Try to extract version
            version_match = re.search(rf'{key}/([\d.]+)', user_agent_lower)
            version = version_match.group(1) if version_match else "unknown"
            return {
                "client_type": "browser",
                "client_details": f"{name} {version}",
                "is_api_client": False,
                "is_browser": True
            }
    
    # Mobile apps
    if "okhttp" in user_agent_lower:
        return {
            "client_type": "mobile-app",
            "client_details": "Android app (OkHttp)",
            "is_api_client": True,
            "is_browser": False
        }
    
    if "alamofire" in user_agent_lower:
        return {
            "client_type": "mobile-app",
            "client_details": "iOS app (Alamofire)",
            "is_api_client": True,
            "is_browser": False
        }
    
    # Default
    return {
        "client_type": "other",
        "client_details": user_agent[:100],  # Truncate long user agents
        "is_api_client": True,
        "is_browser": False
    }


def get_client_category(client_type: str) -> str:
    """
    Get broader category for client type.
    
    Args:
        client_type: Specific client type
        
    Returns:
        Client category (api_testing, automation, browser, mobile, other)
    """
    api_testing = {"curl", "postman", "insomnia", "httpie"}
    automation = {"bubble.io", "python-requests", "python-script", "nodejs"}
    
    if client_type in api_testing:
        return "api_testing"
    elif client_type in automation:
        return "automation"
    elif client_type == "browser":
        return "browser"
    elif client_type == "mobile-app":
        return "mobile"
    else:
        return "other"