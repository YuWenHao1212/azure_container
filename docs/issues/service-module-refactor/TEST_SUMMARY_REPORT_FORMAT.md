# 測試總結報告格式規範

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-07
- **維護者**: 測試團隊
- **目的**: 定義服務層測試的視覺化報告格式

## 1. 報告結構總覽

### 1.1 報告組成部分
1. **標題區** - 測試名稱和執行時間
2. **統計摘要** - 整體成功率和關鍵指標
3. **分布矩陣** - 各模組測試分布和結果
4. **進度視圖** - 視覺化進度條
5. **詳細結果** - 失敗測試詳情
6. **執行資訊** - 環境和配置資訊

### 1.2 輸出格式
- **終端輸出**: ANSI 彩色文字格式
- **檔案輸出**: Markdown 格式報告
- **CI/CD 輸出**: JUnit XML 格式

## 2. 統計摘要格式

### 2.1 標準格式
```
╔══════════════════════════════════════════════════════════════════╗
║                    服務層模組測試執行報告                          ║
╠══════════════════════════════════════════════════════════════════╣
║ 執行時間: 2025-08-07 14:30:25                                     ║
║ 總耗時: 3.42 秒                                                   ║
╚══════════════════════════════════════════════════════════════════╝

📊 測試統計摘要
════════════════════════════════════════════════════════════════════
總測試數: 48
通過: 42 ✅
失敗: 6 ❌
跳過: 0 ⏩
成功率: 87.5%
平均執行時間: 71.25ms
```

### 2.2 彩色編碼規則
- **綠色 (✅)**: 測試通過
- **紅色 (❌)**: 測試失敗
- **黃色 (⚠️)**: 部分失敗或警告
- **灰色 (⏩)**: 跳過的測試
- **藍色 (🔵)**: 資訊性內容

## 3. 測試分布矩陣

### 3.1 標準表格格式
```
📊 測試分布與結果矩陣
═══════════════════════════════════════════════════════════════════════════════
| 測試模組         | 單元測試      | 整合測試      | 效能測試      | 總計         | 狀態 |
|------------------|---------------|---------------|---------------|--------------|------|
| 語言檢測         | 15 ✅(15/0)   | -             | -             | 15 ✅(15/0)  | ✅   |
| Prompt管理       | 15 ⚠️(14/1)   | -             | -             | 15 ⚠️(14/1)  | ⚠️   |
| 關鍵字服務       | 10 ❌(5/5)    | -             | -             | 10 ❌(5/5)   | ❌   |
| LLM Factory      | 8  ✅(8/0)    | -             | -             | 8  ✅(8/0)   | ✅   |
|------------------|---------------|---------------|---------------|--------------|------|
| **總計**         | 48 (42/6)     | 0             | 0             | 48 (42/6)    | ⚠️   |
| **成功率**       | 87.5%         | -             | -             | 87.5%        |      |
═══════════════════════════════════════════════════════════════════════════════
```

### 3.2 數字格式說明
- `15 ✅(15/0)` = 總數 狀態圖標(通過數/失敗數)
- `10 ❌(5/5)` = 10個測試，5個通過，5個失敗
- `15 ⚠️(14/1)` = 15個測試，14個通過，1個失敗（部分失敗）

### 3.3 狀態判定規則
- **✅ 完全通過**: 失敗數 = 0
- **⚠️ 部分失敗**: 0 < 失敗數 < 總數
- **❌ 完全失敗**: 失敗數 >= 總數的50%
- **⏩ 全部跳過**: 所有測試被跳過

## 4. 進度條視圖

### 4.1 整體進度條
```
📈 整體測試進度
[████████████████████████████████████░░░░░] 87.5% (42/48 passed)
```

### 4.2 模組進度條
```
📊 各模組測試進度
────────────────────────────────────────────────────────────────────
語言檢測:    [████████████████████████████████████████] 100% ✅ (15/15)
Prompt管理:  [█████████████████████████████████████░░░]  93% ⚠️ (14/15)
關鍵字服務:  [████████████████████░░░░░░░░░░░░░░░░░░░]  50% ❌ (5/10)
LLM Factory: [████████████████████████████████████████] 100% ✅ (8/8)
────────────────────────────────────────────────────────────────────
```

### 4.3 進度條字元
- `█` - 完成部分
- `░` - 未完成部分
- 每個進度條固定40個字元寬度

## 5. 詳細結果報告

