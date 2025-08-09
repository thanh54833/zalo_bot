import asyncio
import logging
from typing import Dict, List, Type, Union

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# Set up logging
logger = logging.getLogger(__name__)


class GoogleSearchInput(BaseModel):
    query: str = Field(description="The search query.")
    num_results: int = Field(5, description="Number of results to return.")
    lang: str = Field("vi", description="Language for search results.")


class SearchItem(BaseModel):
    title: str
    url: str
    description: str


class GoogleSearchTool(BaseTool):
    name: str = "google_search"
    description: str = (
        "A search engine to find information on the web. "
    )
    args_schema: Type[BaseModel] = GoogleSearchInput

    def _search_sync(self, query: str, num_results: int, lang: str) -> Union[List[SearchItem], str]:
        """Performs a single synchronous Google search."""
        from googlesearch import search
        results = []
        try:
            search_results = search(query, num_results=num_results, lang=lang, advanced=True)
            for item in search_results:
                results.append(
                    SearchItem(
                        url=item.url, title=item.title, description=item.description
                    )
                )
            if not results:
                return "No search results found for this specific query."
        except ImportError:
            return "The googlesearch-python package is not installed."
        except Exception as e:
            return f"An error occurred during Google search: {e}"
        return results

    def _run(self, query: str, num_results: int = 5, lang: str = "vi") -> Union[List[SearchItem], str]:
        """Performs a synchronous Google search."""
        return self._search_sync(query, num_results, lang)

    async def _arun(
            self, query: str, num_results: int = 5, lang: str = "vi"
    ) -> Union[List[SearchItem], str]:
        """Asynchronously performs a Google search."""
        return await asyncio.to_thread(self._search_sync, query, num_results, lang)
