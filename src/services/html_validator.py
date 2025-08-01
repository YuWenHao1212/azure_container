"""
HTML Validator Service.
Validates and cleans HTML for TinyMCE compatibility and security.
"""
import logging
import re
from typing import ClassVar

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HTMLValidator:
    """HTML 驗證和清理服務"""

    # 允許的 HTML 標籤白名單
    ALLOWED_TAGS: ClassVar[set] = {
        'h1', 'h2', 'h3', 'h4', 'p', 'ul', 'li',
        'strong', 'em', 'br', 'a'
    }

    # 允許的屬性
    ALLOWED_ATTRS: ClassVar[dict] = {
        'a': ['href']
    }

    def validate_and_clean(self, html: str) -> str:
        """驗證並清理 HTML"""
        try:
            if not html or not html.strip():
                raise ValueError("Empty HTML content")

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html, 'html.parser')

            # 1. 移除不允許的標籤
            self._remove_disallowed_tags(soup)

            # 2. 清理屬性
            self._clean_attributes(soup)

            # 3. 移除危險內容
            self._remove_dangerous_content(soup)

            # 4. 確保正確的編碼
            cleaned_html = str(soup)

            # 5. 最終驗證
            if not soup.get_text(strip=True):
                raise ValueError("HTML parsing resulted in empty content")

            return cleaned_html

        except Exception as e:
            logger.error(f"HTML validation failed: {e!s}")
            return '<p>Content processing failed - please check the original format</p>'

    def detect_sections(self, html: str) -> dict[str, bool]:
        """檢測履歷中的各個區段"""
        soup = BeautifulSoup(html, 'html.parser')

        return {
            "contact": self._has_contact_info(soup),
            "summary": self._has_summary(soup),
            "skills": self._has_section_h2(soup, "Skills"),
            "experience": self._has_section_h2(soup, "Work Experience"),
            "education": self._has_section_h2(soup, "Education"),
            "projects": self._has_section_h2(soup, "Projects"),
            "certifications": self._has_section_h2(soup, "Certifications")
        }

    def _remove_disallowed_tags(self, soup: BeautifulSoup) -> None:
        """移除不允許的標籤"""
        # 先移除危險標籤及其內容 (script, style 等)
        dangerous_tags = ['script', 'style', 'iframe', 'object', 'embed']
        for tag_name in dangerous_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()  # 完全移除標籤及其內容

        # 再處理其他不允許的標籤 (保留內容)
        for tag in soup.find_all(True):
            if tag.name not in self.ALLOWED_TAGS and tag.name not in dangerous_tags:
                # 保留內容, 只移除標籤
                tag.unwrap()

    def _clean_attributes(self, soup: BeautifulSoup) -> None:
        """清理標籤屬性, 只保留允許的屬性"""
        for tag in soup.find_all(True):
            # 獲取允許的屬性列表
            allowed = self.ALLOWED_ATTRS.get(tag.name, [])

            # 獲取當前標籤的所有屬性
            attrs = dict(tag.attrs)

            # 移除不允許的屬性
            for attr in attrs:
                if attr not in allowed:
                    del tag[attr]

    def _remove_dangerous_content(self, soup: BeautifulSoup) -> None:
        """移除危險內容"""
        # 移除 script 標籤及其內容
        for script in soup.find_all('script'):
            script.decompose()

        # 移除 style 標籤及其內容
        for style in soup.find_all('style'):
            style.decompose()

        # 移除 iframe 等危險標籤
        dangerous_tags = ['iframe', 'object', 'embed', 'form', 'input',
                         'button', 'select', 'textarea', 'canvas', 'svg']
        for tag_name in dangerous_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 清理所有標籤的事件處理器屬性
        for tag in soup.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr.startswith('on'):  # onclick, onload, etc.
                    del tag[attr]

        # 清理 href 中的 javascript:
        for a in soup.find_all('a'):
            if 'href' in a.attrs:
                href = a['href']
                if href and href.lower().startswith('javascript:'):
                    a['href'] = '#'

    def _has_section_h2(self, soup: BeautifulSoup, title: str) -> bool:
        """檢查是否有特定的 h2 標題"""
        h2_tags = soup.find_all('h2')
        return any(h2.get_text().strip() == title for h2 in h2_tags)

    def _has_contact_info(self, soup: BeautifulSoup) -> bool:
        """檢測是否有聯絡資訊"""
        text_content = soup.get_text()
        contact_patterns = [
            r'Email:',
            r'LinkedIn:',
            r'Location:',
            r'Phone:',
            r'mailto:',
            r'linkedin\.com'
        ]
        return any(re.search(pattern, text_content, re.I) for pattern in contact_patterns)

    def _has_summary(self, soup: BeautifulSoup) -> bool:
        """檢測是否有個人摘要"""
        # 檢查是否有名為 "Summary" 或 "Profile" 的 h2 標題
        summary_found = self._has_section_h2(soup, "Summary") or self._has_section_h2(soup, "Profile")
        if summary_found:
            return True

        # 否則尋找 h1 和 h2 之後的第一個 <p> 標籤
        h1 = soup.find('h1')
        h2 = soup.find('h2')

        if h1 and h2:
            # 找 h2 之後的第一個 p 標籤
            next_sibling = h2.find_next_sibling()
            while next_sibling:
                if next_sibling.name == 'p':
                    # 檢查是否像摘要 (長度, 不是聯絡資訊)
                    text = next_sibling.get_text().strip()
                    if (len(text) > 50 and
                        not any(marker in text for marker in ['Email:', 'Location:', 'LinkedIn:', 'Phone:'])):
                        return True
                    break
                elif next_sibling.name == 'h2':
                    # 遇到下一個 h2, 停止搜尋
                    break
                next_sibling = next_sibling.find_next_sibling()

        return False
