#!/usr/bin/env python3
"""
Create Gantt Chart visualization from performance test results
Shows parallel execution timeline and identifies bottlenecks
"""

import json
from datetime import datetime
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


def load_latest_results():
    """Load the most recent performance test results"""
    results_dir = Path('docs/issues/index-cal-gap-analysis-evolution/performance')

    # Find the most recent results file
    result_files = list(results_dir.glob('quick_test_results_*.json'))
    if not result_files:
        print("No test results found")
        return None

    latest_file = max(result_files, key=lambda f: f.stat().st_mtime)
    print(f"Loading results from: {latest_file}")

    with open(latest_file) as f:
        return json.load(f)

def create_gantt_chart(results):
    """Create comprehensive Gantt chart visualization"""

    # Extract timing data
    test_cases = []
    for result in results['results']:
        if result['status'] == 'success' and 'data' in result:
            metadata = result['data'].get('metadata', {})
            if 'execution_timeline' in metadata:
                test_cases.append({
                    'name': result['test_case'],
                    'timeline': metadata['execution_timeline'],
                    'timings': metadata.get('detailed_timings_ms', {})
                })

    if not test_cases:
        print("No timeline data available")
        return

    # Create figure with subplots
    fig = plt.figure(figsize=(18, 12))

    # Define colors for different task types
    colors = {
        'keywords': '#FF6B6B',           # Red
        'embeddings': '#4ECDC4',         # Teal
        'structure_analysis': '#95E77E',  # Green
        'pgvector_warmup': '#FFE66D',    # Yellow
        'index_calculation': '#A8DADC',  # Light Blue
        'gap_analysis': '#457B9D',       # Dark Blue
        'course_availability': '#1D3557'  # Navy
    }

    # Plot 1: Detailed timeline for first test case
    ax1 = plt.subplot(3, 1, 1)
    plot_single_test_timeline(ax1, test_cases[0], colors)

    # Plot 2: Comparison across all test cases
    ax2 = plt.subplot(3, 1, 2)
    plot_comparison_timeline(ax2, test_cases, colors)

    # Plot 3: Performance statistics
    ax3 = plt.subplot(3, 1, 3)
    plot_performance_stats(ax3, results)

    plt.tight_layout()

    # Save the figure
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('docs/issues/index-cal-gap-analysis-evolution/performance')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'gantt_chart_accurate_{timestamp}.png'

    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Gantt chart saved to: {output_file}")

    plt.show()

    return output_file

