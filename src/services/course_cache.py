"""Course Search Cache Service"""
import hashlib
from datetime import datetime, timedelta
from typing import Any


class CourseSearchCache:
    """記憶體快取服務"""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_size = max_size

    def get_cache_key(self, skill_name: str, search_context: str,
                     category: str, threshold: float) -> str:
        """生成快取鍵值"""
        cache_str = f"{skill_name}|{search_context}|{category}|{threshold}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get(self, key: str) -> dict | None:
        """從快取取得資料"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return data
            else:
                # 過期，移除
                del self.cache[key]
        return None

    def set(self, key: str, data: Any):
        """存入快取"""
        # 檢查大小限制
        if len(self.cache) >= self.max_size:
            # 移除最舊的項目
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (data, datetime.now())

    def clear(self):
        """清空快取"""
        self.cache.clear()

    def stats(self) -> dict:
        """取得快取統計"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl.total_seconds()
        }
