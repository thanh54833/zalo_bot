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
    name: str = "content_scraper"
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

    async def _arun(self, urls: List[str]) -> List[dict]:
        """Process a batch of URLs concurrently and return as a list of dicts."""

        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = []
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def bounded_extract(url):
                async with semaphore:
                    return await self._extract_content(session, url)

            for url in urls:
                task = asyncio.create_task(bounded_extract(url))
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            log = {
                "input": {
                    "urls": urls
                },
                "output": {
                    "length": len(results),
                    "length_content": [len(result.content) if result.content is not None else 0 for result in results],
                }
            }
            print("ScraperContentTool -> ", log)

            return [result.dict() for result in results]

    def _run(self, urls: List[str]) -> List[dict]:
        """Sync wrapper for the async run method."""
        return asyncio.run(self._arun(urls))


# --- Standalone Test ---
# python google_agent/tools/scraper_content_tool.py
if __name__ == "__main__":
    import json

    async def test_scraper():
        """Function to test the ScraperContentTool with various URLs."""
        tool = ScraperContentTool()
        test_urls = [
            "https://concung.com/ta-takato/so-sanh-cac-loai-ta-quan-cho-tre-loai-nao-tot-nhat-bv676.html?srsltid=AfmBOopKMQzrIkO-h9-YCTKQSoRJJPdWKvKtHq9q0IsD0Zo6o6fG2qkO",  # Good URL
            "https://concung.com/ta-takato/so-sanh-cac-loai-ta-quan-cho-tre-loai-nao-tot-nhat-bv676.html?srsltid=AfmBOopKMQzrIkO-h9-YCTKQSoRJJPdWKvKtHq9q0IsD0Zo6o6fG2qkO"
        ]

        print("--- Testing ScraperContentTool ---")
        print(f"Scraping {len(test_urls)} URLs...")
        results = await tool._arun(urls=test_urls)

        print("\n--- Results ---")
        print(json.dumps(results, indent=2, ensure_ascii=False))

    asyncio.run(test_scraper())
