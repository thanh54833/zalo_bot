import asyncio
import logging
from typing import Dict, List, Type, Union, Any

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .base_configurable_tool import BaseConfigurableTool

# Set up logging
logger = logging.getLogger(__name__)


class SearchItem(BaseModel):
    title: str
    url: str
    description: str


class GoogleSearchTool(BaseConfigurableTool):
    """
    Google Search Tool - HOÀN TOÀN LẤY TỪ CONFIG!
    NGHIÊM CẤM hard-code bất kỳ thông tin gì!
    """
    
    def __init__(self, tool_config: Dict[str, Any]):
        # ✅ GỌI CONSTRUCTOR CHA VỚI CONFIG
        super().__init__(tool_config)
        
        # ✅ VALIDATE DEPENDENCIES
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """Kiểm tra dependencies có sẵn không"""
        try:
            import googlesearch
            logger.debug("✅ googlesearch-python dependency available")
        except ImportError:
            logger.warning("⚠️ googlesearch-python dependency not available")
    
    def _search_sync(self, query: str, num_results: int = 5, lang: str = "vi") -> Union[List[SearchItem], str]:
        """Performs a single synchronous Google search."""
        try:
            from googlesearch import search
            
            results = []
            search_results = search(query, num_results=num_results, lang=lang, advanced=True)
            
            for item in search_results:
                results.append(
                    SearchItem(
                        url=item.url, 
                        title=item.title, 
                        description=item.description
                    )
                )
            
            if not results:
                return "No search results found for this specific query."
                
            return results
            
        except ImportError:
            return "The googlesearch-python package is not installed."
        except Exception as e:
            return f"An error occurred during Google search: {e}"

    def _run(self, **kwargs) -> Union[List[SearchItem], str]:
        """Performs a synchronous Google search."""
        # ✅ LẤY PARAMETERS TỪ CONFIG - KHÔNG HARD-CODE!
        query = kwargs.get("query")
        num_results = kwargs.get("num_results", 5)
        lang = kwargs.get("lang", "vi")
        
        if not query:
            return "Query parameter is required"
            
        return self._search_sync(query, num_results, lang)

    async def _arun(self, **kwargs) -> Union[List[SearchItem], str]:
        """Asynchronously performs a Google search."""
        return await asyncio.to_thread(self._run, **kwargs)