### 5.1 失敗測試詳情
```
❌ 失敗測試詳情
════════════════════════════════════════════════════════════════════
[FAIL] SVC-PM-007-UT: 參數驗證 (>200字元)
  模組: test_unified_prompt_service.py
  錯誤: AssertionError: Expected validation error for short input
  耗時: 15ms
  
[FAIL] SVC-KW-005-UT: 併發請求處理
  模組: test_keyword_service_integration.py
  錯誤: TimeoutError: Request exceeded 100ms timeout
  耗時: 105ms

[FAIL] SVC-KW-006-UT: 資源池管理
  模組: test_keyword_service_integration.py
  錯誤: ResourceExhaustedError: Pool limit exceeded
  耗時: 45ms
════════════════════════════════════════════════════════════════════
```

### 5.2 警告訊息
```
⚠️ 測試警告
────────────────────────────────────────────────────────────────────
• 3 個測試執行時間超過 80ms（接近 100ms 限制）
• 2 個測試使用了 deprecated fixtures
• 1 個測試有 flaky 標記但未失敗
────────────────────────────────────────────────────────────────────
```

## 6. 執行資訊

### 6.1 環境資訊
```
🔧 執行環境
────────────────────────────────────────────────────────────────────
Python版本: 3.11.0
測試框架: pytest 7.4.0
覆蓋率工具: coverage 7.3.0
執行平台: Darwin 24.4.0
並行執行: 4 workers
Mock策略: 100% mocked (no real API calls)
────────────────────────────────────────────────────────────────────
```

### 6.2 配置資訊
```
⚙️ 測試配置
────────────────────────────────────────────────────────────────────
最大執行時間: 100ms/test
總超時時間: 5 seconds
測試資料長度: >200 chars
語言支援: en, zh-TW
Mock模式: Full isolation
────────────────────────────────────────────────────────────────────
```

## 7. Shell 腳本實作

### 7.1 報告生成函數
```bash
#!/bin/bash

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生成測試摘要
generate_summary() {
    local total=$1
    local passed=$2
    local failed=$3
    local skipped=$4
    local success_rate=$(echo "scale=1; $passed * 100 / $total" | bc)
    
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                    服務層模組測試執行報告                          ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║ 執行時間: $(date '+%Y-%m-%d %H:%M:%S')                           ║"
    echo "║ 總耗時: $ELAPSED_TIME 秒                                          ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 測試統計摘要"
    echo "════════════════════════════════════════════════════════════════════"
    echo "總測試數: $total"
    echo -e "通過: $passed ${GREEN}✅${NC}"
    echo -e "失敗: $failed ${RED}❌${NC}"
    echo -e "跳過: $skipped ${YELLOW}⏩${NC}"
    echo "成功率: ${success_rate}%"
}

# 生成分布矩陣
generate_matrix() {
    echo "📊 測試分布與結果矩陣"
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo "| 測試模組         | 單元測試      | 整合測試      | 效能測試      | 總計         | 狀態 |"
    echo "|------------------|---------------|---------------|---------------|--------------|------|"
    
    # 為每個模組生成行
    for module in "語言檢測" "Prompt管理" "關鍵字服務" "LLM Factory"; do
        generate_module_row "$module"
    done
    
    echo "|------------------|---------------|---------------|---------------|--------------|------|"
    echo "| **總計**         | $UNIT_TOTAL   | $INT_TOTAL    | $PERF_TOTAL   | $TOTAL       | $STATUS |"
    echo "| **成功率**       | $UNIT_RATE%   | $INT_RATE%    | $PERF_RATE%   | $TOTAL_RATE% |      |"
    echo "═══════════════════════════════════════════════════════════════════════════════"
}

# 生成進度條
generate_progress_bar() {
    local percent=$1
    local width=40
    local filled=$(echo "scale=0; $percent * $width / 100" | bc)
    local empty=$((width - filled))
    
    printf "["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "]"
}

# 生成模組進度視圖
generate_progress_view() {
    echo "📊 各模組測試進度"
    echo "────────────────────────────────────────────────────────────────────"
    
    for module in "${!MODULE_RESULTS[@]}"; do
        local result="${MODULE_RESULTS[$module]}"
        local passed=$(echo "$result" | cut -d'/' -f1)
        local total=$(echo "$result" | cut -d'/' -f2)
        local percent=$(echo "scale=0; $passed * 100 / $total" | bc)
        
        printf "%-12s: " "$module"
        generate_progress_bar "$percent"
        
        if [ "$percent" -eq 100 ]; then
            echo -e " ${percent}% ${GREEN}✅${NC} ($passed/$total)"
        elif [ "$percent" -ge 50 ]; then
            echo -e " ${percent}% ${YELLOW}⚠️${NC} ($passed/$total)"
        else
            echo -e " ${percent}% ${RED}❌${NC} ($passed/$total)"
        fi
    done
    echo "────────────────────────────────────────────────────────────────────"
}
```

