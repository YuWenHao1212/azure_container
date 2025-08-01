"""
改進的繁體中文檢測器
解決 langdetect 經常誤判繁體為簡體的問題

Author: Claude Code
Date: 2025-07-03
"""

import logging
from typing import ClassVar

logger = logging.getLogger(__name__)


class ImprovedChineseDetector:
    """
    改進的中文變體檢測器, 更準確區分繁體和簡體中文
    """

    # 擴展的繁體中文特徵字符集 (基於台灣職場常用詞彙)
    TRADITIONAL_CHARS: ClassVar[set] = set(
        '繁體語機業資訊軟體開發設計測試資料庫網路計劃團隊責任工作經驗技能專業證照學歷'
        '維護系統候選尋找精通熟悉需要具備負責優秀歡迎薪酬福利環境條件職缺應徵履歷'
        '產業領域創新願景價值觀國際視野溝通協調執行專案管理分析報告決策建議方案'
        '績效評估晉升機會訓練課程認證資格學習成長挑戰機會彈性工時遠端辦公獎金'
    )

    # 簡體中文特徵字符集
    SIMPLIFIED_CHARS: ClassVar[set] = set(
        '简体语机业资讯软体开发设计测试资料库网络计划团队责任工作经验技能专业证照学历'
        '维护系统候选寻找精通熟悉需要具备负责优秀欢迎薪酬福利环境条件职缺应征履历'
        '产业领域创新愿景价值观国际视野沟通协调执行专案管理分析报告决策建议方案'
        '绩效评估晋升机会训练课程认证资格学习成长挑战机会弹性工时远端办公奖金'
    )

    # 繁體專有詞彙 (這些詞彙組合強烈暗示繁體中文)
    TRADITIONAL_PHRASES: ClassVar[set] = {
        '程式設計', '資料庫', '軟體工程', '網路安全', '雲端運算', '機器學習',
        '專案管理', '系統分析', '使用者介面', '資訊安全', '品質保證', '技術支援',
        '業務開發', '客戶服務', '人力資源', '財務會計', '行銷企劃', '產品經理',
        '薪資福利', '工作環境', '職涯發展', '團隊合作', '溝通協調', '問題解決'
    }

    # 簡體專有詞彙
    SIMPLIFIED_PHRASES: ClassVar[set] = {
        '程序设计', '数据库', '软件工程', '网络安全', '云端运算', '机器学习',
        '项目管理', '系统分析', '用户界面', '信息安全', '质量保证', '技术支持',
        '业务开发', '客户服务', '人力资源', '财务会计', '营销企划', '产品经理',
        '薪资福利', '工作环境', '职业发展', '团队合作', '沟通协调', '问题解决'
    }

    def detect_chinese_variant(self, text: str) -> tuple[str, float]:
        """
        檢測中文變體 (繁體或簡體)

        Args:
            text: 要檢測的文本

        Returns:
            Tuple[語言代碼, 信心分數]
            - 'zh-TW': 繁體中文
            - 'zh-CN': 簡體中文
        """
        if not text:
            return 'zh-CN', 0.5

        # 1. 字符級別檢測
        text_chars = set(text)
        traditional_char_count = len(text_chars.intersection(self.TRADITIONAL_CHARS))
        simplified_char_count = len(text_chars.intersection(self.SIMPLIFIED_CHARS))

        # 2. 詞彙級別檢測
        traditional_phrase_count = sum(1 for phrase in self.TRADITIONAL_PHRASES if phrase in text)
        simplified_phrase_count = sum(1 for phrase in self.SIMPLIFIED_PHRASES if phrase in text)

        # 3. 計算總分
        traditional_score = traditional_char_count * 2 + traditional_phrase_count * 5
        simplified_score = simplified_char_count * 2 + simplified_phrase_count * 5

        # 4. 計算中文字符總數
        chinese_char_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')

        logger.debug(
            f"Chinese variant detection - "
            f"Trad chars: {traditional_char_count}, Simp chars: {simplified_char_count}, "
            f"Trad phrases: {traditional_phrase_count}, Simp phrases: {simplified_phrase_count}, "
            f"Total Chinese: {chinese_char_count}"
        )

        # 5. 判定邏輯
        if traditional_score > simplified_score:
            # 計算信心分數
            if traditional_score > 0:
                confidence = min(0.95, 0.8 + (traditional_phrase_count * 0.05))
            else:
                confidence = 0.85
            return 'zh-TW', confidence

        elif simplified_score > traditional_score:
            confidence = min(0.95, 0.8 + (simplified_phrase_count * 0.05))
            return 'zh-CN', confidence

        else:
            # 分數相同, 檢查其他因素
            # 如果有大量中文字符但沒有明確指標, 預設為繁體 (針對台灣市場)
            if chinese_char_count >= 20:
                return 'zh-TW', 0.75
            else:
                return 'zh-CN', 0.6

    def is_mixed_chinese_english(self, text: str) -> bool:
        """
        檢測是否為中英混合文本

        Args:
            text: 要檢測的文本

        Returns:
            是否為中英混合
        """
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
        has_english = any('a' <= char.lower() <= 'z' for char in text)

        if has_chinese and has_english:
            chinese_ratio = sum(1 for c in text if '\u4e00' <= c <= '\u9fff') / len(text)
            english_ratio = sum(1 for c in text if c.isalpha() and ord(c) < 128) / len(text)

            # 如果中英文都佔有一定比例, 認為是混合文本
            return chinese_ratio > 0.1 and english_ratio > 0.1

        return False

    def get_language_features(self, text: str) -> dict:
        """
        獲取語言特徵詳細信息 (用於調試和分析)

        Args:
            text: 要分析的文本

        Returns:
            包含各種語言特徵的字典
        """
        text_chars = set(text)

        features = {
            'total_length': len(text),
            'chinese_char_count': sum(1 for c in text if '\u4e00' <= c <= '\u9fff'),
            'english_char_count': sum(1 for c in text if c.isalpha() and ord(c) < 128),
            'traditional_char_matches': len(text_chars.intersection(self.TRADITIONAL_CHARS)),
            'simplified_char_matches': len(text_chars.intersection(self.SIMPLIFIED_CHARS)),
            'traditional_phrases': [p for p in self.TRADITIONAL_PHRASES if p in text],
            'simplified_phrases': [p for p in self.SIMPLIFIED_PHRASES if p in text],
            'is_mixed': self.is_mixed_chinese_english(text)
        }

        # 計算比例
        if features['chinese_char_count'] > 0:
            features['chinese_ratio'] = features['chinese_char_count'] / features['total_length']
        else:
            features['chinese_ratio'] = 0.0

        if features['english_char_count'] > 0:
            features['english_ratio'] = features['english_char_count'] / features['total_length']
        else:
            features['english_ratio'] = 0.0

        return features
