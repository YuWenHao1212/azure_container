#!/usr/bin/env python3
"""
Output Formatter for Ruff-checker System
優化 Ruff 檢查系統的輸出格式和用戶體驗
"""

from datetime import datetime
from typing import Dict, List, Optional


class RuffOutputFormatter:
    """Ruff 輸出格式化器"""
    
    # 顏色代碼
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bg_red': '\033[41m',
        'bg_green': '\033[42m',
        'bg_yellow': '\033[43m',
    }
    
    # Sub Agent 專屬顏色主題（黃色）
    SUBAGENT_THEME = {
        'primary': '\033[1;33m',    # 粗體黃色
        'secondary': '\033[33m',     # 普通黃色
        'success': '\033[1;32m',     # 粗體綠色
        'warning': '\033[1;31m',     # 粗體紅色
        'info': '\033[1;36m',        # 粗體青色
        'reset': '\033[0m'
    }
    
    def __init__(self, use_colors: bool = True, theme: str = 'subagent'):
        self.use_colors = use_colors
        self.theme = theme
        
    def colorize(self, text: str, color: str) -> str:
        """為文字添加顏色"""
        if not self.use_colors:
            return text
            
        if self.theme == 'subagent' and color in self.SUBAGENT_THEME:
            return f"{self.SUBAGENT_THEME[color]}{text}{self.SUBAGENT_THEME['reset']}"
        elif color in self.COLORS:
            return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"
        
        return text
    
    def format_header(self, title: str, status: str = "info") -> str:
        """格式化標題"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self.theme == 'subagent':
            # Sub Agent 專用標題格式
            lines = [
                self.colorize("═" * 65, 'primary'),
                self.colorize(f"🛡️  {title} - {timestamp}", 'primary'),
                self.colorize("═" * 65, 'primary')
            ]
        else:
            # 一般標題格式
            color = 'yellow' if status == 'warning' else 'green' if status == 'success' else 'cyan'
            lines = [
                "═" * 65,
                self.colorize(f"⚠️  {title} - {timestamp}", color),
                "═" * 65
            ]
        
        return "\n".join(lines)
    
    def format_statistics(self, stats: Dict) -> str:
        """格式化統計資訊"""
        lines = [self.colorize("📊 檢查統計:", 'info')]
        
        for key, value in stats.items():
            if key == 'files_checked':
                lines.append(f"   • 檢查檔案: {self.colorize(str(value), 'primary')}")
            elif key == 'total_errors':
                color = 'warning' if value > 0 else 'success'
                lines.append(f"   • 總錯誤數: {self.colorize(str(value), color)}")
            elif key == 'auto_fixable':
                color = 'info' if value > 0 else 'secondary'
                lines.append(f"   • 可自動修復: {self.colorize(str(value), color)}")
            elif key == 'fixed_count':
                lines.append(f"   • 已修復: {self.colorize(str(value), 'success')}")
        
        return "\n".join(lines)
    
    def format_error_breakdown(self, errors: Dict[str, int]) -> str:
        """格式化錯誤分解"""
        if not errors:
            return self.colorize("🎉 未發現任何程式碼品質問題！", 'success')
        
        lines = [self.colorize("🔍 錯誤類型分析:", 'info')]
        
        # 按錯誤數量排序
        sorted_errors = sorted(errors.items(), key=lambda x: x[1], reverse=True)
        
        for error_code, count in sorted_errors:
            error_desc = self._get_error_description(error_code)
            severity = self._get_error_severity(error_code)
            
            severity_color = {
                'high': 'warning',
                'medium': 'yellow',
                'low': 'secondary'
            }.get(severity, 'secondary')
            
            lines.append(f"   • {self.colorize(error_code, severity_color)}: "
                        f"{self.colorize(str(count), 'primary')} "
                        f"({error_desc})")
        
        return "\n".join(lines)
    
    def format_file_list(self, files: List[str], title: str = "檢查檔案") -> str:
        """格式化檔案列表"""
        if not files:
            return ""
        
        lines = [self.colorize(f"📁 {title}:", 'info')]
        
        # 限制顯示的檔案數量
        display_files = files[:10]
        for file in display_files:
            lines.append(f"   • {file}")
        
        if len(files) > 10:
            remaining = len(files) - 10
            lines.append(self.colorize(f"   ... 還有 {remaining} 個檔案", 'secondary'))
        
        return "\n".join(lines)
    
    def format_recommendations(self, errors: Dict[str, int], files: List[str]) -> str:
        """格式化建議和行動項目"""
        if not errors:
            return ""
        
        lines = [self.colorize("💡 建議行動:", 'info')]
        
        # 自動修復建議
        fixable_errors = self._get_fixable_errors(errors.keys())
        if fixable_errors:
            file_list = " ".join(files[:5])  # 限制命令長度
            if len(files) > 5:
                file_list += " ..."
            
            lines.append(f"   1. 快速修復: {self.colorize(f'ruff check --fix {file_list} --line-length=120', 'primary')}")
        
        # 詳細檢視建議
        lines.append(f"   2. 詳細檢視: {self.colorize('ruff check . --line-length=120', 'primary')}")
        
        # 嚴重錯誤特別提醒
        critical_errors = self._get_critical_errors(errors.keys())
        if critical_errors:
            lines.append(f"   3. {self.colorize('⚠️  優先處理:', 'warning')} {', '.join(critical_errors)}")
        
        return "\n".join(lines)
    
    def format_footer(self) -> str:
        """格式化頁腳"""
        return self.colorize("═" * 65, 'primary' if self.theme == 'subagent' else 'reset')
    
    def format_success_summary(self, stats: Dict) -> str:
        """格式化成功總結"""
        files_count = stats.get('files_checked', 0)
        lines = [
            self.colorize("🏆 程式碼品質檢查完成", 'success'),
            f"   ✅ {files_count} 個檔案符合品質標準",
            f"   🎯 專案程式碼品質優良，可安全部署"
        ]
        return "\n".join(lines)
    
    def format_complete_report(self, 
                             title: str,
                             stats: Dict,
                             errors: Dict[str, int] = None,
                             files: List[str] = None,
                             recommendations: bool = True) -> str:
        """格式化完整報告"""
        parts = [
            self.format_header(title),
            "",
            self.format_statistics(stats),
            ""
        ]
        
        if errors:
            parts.extend([
                self.format_error_breakdown(errors),
                ""
            ])
            
            if files and recommendations:
                parts.extend([
                    self.format_recommendations(errors, files),
                    ""
                ])
        else:
            parts.extend([
                self.format_success_summary(stats),
                ""
            ])
        
        if files and len(files) <= 10:  # 只顯示較短的檔案列表
            parts.extend([
                self.format_file_list(files),
                ""
            ])
        
        parts.append(self.format_footer())
        
        return "\n".join(parts)
    
    def _get_error_description(self, error_code: str) -> str:
        """獲取錯誤描述"""
        descriptions = {
            'E501': '行長度超過限制',
            'F401': '未使用的 import',
            'F841': '未使用的變數',
            'I001': 'Import 排序問題',
            'W292': '檔案結尾缺少換行',
            'S105': '硬編碼密碼',
            'S603': '子程序安全問題',
            'S607': '程序路徑安全問題',
            'RUF001': '模糊 Unicode 字元',
            'RUF003': '註解中模糊字元',
            'SIM102': '可合併的條件',
            'E741': '模糊變數名稱'
        }
        return descriptions.get(error_code, '未知錯誤類型')
    
    def _get_error_severity(self, error_code: str) -> str:
        """獲取錯誤嚴重程度"""
        high_severity = ['S105', 'S603', 'S607']  # 安全問題
        medium_severity = ['E501', 'F841', 'E741']  # 程式碼品質
        
        if error_code in high_severity:
            return 'high'
        elif error_code in medium_severity:
            return 'medium'
        return 'low'
    
    def _get_fixable_errors(self, error_codes) -> List[str]:
        """獲取可自動修復的錯誤"""
        fixable = ['F401', 'I001', 'W292', 'RUF100', 'RUF005']
        return [code for code in error_codes if code in fixable]
    
    def _get_critical_errors(self, error_codes) -> List[str]:
        """獲取需優先處理的關鍵錯誤"""
        critical = ['S105', 'S603', 'S607']  # 安全相關
        return [code for code in error_codes if code in critical]


# 使用範例
if __name__ == "__main__":
    formatter = RuffOutputFormatter(theme='subagent')
    
    # 測試報告格式
    stats = {
        'files_checked': 25,
        'total_errors': 8,
        'auto_fixable': 5,
        'fixed_count': 3
    }
    
    errors = {
        'E501': 3,
        'F401': 2,
        'I001': 2,
        'S105': 1
    }
    
    files = ['test_file1.py', 'test_file2.py', 'src/main.py']
    
    report = formatter.format_complete_report(
        "Ruff 程式碼品質檢查結果",
        stats,
        errors,
        files
    )
    
    print(report)