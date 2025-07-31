"""
Resume Text Processing Service.
Handles OCR error correction specific to resume formatting.
"""
import logging
import re

logger = logging.getLogger(__name__)


class ResumeTextProcessor:
    """履歷文字處理服務 - 專門處理 OCR 錯誤"""

    # OCR 錯誤修正對照表
    EMAIL_CORRECTIONS = {
        '＠': '@',
        '.c0m': '.com',
        '.c0n': '.com',
        '.con': '.com',
        'gmai1': 'gmail',
        'gmaii': 'gmail',
        'out1ook': 'outlook',
        'outlOOk': 'outlook',
        'yah00': 'yahoo',
        'hotmai1': 'hotmail'
    }

    PHONE_CORRECTIONS = {
        'O': '0',
        'o': '0',
        'I': '1',
        'l': '1',
        'S': '5',
        'Z': '2',
        'B': '8',
        'G': '6'
    }

    # 常見公司/學校名稱修正
    INSTITUTION_CORRECTIONS = {
        'Micr0soft': 'Microsoft',
        'G00gle': 'Google',
        'Amaz0n': 'Amazon',
        'Faceb00k': 'Facebook',
        'App1e': 'Apple',
        'Stanf0rd': 'Stanford',
        'Berke1ey': 'Berkeley'
    }

    def __init__(self):
        self.email_fix_count = 0
        self.phone_fix_count = 0
        self.ocr_error_count = 0
        self.date_fix_count = 0

    def preprocess_ocr_text(self, text: str) -> str:
        """
        預處理 OCR 文字

        只支援新格式：【Type】:Content（每行一個項目）
        """
        # 重置計數器
        self.email_fix_count = 0
        self.phone_fix_count = 0
        self.ocr_error_count = 0
        self.date_fix_count = 0

        # 處理新格式：保留每行結構，只清理內容部分
        lines = text.strip().split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 處理【Type】:Content 格式
            if '】:' in line:
                parts = line.split('】:', 1)
                if len(parts) == 2:
                    type_part = parts[0] + '】'
                    content_part = parts[1].strip()

                    # 對內容部分進行 OCR 錯誤修正
                    content_part = self._fix_email_errors(content_part)
                    content_part = self._fix_phone_errors(content_part)
                    content_part = self._fix_institution_names(content_part)
                    content_part = self._fix_encoding_issues(content_part)

                    cleaned_lines.append(f"{type_part}:{content_part}")
                else:
                    cleaned_lines.append(line)
            else:
                # 不符合格式的行，進行基本清理
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def postprocess_html(self, html: str) -> str:
        """後處理 HTML 內容"""
        # 修正 HTML 中可能仍存在的 OCR 錯誤
        html = self._fix_email_errors(html)
        html = self._fix_phone_errors(html)
        html = self._standardize_dates(html)

        return html

    def _fix_email_errors(self, text: str) -> str:
        """修正 email 相關的 OCR 錯誤"""
        original_text = text

        # 先處理特定的錯誤對照
        for wrong, correct in self.EMAIL_CORRECTIONS.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                self.email_fix_count += 1

        # 使用正則表達式修正 email 格式
        # 匹配可能的 email 模式，包括錯誤的 @ 符號
        email_pattern = r'([a-zA-Z0-9._%+-]+)[@＠]([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        matches = re.findall(email_pattern, text)

        for match in matches:
            old_email = f"{match[0]}@{match[1]}"
            # 確保使用正確的 @ 符號
            new_email = f"{match[0]}@{match[1]}"
            if old_email != new_email:
                text = text.replace(old_email, new_email)
                self.email_fix_count += 1

        if text != original_text:
            self.ocr_error_count += 1

        return text

    def _fix_phone_errors(self, text: str) -> str:
        """修正電話號碼相關的 OCR 錯誤"""
        # 尋找可能的電話號碼模式
        # 支援多種格式：+1 (123) 456-7890, 123-456-7890, etc.
        phone_patterns = [
            # 國際格式：+1-555-123-4567, +86 138 0000 0000
            r'\+[0-9IOl]{1,3}[\s.-]?[0-9IOl]{3,4}[\s.-]?[0-9IOl]{3,4}[\s.-]?[0-9IOl]{3,4}',
            # 基本格式：555-123-4567, 555.123.4567
            r'[0-9IOl]{3}[\s.-][0-9IOl]{3}[\s.-][0-9IOl]{4}',
            # 帶括號格式：(408) 555-0123
            r'\([0-9IOl]{3}\)\s*[0-9IOl]{3}[\s.-][0-9IOl]{4}',
            # 更寬鬆的格式來捕捉各種變化
            r'[\+\(]?[0-9IOl]{1,4}[\)\s.-]?[0-9IOl]{3,4}[\s.-]?[0-9IOl]{3,4}[\s.-]?[0-9IOl]{3,4}'
        ]

        for pattern in phone_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                phone = match.group()
                fixed_phone = phone

                # 修正常見的 OCR 錯誤 - 字母到數字的轉換
                fixed_phone = fixed_phone.replace('O', '0')
                fixed_phone = fixed_phone.replace('o', '0')
                fixed_phone = fixed_phone.replace('I', '1')
                fixed_phone = fixed_phone.replace('l', '1')

                # 修正其他常見錯誤
                for wrong, correct in self.PHONE_CORRECTIONS.items():
                    if wrong in fixed_phone:
                        fixed_phone = fixed_phone.replace(wrong, correct)

                if phone != fixed_phone:
                    text = text.replace(phone, fixed_phone)
                    self.phone_fix_count += 1

        return text

    def _fix_institution_names(self, text: str) -> str:
        """修正常見機構名稱的 OCR 錯誤"""
        for wrong, correct in self.INSTITUTION_CORRECTIONS.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                self.ocr_error_count += 1

        return text

    def _fix_encoding_issues(self, text: str) -> str:
        """修正編碼問題"""
        # 移除常見的亂碼字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        # 修正常見的編碼錯誤
        encoding_fixes = {
            'â€™': "'",
            'â€œ': '"',
            'â€': '"',
            'â€"': '-',
            'Ã©': 'é',
            'Ã¨': 'è',
            'Ã ': 'à'
        }

        for wrong, correct in encoding_fixes.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                self.ocr_error_count += 1

        return text

    def _standardize_dates(self, text: str) -> str:
        """標準化日期格式為 mmm YYYY"""
        # 匹配多種日期格式並轉換為標準格式
        date_patterns = [
            # 01/2023, 1/2023
            (r'\b(\d{1,2})/(\d{4})\b', self._convert_numeric_date),
            # 2023/01, 2023/1
            (r'\b(\d{4})/(\d{1,2})\b', self._convert_yyyy_mm_date),
            # 2023-01, 2023-1
            (r'\b(\d{4})-(\d{1,2})\b', self._convert_iso_date),
            # January 2023, Jan 2023
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', self._convert_full_month),
            # Sept 2023, Oct. 2023 等縮寫格式
            (r'\b(Jan\.?|Feb\.?|Mar\.?|Apr\.?|May\.?|Jun\.?|Jul\.?|Aug\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)\s+(\d{4})\b', self._convert_abbrev_month),
            # 01-2023, 1-2023
            (r'\b(\d{1,2})-(\d{4})\b', self._convert_numeric_date)
        ]

        for pattern, converter in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                old_date = match.group()
                new_date = converter(match)
                if old_date != new_date:
                    text = text.replace(old_date, new_date)
                    self.date_fix_count += 1

        return text

    def _convert_numeric_date(self, match) -> str:
        """轉換數字日期格式 (01/2023) 為 Jan 2023"""
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        try:
            month = int(match.group(1))
            year = match.group(2)
            if 1 <= month <= 12:
                return f"{month_names[month-1]} {year}"
        except (ValueError, IndexError):
            pass
        return match.group()

    def _convert_yyyy_mm_date(self, match) -> str:
        """轉換 YYYY/MM 日期格式 (2023/01) 為 Jan 2023"""
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        try:
            year = match.group(1)
            month = int(match.group(2))
            if 1 <= month <= 12:
                return f"{month_names[month-1]} {year}"
        except (ValueError, IndexError):
            pass
        return match.group()

    def _convert_iso_date(self, match) -> str:
        """轉換 ISO 日期格式 (2023-01) 為 Jan 2023"""
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        try:
            year = match.group(1)
            month = int(match.group(2))
            if 1 <= month <= 12:
                return f"{month_names[month-1]} {year}"
        except (ValueError, IndexError):
            pass
        return match.group()

    def _convert_full_month(self, match) -> str:
        """轉換完整月份名稱為縮寫"""
        month_map = {
            'january': 'Jan', 'february': 'Feb', 'march': 'Mar',
            'april': 'Apr', 'may': 'May', 'june': 'Jun',
            'july': 'Jul', 'august': 'Aug', 'september': 'Sep',
            'october': 'Oct', 'november': 'Nov', 'december': 'Dec'
        }
        month = match.group(1).lower()
        year = match.group(2)
        return f"{month_map.get(month, match.group(1))} {year}"

    def _convert_abbrev_month(self, match) -> str:
        """標準化月份縮寫"""
        month_map = {
            'jan': 'Jan', 'jan.': 'Jan',
            'feb': 'Feb', 'feb.': 'Feb',
            'mar': 'Mar', 'mar.': 'Mar',
            'apr': 'Apr', 'apr.': 'Apr',
            'may': 'May', 'may.': 'May',
            'jun': 'Jun', 'jun.': 'Jun',
            'jul': 'Jul', 'jul.': 'Jul',
            'aug': 'Aug', 'aug.': 'Aug',
            'sept': 'Sep', 'sept.': 'Sep',
            'oct': 'Oct', 'oct.': 'Oct',
            'nov': 'Nov', 'nov.': 'Nov',
            'dec': 'Dec', 'dec.': 'Dec'
        }
        month = match.group(1).lower()
        year = match.group(2)
        return f"{month_map.get(month, match.group(1))} {year}"

    def get_correction_stats(self) -> dict[str, int]:
        """獲取修正統計"""
        return {
            "ocr_errors": self.ocr_error_count,
            "email_fixes": self.email_fix_count,
            "phone_fixes": self.phone_fix_count,
            "date_standardization": self.date_fix_count
        }
