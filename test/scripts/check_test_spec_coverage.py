#!/usr/bin/env python3
"""
自動化工具檢查 TEST_SPEC 覆蓋率

此工具會：
1. 解析 TEST_SPEC.md 中定義的所有測試案例 ID
2. 掃描測試程式碼中的 TEST: API-XXX-XXX-XX 標記
3. 生成覆蓋率報告
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


class TestSpecCoverageChecker:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.test_spec_file = self.project_root / "test" / "TEST_SPEC.md"
        self.test_dir = self.project_root / "test"

        # 測試案例 ID 正則表達式
        self.test_id_pattern = re.compile(r'API-[A-Z]+-\d{3}-[A-Z]{2}')
        self.test_marker_pattern = re.compile(r'"""TEST:\s*(API-[A-Z]+-\d{3}-[A-Z]{2})')

    def parse_test_spec(self) -> dict[str, dict]:
        """解析 TEST_SPEC.md 文件，提取所有測試案例定義"""
        test_cases = {}

        if not self.test_spec_file.exists():
            raise FileNotFoundError(f"TEST_SPEC.md not found at {self.test_spec_file}")

        with open(self.test_spec_file, encoding='utf-8') as f:
            content = f.read()

        # 查找所有測試案例定義
        # 格式: #### API-XXX-XXX-XX: 描述
        pattern = re.compile(r'####\s+(API-[A-Z]+-\d{3}-[A-Z]{2}):\s*(.+)')

        for match in pattern.finditer(content):
            test_id = match.group(1)
            description = match.group(2).strip()

            # 提取模組信息
            module = test_id.split('-')[1]

            test_cases[test_id] = {
                'id': test_id,
                'description': description,
                'module': module,
                'status': 'not_implemented',
                'location': None
            }

        return test_cases

    def scan_test_files(self) -> dict[str, list[str]]:
        """掃描所有測試文件，找出已標記的測試案例"""
        marked_tests = defaultdict(list)

        # 掃描所有 Python 測試文件
        for test_file in self.test_dir.rglob("test_*.py"):
            with open(test_file, encoding='utf-8') as f:
                content = f.read()

            # 查找所有 TEST: API-XXX-XXX-XX 標記
            for match in self.test_marker_pattern.finditer(content):
                test_id = match.group(1)
                relative_path = test_file.relative_to(self.project_root)
                marked_tests[test_id].append(str(relative_path))

        return marked_tests

    def generate_coverage_report(self) -> dict:
        """生成覆蓋率報告"""
        # 解析 TEST_SPEC
        all_test_cases = self.parse_test_spec()

        # 掃描已實作的測試
        implemented_tests = self.scan_test_files()

        # 更新測試案例狀態
        for test_id, locations in implemented_tests.items():
            if test_id in all_test_cases:
                all_test_cases[test_id]['status'] = 'implemented'
                all_test_cases[test_id]['location'] = locations

        # 計算統計資料
        total_count = len(all_test_cases)
        implemented_count = len(implemented_tests)

        # 按模組分組統計
        module_stats = defaultdict(lambda: {'total': 0, 'implemented': 0})

        for test_case in all_test_cases.values():
            module = test_case['module']
            module_stats[module]['total'] += 1
            if test_case['status'] == 'implemented':
                module_stats[module]['implemented'] += 1

        # 生成報告
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_test_cases': total_count,
                'implemented_test_cases': implemented_count,
                'not_implemented_test_cases': total_count - implemented_count,
                'coverage_percentage': round((implemented_count / total_count * 100) if total_count > 0 else 0, 2)
            },
            'module_statistics': dict(module_stats),
            'test_cases': all_test_cases,
            'not_implemented_list': [
                test_id for test_id, info in all_test_cases.items()
                if info['status'] == 'not_implemented'
            ],
            'duplicate_implementations': [
                test_id for test_id, locations in implemented_tests.items()
                if len(locations) > 1
            ]
        }

        return report

    def generate_markdown_report(self, report: dict) -> str:
        """生成 Markdown 格式的報告"""
        md_lines = []

        # 標題
        md_lines.append("# TEST_SPEC 覆蓋率報告")
        md_lines.append(f"\n**生成時間**: {report['timestamp']}")
        md_lines.append("")

        # 總體統計
        md_lines.append("## 總體統計")
        summary = report['summary']
        md_lines.append(f"- **總測試案例數**: {summary['total_test_cases']}")
        md_lines.append(f"- **已實作案例數**: {summary['implemented_test_cases']}")
        md_lines.append(f"- **未實作案例數**: {summary['not_implemented_test_cases']}")
        md_lines.append(f"- **覆蓋率**: {summary['coverage_percentage']}%")
        md_lines.append("")

        # 模組統計
        md_lines.append("## 模組統計")
        md_lines.append("| 模組 | 總數 | 已實作 | 覆蓋率 |")
        md_lines.append("|------|------|--------|--------|")

        for module, stats in sorted(report['module_statistics'].items()):
            coverage = round((stats['implemented'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1)
            md_lines.append(f"| {module} | {stats['total']} | {stats['implemented']} | {coverage}% |")

        md_lines.append("")

        # 未實作清單
        if report['not_implemented_list']:
            md_lines.append("## 未實作的測試案例")
            for test_id in sorted(report['not_implemented_list']):
                test_info = report['test_cases'][test_id]
                md_lines.append(f"- **{test_id}**: {test_info['description']}")

        md_lines.append("")

        # 重複實作警告
        if report['duplicate_implementations']:
            md_lines.append("## ⚠️ 重複實作警告")
            md_lines.append("以下測試 ID 在多個文件中被標記：")
            for test_id in report['duplicate_implementations']:
                locations = ", ".join(report['test_cases'][test_id]['location'])
                md_lines.append(f"- **{test_id}**: {locations}")

        return "\n".join(md_lines)

    def run(self, output_dir: str | None = None):
        """執行覆蓋率檢查並生成報告"""
        # 生成報告
        report = self.generate_coverage_report()

        # 輸出到控制台
        print("\n" + "="*60)
        print("TEST_SPEC 覆蓋率檢查結果")
        print("="*60)
        print(f"總測試案例: {report['summary']['total_test_cases']}")
        print(f"已實作案例: {report['summary']['implemented_test_cases']}")
        print(f"覆蓋率: {report['summary']['coverage_percentage']}%")
        print("="*60)

        # 保存報告
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # JSON 報告
            json_file = output_path / "test_spec_coverage.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\nJSON 報告已保存至: {json_file}")

            # Markdown 報告
            md_content = self.generate_markdown_report(report)
            md_file = output_path / "test_spec_coverage.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"Markdown 報告已保存至: {md_file}")

        return report


def main():
    """主程式"""
    # 設定專案根目錄
    project_root = os.environ.get('PROJECT_ROOT', '/Users/yuwenhao/Documents/GitHub/azure_container')

    # 設定輸出目錄
    output_dir = os.path.join(project_root, 'test', 'reports')

    # 執行檢查
    checker = TestSpecCoverageChecker(project_root)
    report = checker.run(output_dir)

    # 如果覆蓋率低於閾值，返回非零退出碼  # noqa: RUF003
    threshold = 80  # 80% 覆蓋率閾值
    if report['summary']['coverage_percentage'] < threshold:
        print(f"\n⚠️ 警告: 覆蓋率 ({report['summary']['coverage_percentage']}%) 低於閾值 ({threshold}%)")
        sys.exit(1)
    else:
        print("\n✅ 覆蓋率檢查通過!")
        sys.exit(0)


if __name__ == "__main__":
    main()