### 7.2 主執行腳本
```bash
#!/bin/bash
# run_service_modules_tests.sh

# 執行測試並生成報告
run_tests_with_report() {
    START_TIME=$(date +%s)
    
    # 執行測試
    pytest test/unit/services/ \
        --tb=short \
        --junit-xml=test-results.xml \
        --cov=src/services \
        --cov-report=term-missing \
        > test_output.log 2>&1
    
    TEST_EXIT_CODE=$?
    END_TIME=$(date +%s)
    ELAPSED_TIME=$((END_TIME - START_TIME))
    
    # 解析結果
    parse_test_results
    
    # 生成報告
    clear
    generate_summary "$TOTAL" "$PASSED" "$FAILED" "$SKIPPED"
    echo ""
    generate_matrix
    echo ""
    generate_progress_view
    
    # 顯示失敗詳情
    if [ "$FAILED" -gt 0 ]; then
        echo ""
        show_failure_details
    fi
    
    # 顯示執行資訊
    echo ""
    show_execution_info
    
    # 保存報告
    save_report_to_file
    
    return $TEST_EXIT_CODE
}

# 執行
run_tests_with_report
```

## 8. Markdown 報告格式

### 8.1 檔案結構
```markdown
# 服務層模組測試報告

**執行時間**: 2025-08-07 14:30:25  
**總耗時**: 3.42 秒  
**執行環境**: Python 3.11.0 / Darwin 24.4.0

## 測試統計

| 指標 | 數值 |
|------|------|
| 總測試數 | 48 |
| 通過 | 42 ✅ |
| 失敗 | 6 ❌ |
| 跳過 | 0 ⏩ |
| 成功率 | 87.5% |

## 模組測試結果

| 模組 | 單元測試 | 整合測試 | 效能測試 | 總計 | 成功率 |
|------|----------|----------|----------|------|---------|
| 語言檢測 | 15/15 | - | - | 15/15 | 100% ✅ |
| Prompt管理 | 14/15 | - | - | 14/15 | 93.3% ⚠️ |
| 關鍵字服務 | 5/10 | - | - | 5/10 | 50% ❌ |
| LLM Factory | 8/8 | - | - | 8/8 | 100% ✅ |

## 失敗測試詳情

### SVC-PM-007-UT: 參數驗證
- **檔案**: test_unified_prompt_service.py:157
- **錯誤**: AssertionError
- **訊息**: Expected validation error for input less than 200 characters

### SVC-KW-005-UT: 併發請求處理
- **檔案**: test_keyword_service_integration.py:234
- **錯誤**: TimeoutError
- **訊息**: Request exceeded 100ms timeout limit

## 測試覆蓋率

- **行覆蓋率**: 88.5%
- **分支覆蓋率**: 82.3%
- **函數覆蓋率**: 91.0%
```

## 9. JUnit XML 格式

### 9.1 標準 JUnit 結構
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Service Module Tests" tests="48" failures="6" errors="0" time="3.42">
  <testsuite name="Language Detection Service" tests="15" failures="0" errors="0" time="0.95">
    <testcase classname="test_language_detection_service" name="test_SVC_LD_001_pure_english" time="0.045">
      <system-out>Pure English detection passed</system-out>
    </testcase>
    <!-- More test cases -->
  </testsuite>
  
  <testsuite name="Prompt Management Service" tests="15" failures="1" errors="0" time="1.12">
    <testcase classname="test_unified_prompt_service" name="test_SVC_PM_007_validation" time="0.015">
      <failure message="AssertionError: Expected validation error">
        Traceback (most recent call last):
          File "test_unified_prompt_service.py", line 157
          AssertionError: Expected validation error for short input
      </failure>
    </testcase>
    <!-- More test cases -->
  </testsuite>
