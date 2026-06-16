import re
from html.parser import HTMLParser

import httpx

from app.models import CrawlResult


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = False
        self.title = ""
        self._in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True
        if tag == "title":
            self._in_title = True
        if tag in {"p", "div", "li", "br", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if not clean or self._skip:
            return
        if self._in_title:
            self.title += clean
        self.parts.append(clean)

    def text(self) -> str:
        text = "\n".join(self.parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def crawl_url(url: str) -> CrawlResult:
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 BaoyanAgentBot/0.1",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            response.raise_for_status()
        parser = _TextExtractor()
        parser.feed(response.text)
        content = parser.text()
        title = parser.title.strip() or url
        if len(content) < 80:
            return CrawlResult(url=url, status="failed", title=title, error="网页正文过短，建议改用文本粘贴")
        return CrawlResult(url=url, status="success", title=title, content=content[:30000])
    except httpx.HTTPError as exc:
        return CrawlResult(url=url, status="failed", error=f"网页抓取失败: {exc.__class__.__name__}")
