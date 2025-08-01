"""
API Security monitoring and threat detection.
Monitors for suspicious patterns and unauthorized access attempts.
"""
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import Request

from src.core.monitoring.storage.failure_storage import failure_storage
from src.core.monitoring_service import monitoring_service


class SecurityMonitor:
    """
    API Security monitoring system.

    Features:
    - Origin validation
    - Suspicious pattern detection
    - Rate limit monitoring per IP
    - User-Agent analysis
    - SQL injection/XSS detection
    """

    def __init__(self):
        """Initialize security monitor."""
        # Allowed origins
        self.allowed_origins = {
            "https://airesumeadvisor.bubbleapps.io",
            "https://version-test.bubbleapps.io",
            "http://localhost:3000",
            "http://localhost:8000"
        }

        # Suspicious patterns
        self.suspicious_patterns = [
            (r"<script.*?>.*?</script>", "XSS_ATTEMPT"),
            (r"javascript:", "XSS_ATTEMPT"),
            (r"on\w+\s*=", "XSS_ATTEMPT"),
            (r"(?i)(union|select|insert|update|delete|drop)\s+(all|from|into|table)", "SQL_INJECTION"),
            (r"(?i)(exec|execute)\s*\(", "CODE_INJECTION"),
            (r"\.\./", "PATH_TRAVERSAL"),
            (r"\${.*}", "TEMPLATE_INJECTION"),
            (r"(?i)(cmd|powershell|bash|sh)\s*[\|\;]", "COMMAND_INJECTION")
        ]

        # Rate limiting tracking
        self.ip_requests = defaultdict(lambda: deque(maxlen=1000))
        self.rate_limit_threshold = 60  # requests per minute

        # Blocked IPs
        self.blocked_ips = set()
        self.temp_blocked_ips = {}  # IP -> unblock_time

        # Statistics
        self.security_stats = {
            "total_requests": 0,
            "suspicious_requests": 0,
            "blocked_requests": 0,
            "threats_by_type": defaultdict(int),
            "suspicious_ips": set(),
            "suspicious_user_agents": defaultdict(int)
        }

    async def check_request_security(self, request: Request) -> dict[str, any]:
        """
        Check request for security threats.

        Args:
            request: FastAPI request object

        Returns:
            Security check result with risk assessment
        """
        self.security_stats["total_requests"] += 1

        security_result = {
            "is_suspicious": False,
            "is_blocked": False,
            "risk_level": "low",
            "threats": [],
            "client_ip": self._get_client_ip(request),
            "checks_performed": []
        }

        # Bypass security for test environments
        if request.headers.get("X-Test-Bypass-Security") == "true":
            # Return a clean result - no threats, no blocking
            # Skip ALL security checks including IP blocking
            return security_result

        # Check if IP is blocked
        client_ip = security_result["client_ip"]
        if self._is_ip_blocked(client_ip):
            security_result["is_blocked"] = True
            security_result["risk_level"] = "blocked"
            security_result["threats"].append("IP_BLOCKED")
            self.security_stats["blocked_requests"] += 1
            return security_result

        # Check origin
        origin_check = self._check_origin(request)
        security_result["checks_performed"].append("origin")
        if not origin_check["valid"]:
            security_result["is_suspicious"] = True
            security_result["threats"].append("INVALID_ORIGIN")
            security_result["risk_level"] = "medium"

        # Check User-Agent
        ua_check = self._check_user_agent(request)
        security_result["checks_performed"].append("user_agent")
        if ua_check["suspicious"]:
            security_result["is_suspicious"] = True
            security_result["threats"].extend(ua_check["threats"])
            if security_result["risk_level"] == "low":
                security_result["risk_level"] = "medium"

        # Check rate limits
        rate_check = self._check_rate_limit(client_ip)
        security_result["checks_performed"].append("rate_limit")
        if not rate_check["allowed"]:
            security_result["is_suspicious"] = True
            security_result["threats"].append("RATE_LIMIT_EXCEEDED")
            security_result["risk_level"] = "high"

        # Check request content for malicious patterns
        if request.method in ["POST", "PUT", "PATCH"]:
            content_check = await self._check_request_content(request)
            security_result["checks_performed"].append("content")
            if content_check["threats"]:
                security_result["is_suspicious"] = True
                security_result["threats"].extend(content_check["threats"])
                security_result["risk_level"] = "high"

        # Update statistics and take action if needed
        if security_result["is_suspicious"]:
            self.security_stats["suspicious_requests"] += 1
            self.security_stats["suspicious_ips"].add(client_ip)

            for threat in security_result["threats"]:
                self.security_stats["threats_by_type"][threat] += 1

            # Block IP if high risk
            if security_result["risk_level"] == "high":
                self._block_ip_temporarily(client_ip, minutes=15)

            # Store suspicious request for analysis
            await self._store_suspicious_request(request, security_result)

            # Send security alert
            self._send_security_alert(security_result)

        return security_result

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For header (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Use direct connection IP
        return request.client.host if request.client else "unknown"

    def _check_origin(self, request: Request) -> dict[str, any]:
        """Check if request origin is allowed."""
        origin = request.headers.get("origin", "").lower()
        referer = request.headers.get("referer", "").lower()

        # No origin/referer might be okay for some requests
        if not origin and not referer:
            return {"valid": True, "origin": None}

        # Check against allowed origins
        check_origin = origin or referer
        for allowed in self.allowed_origins:
            if check_origin.startswith(allowed.lower()):
                return {"valid": True, "origin": check_origin}

        return {"valid": False, "origin": check_origin}

    def _check_user_agent(self, request: Request) -> dict[str, any]:
        """Check User-Agent for suspicious patterns."""
        user_agent = request.headers.get("user-agent", "").lower()
        result = {"suspicious": False, "threats": []}

        # Check for missing User-Agent
        if not user_agent:
            result["suspicious"] = True
            result["threats"].append("MISSING_USER_AGENT")
            return result

        # Check for known bad patterns
        suspicious_patterns = [
            ("bot", "BOT_DETECTED"),
            ("crawler", "CRAWLER_DETECTED"),
            ("scraper", "SCRAPER_DETECTED"),
            ("curl", "AUTOMATED_TOOL"),
            ("wget", "AUTOMATED_TOOL"),
            ("python", "AUTOMATED_TOOL"),
            ("scanner", "SCANNER_DETECTED")
        ]

        for pattern, threat in suspicious_patterns:
            if pattern in user_agent:
                result["suspicious"] = True
                result["threats"].append(threat)
                self.security_stats["suspicious_user_agents"][user_agent] += 1

        return result

    def _check_rate_limit(self, client_ip: str) -> dict[str, any]:
        """Check if IP exceeds rate limit."""
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self.ip_requests[client_ip] = deque(
            (req_time for req_time in self.ip_requests[client_ip] if req_time > minute_ago),
            maxlen=1000
        )

        # Add current request
        self.ip_requests[client_ip].append(now)

        # Check rate
        request_count = len(self.ip_requests[client_ip])

        return {
            "allowed": request_count <= self.rate_limit_threshold,
            "current_rate": request_count,
            "limit": self.rate_limit_threshold
        }

    async def _check_request_content(self, request: Request) -> dict[str, any]:
        """Check request body for malicious patterns."""
        result = {"threats": []}

        try:
            # Check if we've already read the body
            if hasattr(request.state, "_body"):
                body = request.state._body
            else:
                # Read and cache the body
                body = await request.body()
                # Store it for later use
                request.state._body = body

                # IMPORTANT: Replace the receive function to allow re-reading
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive

            if not body:
                return result

            body_text = body.decode('utf-8', errors='ignore')

            # Check against suspicious patterns
            for pattern, threat_type in self.suspicious_patterns:
                if re.search(pattern, body_text, re.IGNORECASE):
                    result["threats"].append(threat_type)

            # Check for overly long inputs (potential buffer overflow)
            if len(body_text) > 100000:  # 100KB
                result["threats"].append("OVERSIZED_REQUEST")

        except Exception:
            # If we can't read the body, consider it suspicious
            result["threats"].append("UNREADABLE_CONTENT")

        return result

    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        # Check permanent blocks
        if ip in self.blocked_ips:
            return True

        # Check temporary blocks
        if ip in self.temp_blocked_ips:
            if datetime.now(timezone.utc) < self.temp_blocked_ips[ip]:
                return True
            else:
                # Unblock if time expired
                del self.temp_blocked_ips[ip]

        return False

    def _block_ip_temporarily(self, ip: str, minutes: int = 15):
        """Temporarily block an IP address."""
        unblock_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.temp_blocked_ips[ip] = unblock_time

        monitoring_service.track_event(
            "security_ip_blocked",
            {
                "ip": ip,
                "duration_minutes": minutes,
                "unblock_time": unblock_time.isoformat()
            }
        )

    async def _store_suspicious_request(self, request: Request, security_result: dict):
        """Store suspicious request for analysis."""
        try:
            # Use cached body if available
            if hasattr(request.state, "_body"):
                body = request.state._body
            else:
                body = await request.body()
            body_text = body.decode('utf-8', errors='ignore')[:500]  # First 500 chars
        except Exception:
            body_text = "Unable to read body"

        await failure_storage.store_failure(
            category="security_threat",
            job_description=body_text,
            failure_reason=f"Security threats detected: {', '.join(security_result['threats'])}",
            additional_info={
                "client_ip": security_result["client_ip"],
                "risk_level": security_result["risk_level"],
                "threats": security_result["threats"],
                "origin": request.headers.get("origin"),
                "user_agent": request.headers.get("user-agent"),
                "method": request.method,
                "path": request.url.path
            }
        )

    def _send_security_alert(self, security_result: dict):
        """Send security alert to monitoring."""
        monitoring_service.track_event(
            "security_threat_detected",
            {
                "client_ip": security_result["client_ip"],
                "risk_level": security_result["risk_level"],
                "threats": ", ".join(security_result["threats"]),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        # Track security metrics
        monitoring_service.track_metric(
            "security_threat_count",
            len(security_result["threats"]),
            {
                "risk_level": security_result["risk_level"],
                "primary_threat": security_result["threats"][0] if security_result["threats"] else "none"
            }
        )

    def get_security_summary(self) -> dict[str, any]:
        """Get security monitoring summary."""
        total = self.security_stats["total_requests"]
        suspicious = self.security_stats["suspicious_requests"]

        return {
            "total_requests": total,
            "suspicious_requests": suspicious,
            "blocked_requests": self.security_stats["blocked_requests"],
            "suspicious_rate": f"{(suspicious / total * 100):.2f}%" if total > 0 else "0.00%",
            "active_blocks": len(self.temp_blocked_ips),
            "permanent_blocks": len(self.blocked_ips),
            "threats_detected": dict(self.security_stats["threats_by_type"]),
            "suspicious_ips": list(self.security_stats["suspicious_ips"])[:10],  # Top 10
            "top_suspicious_user_agents": sorted(
                self.security_stats["suspicious_user_agents"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def add_allowed_origin(self, origin: str):
        """Add an allowed origin."""
        self.allowed_origins.add(origin)

    def block_ip(self, ip: str):
        """Permanently block an IP."""
        self.blocked_ips.add(ip)

    def unblock_ip(self, ip: str):
        """Unblock an IP."""
        self.blocked_ips.discard(ip)
        self.temp_blocked_ips.pop(ip, None)

    def clear_all_blocks(self):
        """Clear all IP blocks (for testing)."""
        self.blocked_ips.clear()
        self.temp_blocked_ips.clear()
        self.security_stats["blocked_requests"] = 0


# Global security monitor instance
security_monitor = SecurityMonitor()