def plot_single_test_timeline(ax, test_case, colors):
    """Plot detailed timeline for a single test case"""

    timeline = test_case['timeline']
    timings = test_case['timings']

    ax.set_title(f'Execution Timeline - {test_case["name"]}', fontsize=14, fontweight='bold')

    y_pos = 0
    y_labels = []
    max_time = 0

    # Plot parallel tasks
    if 'parallel_tasks' in timeline:
        ax.text(-500, y_pos + 0.5, '🔀 PARALLEL', fontsize=10, fontweight='bold', va='center')

        for task_name, task_data in timeline['parallel_tasks'].items():
            if isinstance(task_data, dict):
                start = task_data.get('start', 0)
                end = task_data.get('end', 0)

                if end > start:
                    # Draw task bar
                    ax.barh(y_pos, end - start, left=start, height=0.7,
                           color=colors.get(task_name, 'gray'), alpha=0.8,
                           edgecolor='black', linewidth=1)

                    # Add task duration text
                    duration_text = f'{end:.0f}ms'
                    if task_name == 'structure_analysis' and 'wait_time' in task_data:
                        duration_text += f' (+{task_data["wait_time"]:.0f}ms wait)'

                    ax.text(start + (end - start)/2, y_pos, duration_text,
                           ha='center', va='center', fontsize=9, color='white', fontweight='bold')

                    y_labels.append(task_name.replace('_', ' ').title())
                    y_pos += 1
                    max_time = max(max_time, end)

    # Add separator
    if y_pos > 0:
        ax.axhline(y=y_pos - 0.5, color='black', linestyle='--', alpha=0.5)
        y_pos += 0.5

    # Plot sequential tasks
    if 'sequential_tasks' in timeline:
        ax.text(-500, y_pos + 0.5, '➡️ SEQUENTIAL', fontsize=10, fontweight='bold', va='center')

        for task_name, task_data in timeline['sequential_tasks'].items():
            if isinstance(task_data, dict):
                start = task_data.get('start', 0)
                end = task_data.get('end', 0)

                if end > start:
                    # Draw task bar
                    ax.barh(y_pos, end - start, left=start, height=0.7,
                           color=colors.get(task_name, 'gray'), alpha=0.8,
                           edgecolor='black', linewidth=1)

                    # Add task duration text
                    duration = end - start
                    ax.text(start + duration/2, y_pos, f'{duration:.0f}ms',
                           ha='center', va='center', fontsize=9, color='white', fontweight='bold')

                    y_labels.append(task_name.replace('_', ' ').title())
                    y_pos += 1
                    max_time = max(max_time, end)

    # Add phase markers
    if 'embedding_time' in timings:
        ax.axvline(x=timings['embedding_time'], color='red', linestyle=':', alpha=0.5, label='Phase 2 Start')

    # Format axes
    ax.set_ylim(-0.5, y_pos - 0.5)
    ax.set_xlim(-600, max_time * 1.1)
    ax.set_xlabel('Time (milliseconds)', fontsize=11)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.grid(True, alpha=0.3, axis='x')

    # Add total time annotation
    total_time = timings.get('total_time', 0)
    ax.text(max_time * 1.05, y_pos/2, f'Total: {total_time:.0f}ms',
           fontsize=11, fontweight='bold', va='center',
           bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

def plot_comparison_timeline(ax, test_cases, colors):
    """Plot comparison of execution times across test cases"""

    ax.set_title('Execution Time Comparison Across Test Cases', fontsize=14, fontweight='bold')

    # Extract task timings for each test case
    task_types = ['keyword_matching_time', 'embedding_time', 'structure_analysis_time',
                  'index_calculation_time', 'gap_analysis_time', 'course_availability_time']

    x = np.arange(len(test_cases))
    width = 0.8
    bottom = np.zeros(len(test_cases))

    for task in task_types:
        values = []
        for tc in test_cases:
            value = tc['timings'].get(task, 0)
            values.append(value)

        task_name = task.replace('_time', '').replace('_', ' ')
        color = colors.get(task.replace('_time', ''), 'gray')

        ax.bar(x, values, width, bottom=bottom, label=task_name.title(),
               color=color, alpha=0.8, edgecolor='black', linewidth=0.5)

        # Add value labels for significant values
        for i, v in enumerate(values):
            if v > 500:  # Only show labels for values > 500ms
                ax.text(i, bottom[i] + v/2, f'{v:.0f}', ha='center', va='center',
                       fontsize=8, color='white', fontweight='bold')

        bottom += values

    ax.set_xlabel('Test Case', fontsize=11)
    ax.set_ylabel('Time (milliseconds)', fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([tc['name'] for tc in test_cases], rotation=45, ha='right')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(True, alpha=0.3, axis='y')

def plot_performance_stats(ax, results):
    """Plot performance statistics and bottleneck analysis"""

    ax.set_title('Performance Statistics & Bottleneck Analysis', fontsize=14, fontweight='bold')

    # Extract statistics
    stats = results.get('statistics', {})
    function_timings = stats.get('function_timings', {})

    if not function_timings:
        ax.text(0.5, 0.5, 'No statistics available', ha='center', va='center')
        return

    # Calculate averages and identify bottlenecks
    bottlenecks = []
    for func, times in function_timings.items():
        if times:
            avg_time = sum(times) / len(times)
            bottlenecks.append((func, avg_time, min(times), max(times)))

    # Sort by average time
    bottlenecks.sort(key=lambda x: x[1], reverse=True)

    # Create bar chart
    functions = [b[0].replace('_', ' ').title() for b in bottlenecks]
    avg_times = [b[1] for b in bottlenecks]
    min_times = [b[2] for b in bottlenecks]
    max_times = [b[3] for b in bottlenecks]

    x = np.arange(len(functions))
    width = 0.25

    bars1 = ax.bar(x - width, min_times, width, label='Min', color='green', alpha=0.7)
    bars2 = ax.bar(x, avg_times, width, label='Average', color='blue', alpha=0.7)
    bars3 = ax.bar(x + width, max_times, width, label='Max', color='red', alpha=0.7)

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 100:  # Only show labels for values > 100ms
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}', ha='center', va='bottom', fontsize=8)

    # Highlight bottlenecks
    if bottlenecks:
        top_bottleneck = bottlenecks[0]
        ax.text(0.5, max_times[0] * 1.1,
               f'🔴 Main Bottleneck: {functions[0]} ({avg_times[0]:.0f}ms avg)',
               ha='center', fontsize=11, fontweight='bold', color='red',
               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    ax.set_xlabel('Function', fontsize=11)
    ax.set_ylabel('Time (milliseconds)', fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(functions, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Add efficiency note
    response_times = stats.get('response_times', [])
    if response_times:
        avg_response = sum(response_times) / len(response_times)
        ax.text(0.95, 0.95, f'Avg Response: {avg_response:.1f}s',
               transform=ax.transAxes, ha='right', va='top',
               fontsize=10, bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

def main():
    """Main execution"""
    print("🎨 Creating Gantt Chart Visualization")
    print("="*60)

    # Load results
    results = load_latest_results()
    if not results:
        return

    # Create visualization
    output_file = create_gantt_chart(results)

    print("="*60)
    print("✅ Visualization complete!")

    return output_file

if __name__ == "__main__":
    main()
