import asyncio
from typing import List, Optional, Type

import aiohttp
import trafilatura
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class ScraperInput(BaseModel):
    urls: List[str] = Field(description="A list of URLs to scrape content from.")


class ScrapedContent(BaseModel):
    url: str
    content: Optional[str]
    title: Optional[str]
    success: bool


class ScraperContentTool(BaseTool):
    name: str = "scraper_content"
    description: str = "Extracts the main content and title from a list of URLs. Useful for getting detailed information from a webpage after finding it with a search."
    args_schema: Type[BaseModel] = ScraperInput

    max_concurrent: int = 10
    headers: dict = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

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

    def _run(
            self,
            urls: List[str]
    ) -> str:
        """Process a batch of URLs concurrently and return a formatted string."""
        results = asyncio.run(self._arun(urls=urls))
        return self._format_results(results)

    async def _arun(
            self,
            urls: List[str],
    ) -> List[dict]:
        """Process a batch of URLs concurrently and return as a list of dicts."""
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
