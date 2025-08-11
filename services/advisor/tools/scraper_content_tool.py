import asyncio
import logging
from typing import List, Optional, Type, Dict, Any

import aiohttp
import trafilatura
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .base_configurable_tool import BaseConfigurableTool

# Set up logging
logger = logging.getLogger(__name__)


class ScrapedContent(BaseModel):
    url: str
    content: Optional[str]
    title: Optional[str]
    success: bool


class ScraperContentTool(BaseConfigurableTool):
    """
    Scraper Content Tool - HOÀN TOÀN LẤY TỪ CONFIG!
    NGHIÊM CẤM hard-code bất kỳ thông tin gì!
    """
    
    def __init__(self, tool_config: Dict[str, Any]):
        # ✅ GỌI CONSTRUCTOR CHA VỚI CONFIG
        super().__init__(tool_config)
        
        # ✅ VALIDATE DEPENDENCIES
        self._validate_dependencies()
        
        # ✅ SET CONFIGURABLE PROPERTIES
        self.max_concurrent = tool_config.get("max_concurrent", 10)
        self.headers = tool_config.get("headers", {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _validate_dependencies(self):
        """Kiểm tra dependencies có sẵn không"""
        try:
            import aiohttp
            import trafilatura
            logger.debug("✅ aiohttp and trafilatura dependencies available")
        except ImportError as e:
            logger.warning(f"⚠️ Dependencies not available: {e}")
    
    async def _extract_content(self, session: aiohttp.ClientSession, url: str) -> ScrapedContent:
        """Extract clean content from URL using async request"""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return ScrapedContent(url=url, content=None, title=None, success=False)

                html_content = await response.text()

                # Extract content and metadata
                content = trafilatura.extract(html_content, include_comments=False)
                metadata = trafilatura.extract_metadata(html_content)
                title = metadata.title if metadata else None

                if content and len(content) > 200:
                    return ScrapedContent(
                        url=url,
                        content=content,
                        title=title,
                        success=True
                    )

                return ScrapedContent(url=url, content=None, title=None, success=False)

        except Exception as e:
            return ScrapedContent(url=url, content=f"Error scraping: {e}", title=None, success=False)

    def _run(self, **kwargs) -> str:
        """Process a batch of URLs concurrently and return a formatted string."""
        # ✅ LẤY PARAMETERS TỪ CONFIG - KHÔNG HARD-CODE!
        urls = kwargs.get("urls")
        if not urls:
            return "URLs parameter is required"
            
        results = asyncio.run(self._arun(urls=urls))
        return self._format_results(results)

    async def _arun(self, **kwargs) -> List[dict]:
        """Process a batch of URLs concurrently and return as a list of dicts."""
        # ✅ LẤY PARAMETERS TỪ CONFIG - KHÔNG HARD-CODE!
        urls = kwargs.get("urls", [])
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = [self._extract_content(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            return [result.dict() for result in results]

    def _format_results(self, results: List[dict]) -> str:
        """Format the results into a single string."""
        if not results:
            return "No content was scraped."

        formatted_output = []
        for res in results:
            if res['success']:
                content_preview = res.get('content', '')[:500]
                formatted_output.append(
                    f"URL: {res['url']}\n"
                    f"Title: {res.get('title', 'N/A')}\n"
                    f"Content: {content_preview}...\n"
                )
            else:
                formatted_output.append(
                    f"URL: {res['url']}\n"
                    f"Error: Failed to scrape content.\n"
                )
        return "\n---\n".join(formatted_output)
