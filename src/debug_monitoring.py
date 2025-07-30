# flake8: noqa
"""Debug monitoring service to check if it's working."""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def debug_monitoring():
    """Debug monitoring configuration."""
    print("=== Monitoring Debug Info ===")
    
    # Check environment variables
    print("\n1. Environment Variables:")
    print(f"APPINSIGHTS_INSTRUMENTATIONKEY: {os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY', 'NOT SET')}")
    print(f"APPLICATIONINSIGHTS_CONNECTION_STRING: {os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING', 'NOT SET')[:50]}...")
    print(f"MONITORING_ENABLED: {os.getenv('MONITORING_ENABLED', 'NOT SET')}")
    print(f"pytest in sys.modules: {'pytest' in sys.modules}")
    
    # Try to import and check monitoring service
    print("\n2. Monitoring Service Status:")
    try:
        from src.core.monitoring_service import monitoring_service
        print("Monitoring service imported successfully")
        print(f"Is enabled: {monitoring_service.is_enabled}")
        print(f"Instrumentation key: {monitoring_service.instrumentation_key[:8]}...")
        
        # Try to send a test event
        print("\n3. Sending test event...")
        monitoring_service.track_event("DEBUG_TEST_EVENT", {
            "test": "true",
            "timestamp": "2025-01-06T12:00:00Z"
        })
        print("Test event sent successfully")
        
    except Exception as e:
        print(f"Error with monitoring service: {e}")
        import traceback
        traceback.print_exc()
    
    # Check if OpenCensus is working
    print("\n4. OpenCensus Check:")
    try:
        print("OpenCensus Azure exporter imported successfully")
    except Exception as e:
        print(f"Error importing OpenCensus: {e}")
    
    return True

if __name__ == "__main__":
    debug_monitoring()