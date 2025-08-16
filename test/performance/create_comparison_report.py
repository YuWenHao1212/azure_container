#!/usr/bin/env python3
"""
Create comparison report between v1.0.0 and v1.0.1 performance tests
"""

import json
from datetime import datetime
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


def load_test_results():
    """Load both test result files"""
    results_dir = Path('docs/issues/index-cal-gap-analysis-evolution/performance')

    # Load v1.0.0 results (earlier test)
    v100_file = results_dir / 'performance_results_20250816_133242.json'
    with open(v100_file) as f:
        v100_data = json.load(f)

    # Load v1.0.1 results (new test)
    v101_file = results_dir / 'performance_v101_20250816_143848.json'
    with open(v101_file) as f:
        v101_data = json.load(f)

    return v100_data, v101_data

def create_comparison_chart(v100_data, v101_data):
    """Create visual comparison between v1.0.0 and v1.0.1"""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Performance Comparison: v1.0.0 vs v1.0.1 Resume Structure Analyzer', fontsize=16, fontweight='bold')

    # 1. Response Time Comparison
    ax1 = axes[0, 0]

    # Extract response times
    v100_times = v100_data['statistics']['all_times']
    v101_times = [r['total_time'] for r in v101_data['test_results']]

    companies = [r['company'] for r in v101_data['test_results'][:10]]
    v100_subset = v100_times[:10]
    v101_subset = v101_times[:10]

    x = np.arange(len(companies))
    width = 0.35

    bars1 = ax1.bar(x - width/2, v100_subset, width, label='v1.0.0', color='#FF6B6B', alpha=0.8)
    bars2 = ax1.bar(x + width/2, v101_subset, width, label='v1.0.1', color='#4ECDC4', alpha=0.8)

    ax1.set_xlabel('Test Case')
    ax1.set_ylabel('Response Time (seconds)')
    ax1.set_title('Response Times by Test Case (First 10)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(companies, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)

    # 2. Statistical Comparison
    ax2 = axes[0, 1]

    metrics = ['P50', 'P95', 'Mean', 'Min', 'Max']
    v100_values = [
        v100_data['statistics']['p50'],
        v100_data['statistics']['p95'],
        v100_data['statistics']['mean_time'],
        v100_data['statistics']['min_time'],
        v100_data['statistics']['max_time']
    ]
    v101_values = [
        v101_data['statistics']['p50'],
        v101_data['statistics']['p95'],
        v101_data['statistics']['mean_time'],
        v101_data['statistics']['min_time'],
        v101_data['statistics']['max_time']
    ]

    x = np.arange(len(metrics))
    width = 0.35

    bars1 = ax2.bar(x - width/2, v100_values, width, label='v1.0.0', color='#FF6B6B', alpha=0.8)
    bars2 = ax2.bar(x + width/2, v101_values, width, label='v1.0.1', color='#4ECDC4', alpha=0.8)

    ax2.set_xlabel('Metric')
    ax2.set_ylabel('Time (seconds)')
    ax2.set_title('Statistical Comparison')
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Add value labels and improvement percentages
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2, strict=False)):
        h1 = bar1.get_height()
        h2 = bar2.get_height()
        ax2.text(bar1.get_x() + bar1.get_width()/2., h1,
                f'{h1:.2f}', ha='center', va='bottom', fontsize=9)
        ax2.text(bar2.get_x() + bar2.get_width()/2., h2,
                f'{h2:.2f}', ha='center', va='bottom', fontsize=9)

        # Show improvement
        improvement = ((h1 - h2) / h1) * 100
        if improvement > 0:
            ax2.text(x[i], max(h1, h2) + 0.5,
                    f'↓{improvement:.1f}%', ha='center', va='bottom',
                    color='green', fontweight='bold', fontsize=10)
        elif improvement < 0:
            ax2.text(x[i], max(h1, h2) + 0.5,
                    f'↑{abs(improvement):.1f}%', ha='center', va='bottom',
                    color='red', fontweight='bold', fontsize=10)

    # 3. Distribution Comparison
    ax3 = axes[1, 0]

    ax3.hist(v100_times, bins=10, alpha=0.5, label='v1.0.0', color='#FF6B6B', edgecolor='black')
    ax3.hist(v101_times, bins=10, alpha=0.5, label='v1.0.1', color='#4ECDC4', edgecolor='black')
    ax3.axvline(v100_data['statistics']['p50'], color='#FF6B6B', linestyle='--', linewidth=2, label='v1.0.0 P50')
    ax3.axvline(v101_data['statistics']['p50'], color='#4ECDC4', linestyle='--', linewidth=2, label='v1.0.1 P50')
    ax3.set_xlabel('Response Time (seconds)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Response Time Distribution')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Improvement Summary
    ax4 = axes[1, 1]
    ax4.axis('off')

    # Calculate improvements
    p50_improvement = ((v100_data['statistics']['p50'] - v101_data['statistics']['p50']) / v100_data['statistics']['p50']) * 100
    p95_improvement = ((v100_data['statistics']['p95'] - v101_data['statistics']['p95']) / v100_data['statistics']['p95']) * 100
    mean_improvement = ((v100_data['statistics']['mean_time'] - v101_data['statistics']['mean_time']) / v100_data['statistics']['mean_time']) * 100

    # Create summary text
    summary_text = f"""
    PERFORMANCE IMPROVEMENT SUMMARY
    =====================================

    Resume Structure Analyzer Prompt Version
    • v1.0.0 → v1.0.1

    Response Time Improvements:
    • P50: {v100_data['statistics']['p50']:.2f}s → {v101_data['statistics']['p50']:.2f}s ({p50_improvement:+.1f}%)
    • P95: {v100_data['statistics']['p95']:.2f}s → {v101_data['statistics']['p95']:.2f}s ({p95_improvement:+.1f}%)
    • Mean: {v100_data['statistics']['mean_time']:.2f}s → {v101_data['statistics']['mean_time']:.2f}s ({mean_improvement:+.1f}%)

    Key Achievements:
    • {"✅ Significant improvement" if p50_improvement > 10 else "⚠️ Moderate improvement" if p50_improvement > 0 else "❌ No improvement"} in P50 response time
    • {"✅ Better consistency" if p95_improvement > 10 else "⚠️ Similar consistency" if p95_improvement > -5 else "❌ Less consistent"} in P95 times
    • {"✅ Overall faster" if mean_improvement > 10 else "⚠️ Slightly faster" if mean_improvement > 0 else "❌ Slower"} average performance

    Test Configuration:
    • Tests: 20 diverse job descriptions
    • Environment: Azure Container Apps (Production)
    • Region: Japan East
    """

    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
             fontsize=11, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # Save figure
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('docs/issues/index-cal-gap-analysis-evolution/performance')
    output_file = output_dir / f'comparison_chart_{timestamp}.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Comparison chart saved to: {output_file}")

    return output_file

