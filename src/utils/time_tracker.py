"""
Simple Time Tracker for Performance Monitoring
用於追蹤 API 執行時間的工具類別
"""
import time
from typing import Any


class SimpleTimeTracker:
    """簡單的時間追蹤器, 用於記錄各個執行階段的時間"""

    def __init__(self, enabled: bool = True):
        """
        初始化時間追蹤器

        Args:
            enabled: 是否啟用時間追蹤
        """
        self.enabled = enabled
        self.start_time = None
        self.tasks = []
        self.current_task = None

    def start(self):
        """開始計時"""
        if not self.enabled:
            return
        self.start_time = time.time() * 1000  # 轉換為毫秒
        self.tasks = []

    def start_task(self, task_name: str, description: str = ""):
        """
        開始一個新任務

        Args:
            task_name: 任務名稱 (preparation, cache_operations, db_operations, processing)
            description: 任務描述
        """
        if not self.enabled:
            return

        # 如果有正在進行的任務, 先結束它
        if self.current_task:
            self.end_task()

        current_time = time.time() * 1000
        self.current_task = {
            "task": task_name,
            "start_ms": current_time - self.start_time,
            "description": description
        }

    def end_task(self):
        """結束當前任務"""
        if not self.enabled or not self.current_task:
            return

        current_time = time.time() * 1000
        end_ms = current_time - self.start_time

        self.current_task["end_ms"] = end_ms
        self.current_task["duration_ms"] = end_ms - self.current_task["start_ms"]

        # 如果任務時間太短(< 1ms), 標記為跳過
        if self.current_task["duration_ms"] < 1:
            self.current_task["skipped"] = True

        self.tasks.append(self.current_task)
        self.current_task = None

    def get_tracking_data(self) -> dict[str, Any] | None:
        """
        獲取時間追蹤數據

        Returns:
            包含時間追蹤資訊的字典, 如果未啟用則返回 None
        """
        if not self.enabled:
            return None

        # 確保最後一個任務已結束
        if self.current_task:
            self.end_task()

        if not self.tasks:
            return None

        total_ms = time.time() * 1000 - self.start_time

        # 計算各任務的時間百分比
        task_times = {}
        for task in self.tasks:
            task_name = task["task"]
            if task_name not in task_times:
                task_times[task_name] = 0
            task_times[task_name] += task["duration_ms"]

        # 生成摘要
        summary = {}
        for task_name, duration in task_times.items():
            percentage = (duration / total_ms * 100) if total_ms > 0 else 0
            summary[f"{task_name}_pct"] = round(percentage, 1)

        # 生成時間線(簡化版, 只包含必要欄位)
        timeline = []
        for task in self.tasks:
            timeline_task = {
                "task": task["task"],
                "duration_ms": round(task["duration_ms"], 0),
            }
            if task["description"]:
                timeline_task["description"] = task["description"]
            if task.get("skipped"):
                timeline_task["skipped"] = True
            timeline.append(timeline_task)

        return {
            "enabled": True,
            "total_ms": round(total_ms, 0),
            "timeline": timeline,
            "summary": summary
        }

    def add_task_result(self, task_name: str, duration_ms: float, description: str = ""):
        """
        直接添加一個已完成的任務(用於並行任務)

        Args:
            task_name: 任務名稱
            duration_ms: 任務持續時間(毫秒)
            description: 任務描述
        """
        if not self.enabled:
            return

        task = {
            "task": task_name,
            "duration_ms": round(duration_ms, 0),
            "description": description
        }

        if duration_ms < 1:
            task["skipped"] = True

        self.tasks.append(task)