</testsuites>
```

## 10. 視覺化改進提案

### 10.1 互動式 HTML 報告
```html
<!DOCTYPE html>
<html>
<head>
    <title>服務層測試報告</title>
    <style>
        .progress-bar {
            width: 100%;
            background-color: #f0f0f0;
            border-radius: 5px;
            overflow: hidden;
        }
        .progress-fill {
            height: 30px;
            background: linear-gradient(90deg, #4CAF50, #45a049);
            text-align: center;
            line-height: 30px;
            color: white;
            transition: width 0.5s ease;
        }
        .test-pass { color: #4CAF50; }
        .test-fail { color: #f44336; }
        .test-skip { color: #ff9800; }
    </style>
</head>
<body>
    <h1>服務層模組測試報告</h1>
    
    <div class="summary-card">
        <h2>測試統計</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: 87.5%">87.5%</div>
        </div>
        <p>通過: <span class="test-pass">42 ✅</span></p>
        <p>失敗: <span class="test-fail">6 ❌</span></p>
        <p>跳過: <span class="test-skip">0 ⏩</span></p>
    </div>
    
    <!-- Interactive charts using Chart.js -->
    <canvas id="testChart"></canvas>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // 動態圖表生成
        const ctx = document.getElementById('testChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['通過', '失敗', '跳過'],
                datasets: [{
                    data: [42, 6, 0],
                    backgroundColor: ['#4CAF50', '#f44336', '#ff9800']
                }]
            }
        });
    </script>
</body>
</html>
```

### 10.2 終端動畫效果
```python
#!/usr/bin/env python3
"""
animated_test_report.py - 動畫測試報告生成器
"""

import time
import sys
from colorama import init, Fore, Style

init(autoreset=True)

def animated_progress_bar(percent, width=40):
    """生成動畫進度條"""
    for i in range(0, int(percent * width / 100) + 1):
        filled = '█' * i
        empty = '░' * (width - i)
        bar = f"[{filled}{empty}]"
        percentage = f"{int(i * 100 / width)}%"
        
        sys.stdout.write(f"\r{bar} {percentage}")
        sys.stdout.flush()
        time.sleep(0.02)
    
    # 最終狀態
    if percent == 100:
        print(f" {Fore.GREEN}✅")
    elif percent >= 50:
        print(f" {Fore.YELLOW}⚠️")
    else:
        print(f" {Fore.RED}❌")

def generate_animated_report(results):
    """生成動畫報告"""
    print(Fore.CYAN + "=" * 70)
    print(Fore.CYAN + "                    服務層模組測試執行報告")
    print(Fore.CYAN + "=" * 70)
    
    for module, data in results.items():
        print(f"\n{Fore.BLUE}{module}:")
        animated_progress_bar(data['success_rate'])
    
    print(f"\n{Fore.GREEN}測試完成！")

# 使用範例
if __name__ == "__main__":
    test_results = {
        "語言檢測": {"success_rate": 100},
        "Prompt管理": {"success_rate": 93},
        "關鍵字服務": {"success_rate": 50},
        "LLM Factory": {"success_rate": 100}
    }
    
    generate_animated_report(test_results)
```

## 11. CI/CD 整合

### 11.1 GitHub Actions 輸出
```yaml
- name: Run Service Module Tests
  run: |
    ./test/scripts/run_service_modules_tests.sh
  
- name: Upload Test Report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-report
    path: |
      test-results.xml
      test-report.html
      coverage.xml

- name: Comment PR with Results
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const report = fs.readFileSync('test-report.md', 'utf8');
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: report
      });
```

### 11.2 測試狀態徽章
```markdown
![Tests](https://img.shields.io/badge/tests-42%20passed%2C%206%20failed-yellow)
![Coverage](https://img.shields.io/badge/coverage-88.5%25-brightgreen)
![Duration](https://img.shields.io/badge/duration-3.42s-blue)
```

## 12. 使用指南

### 12.1 生成基本報告
```bash
# 執行測試並生成文字報告
./test/scripts/run_service_modules_tests.sh

# 生成 HTML 報告
./test/scripts/run_service_modules_tests.sh --html

# 生成所有格式報告
./test/scripts/run_service_modules_tests.sh --all-formats
```

### 12.2 自訂報告選項
```bash
# 只顯示失敗測試
./test/scripts/run_service_modules_tests.sh --failures-only

# 顯示詳細進度
./test/scripts/run_service_modules_tests.sh --verbose

# 生成覆蓋率報告
./test/scripts/run_service_modules_tests.sh --with-coverage
```

## 13. 維護指南

### 13.1 更新報告格式
1. 修改對應的格式模板
2. 更新生成函數
3. 測試新格式輸出
4. 更新文檔

### 13.2 新增報告類型
1. 定義新的格式規範
2. 實作生成器函數
3. 整合到主腳本
4. 新增使用範例

---

**文檔維護**:
- 最後更新：2025-08-07
- 審查週期：每個Sprint
- 負責人：測試團隊