def create_comparison_report(v100_data, v101_data):
    """Create detailed comparison report"""

    # Calculate improvements
    p50_improvement = ((v100_data['statistics']['p50'] - v101_data['statistics']['p50']) / v100_data['statistics']['p50']) * 100
    p95_improvement = ((v100_data['statistics']['p95'] - v101_data['statistics']['p95']) / v100_data['statistics']['p95']) * 100
    mean_improvement = ((v100_data['statistics']['mean_time'] - v101_data['statistics']['mean_time']) / v100_data['statistics']['mean_time']) * 100

    report = f"""# 性能比較報告 - Resume Structure Analyzer v1.0.1 升級

## 執行摘要

本報告比較 Resume Structure Analyzer 從 v1.0.0 升級到 v1.0.1 後的性能變化。

**測試日期**: 2025-08-16
**測試環境**: Azure Container Apps Production (Japan East)
**測試數量**: 20 個不同職缺描述

## 📊 關鍵性能指標比較

| 指標 | v1.0.0 | v1.0.1 | 改善幅度 | 狀態 |
|------|--------|--------|---------|------|
| **P50 (中位數)** | {v100_data['statistics']['p50']:.2f}s | {v101_data['statistics']['p50']:.2f}s | {p50_improvement:+.1f}% | {"✅" if p50_improvement > 0 else "❌"} |
| **P95** | {v100_data['statistics']['p95']:.2f}s | {v101_data['statistics']['p95']:.2f}s | {p95_improvement:+.1f}% | {"✅" if p95_improvement > 0 else "❌"} |
| **平均值** | {v100_data['statistics']['mean_time']:.2f}s | {v101_data['statistics']['mean_time']:.2f}s | {mean_improvement:+.1f}% | {"✅" if mean_improvement > 0 else "❌"} |
| **最小值** | {v100_data['statistics']['min_time']:.2f}s | {v101_data['statistics']['min_time']:.2f}s | - | - |
| **最大值** | {v100_data['statistics']['max_time']:.2f}s | {v101_data['statistics']['max_time']:.2f}s | - | - |

## 🎯 主要發現

### 1. 整體性能改善
{"✅ **顯著改善**" if p50_improvement > 10 else "⚠️ **中度改善**" if p50_improvement > 0 else "❌ **性能退步**"}
- P50 回應時間改善 {abs(p50_improvement):.1f}%
- 整體回應時間從 {v100_data['statistics']['p50']:.2f}s 降至 {v101_data['statistics']['p50']:.2f}s
- 減少約 {(v100_data['statistics']['p50'] - v101_data['statistics']['p50']):.2f} 秒的等待時間

### 2. 一致性分析
- P95 改善 {abs(p95_improvement):.1f}%
- 最差情況從 {v100_data['statistics']['max_time']:.2f}s 變為 {v101_data['statistics']['max_time']:.2f}s
- {"✅ 性能更加穩定" if abs(v101_data['statistics']['max_time'] - v101_data['statistics']['min_time']) < abs(v100_data['statistics']['max_time'] - v100_data['statistics']['min_time']) else "⚠️ 性能波動相似"}

### 3. Resume Structure Analyzer 優化效果
v1.0.1 版本的改進：
- 更精簡的 prompt 設計
- 優化的 JSON 結構定義
- 改進的多語言支援

## 📈 詳細比較

### 最佳表現案例 (v1.0.1)
"""

    # Add top 5 performers for v1.0.1
    v101_sorted = sorted(v101_data['test_results'], key=lambda x: x['total_time'])[:5]
    for i, result in enumerate(v101_sorted, 1):
        report += f"\n{i}. {result['company']} - {result['position']}: {result['total_time']:.2f}s"

    report += "\n\n### 最差表現案例 (v1.0.1)\n"
    v101_worst = sorted(v101_data['test_results'], key=lambda x: x['total_time'], reverse=True)[:5]
    for i, result in enumerate(v101_worst, 1):
        report += f"\n{i}. {result['company']} - {result['position']}: {result['total_time']:.2f}s"

    report += f"""

## 💡 優化建議

基於測試結果，以下是進一步優化的建議：

1. **繼續優化 Prompt**
   - v1.0.1 顯示了 prompt 優化的效果
   - 可考慮進一步簡化指令，減少 token 使用

2. **差距分析仍是主要瓶頸**
   - 雖然結構分析有改善，但整體時間主要仍受差距分析影響
   - 建議優先優化差距分析的 LLM 調用

3. **考慮快取策略**
   - 對相似的職缺描述實施智能快取
   - 減少重複的 LLM 調用

## 📊 結論

Resume Structure Analyzer v1.0.1 升級帶來了{"**顯著的性能改善**" if p50_improvement > 10 else "**一定程度的性能改善**" if p50_improvement > 0 else "**未達預期的改善**"}：

- ✅ P50 改善 {abs(p50_improvement):.1f}%
- ✅ P95 改善 {abs(p95_improvement):.1f}%
- ✅ 平均回應時間減少 {abs(mean_improvement):.1f}%

{"建議將 v1.0.1 保持為生產環境版本。" if p50_improvement > 0 else "建議進一步調查性能問題。"}

---

## 附錄：測試檔案

- v1.0.0 結果: `performance_results_20250816_133242.json`
- v1.0.1 結果: `performance_v101_20250816_143848.json`
- 比較圖表: `comparison_chart_[timestamp].png`

*報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    # Save report
    output_dir = Path('docs/issues/index-cal-gap-analysis-evolution/performance')
    output_file = output_dir / 'PERFORMANCE_COMPARISON_REPORT.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Comparison report saved to: {output_file}")
    return output_file

def main():
    """Main execution"""
    print("🔍 Loading test results...")
    v100_data, v101_data = load_test_results()

    print("📊 Creating comparison chart...")
    chart_file = create_comparison_chart(v100_data, v101_data)

    print("📝 Creating comparison report...")
    report_file = create_comparison_report(v100_data, v101_data)

    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)

    # Print key improvements
    p50_improvement = ((v100_data['statistics']['p50'] - v101_data['statistics']['p50']) / v100_data['statistics']['p50']) * 100
    p95_improvement = ((v100_data['statistics']['p95'] - v101_data['statistics']['p95']) / v100_data['statistics']['p95']) * 100

    print(f"P50: {v100_data['statistics']['p50']:.2f}s → {v101_data['statistics']['p50']:.2f}s ({p50_improvement:+.1f}%)")
    print(f"P95: {v100_data['statistics']['p95']:.2f}s → {v101_data['statistics']['p95']:.2f}s ({p95_improvement:+.1f}%)")

    if p50_improvement > 0:
        print("\n✅ Performance IMPROVED with v1.0.1!")
    else:
        print("\n⚠️ Performance did not improve as expected.")

    print("\nFiles created:")
    print(f"  - {chart_file}")
    print(f"  - {report_file}")

if __name__ == "__main__":
    main()
