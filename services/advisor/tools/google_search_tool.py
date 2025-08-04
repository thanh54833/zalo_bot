import logging
from typing import Dict, List, Type, Union
import asyncio
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
        "It automatically searches both the general web and the concung.com website in parallel. "
        "Use this as the primary tool to understand a user's general query in the context of mother and baby products."
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

    async def _arun(
            self, query: str, num_results: int = 5, lang: str = "vi"
    ) -> Dict[str, Union[List[SearchItem], str]]:
        """
        Runs a general web search and a concung.com-specific search in parallel.
        Returns a dictionary with prioritized results from concung.com.
        """
        concung_query = f"{query} site:concung.com"
        normal_query = f"{query} -site:avakids.com"

        # Run both searches in parallel using the synchronous _search_sync method in separate threads.
        loop = asyncio.get_running_loop()
        task_concung = loop.run_in_executor(None, self._search_sync, concung_query, 5, lang)
        task_normal = loop.run_in_executor(None, self._search_sync, normal_query, num_results, lang)

        results_concung, results_normal = await asyncio.gather(
            task_concung, task_normal
        )

        logger.info(f"Google Search: Found {len(results_concung)} results from concung.com and {len(results_normal)} from the web for query '{query}'.")

        return {
            "concung_results": results_concung,
            "web_results": results_normal,
        }

    def _run(self, query: str, num_results: int = 10, lang: str = "vi") -> Dict[str, Union[List[SearchItem], str]]:
        """Synchronous wrapper for the async run method."""
        return asyncio.run(self._arun(query, num_results, lang))
