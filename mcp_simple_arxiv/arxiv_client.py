"""
arXiv API client with rate limiting.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any

import feedparser
import httpx
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


class SortBy(str, Enum):
    """Valid sort field options for arXiv API."""
    SUBMITTED_DATE = "submittedDate"
    UPDATED_DATE = "lastUpdatedDate"
    RELEVANCE = "relevance"


class SortOrder(str, Enum):
    """Valid sort order options for arXiv API."""
    DESCENDING = "descending"
    ASCENDING = "ascending"


@dataclass
class SearchResult:
    """Container for arXiv search results with metadata."""
    papers: List[Dict[str, Any]]
    total_results: int
    results_returned: int


class ArxivClient:
    """
    arXiv API client with built-in rate limiting.
    Ensures no more than 1 request every 3 seconds.
    """
    
    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"
        self._last_request: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
    async def _wait_for_rate_limit(self) -> None:
        """Ensures we respect arXiv's rate limit of 1 request every 3 seconds."""
        async with self._lock:
            if self._last_request is not None:
                elapsed = datetime.now() - self._last_request
                if elapsed < timedelta(seconds=3):
                    await asyncio.sleep(3 - elapsed.total_seconds())
            self._last_request = datetime.now()

    def _clean_text(self, text: str) -> str:
        """Clean up text by removing extra whitespace and newlines."""
        return " ".join(text.split())

    def _get_html_url(self, arxiv_id: str) -> str:
        """
        Construct HTML version URL for a paper.
        
        The HTML version URL is not provided by the API but can be constructed
        from the paper ID with the version suffix removed.
        """
        # Remove only a trailing version suffix (e.g., v1, v12); legacy archive
        # names such as "solv-int" may contain the letter "v" themselves
        base_id = re.sub(r'v[0-9]+$', '', arxiv_id)
        return f"https://arxiv.org/html/{base_id}"

    def _parse_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a feed entry into a paper dictionary."""
        # Extract PDF and HTML links
        pdf_url = None
        abstract_url = None  # This is the URL to the abstract page
        for link in entry.get('links', []):
            if isinstance(link, dict):
                if link.get('type') == 'application/pdf':
                    pdf_url = link.get('href')
                elif link.get('type') == 'text/html':
                    abstract_url = link.get('href')

        # Get paper ID
        paper_id = entry.get('id', '').split("/abs/")[-1].rstrip()
        
        # Create HTML version URL
        html_url = self._get_html_url(paper_id) if paper_id else None

        # Get authors
        authors = []
        for author in entry.get('authors', []):
            if isinstance(author, dict) and 'name' in author:
                authors.append(author['name'])
            elif hasattr(author, 'name'):
                authors.append(author.name)

        # Get categories
        categories = []
        primary_category = None
        
        # Get primary category
        if 'arxiv_primary_category' in entry:
            if isinstance(entry['arxiv_primary_category'], dict):
                primary_category = entry['arxiv_primary_category'].get('term')
            elif hasattr(entry['arxiv_primary_category'], 'term'):
                primary_category = entry['arxiv_primary_category'].term
        
        # Get all categories
        for category in entry.get('tags', []):
            if isinstance(category, dict) and 'term' in category:
                categories.append(category['term'])
            elif hasattr(category, 'term'):
                categories.append(category.term)

        # Remove primary category from regular categories if it's there
        if primary_category and primary_category in categories:
            categories.remove(primary_category)

        return {
            "id": paper_id,
            "title": self._clean_text(entry.get('title', '')),
            "authors": authors,
            "primary_category": primary_category,
            "categories": categories,
            "published": entry.get('published', ''),
            "updated": entry.get('updated', ''),
            "summary": self._clean_text(entry.get('summary', '')),
            "comment": self._clean_text(entry.get('arxiv_comment', '')),
            "journal_ref": entry.get('arxiv_journal_ref', ''),
            "doi": entry.get('arxiv_doi', ''),
            "pdf_url": pdf_url,
            "abstract_url": abstract_url,  # URL to abstract page
            "html_url": html_url  # URL to HTML version if available
        }

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: SortBy = SortBy.SUBMITTED_DATE,
        sort_order: SortOrder = SortOrder.DESCENDING
    ) -> SearchResult:
        """
        Search arXiv papers.
        
        The query string supports arXiv's advanced search syntax:
        - Search in title: ti:"search terms"
        - Search in abstract: abs:"search terms"
        - Search by author: au:"author name"
        - Combine terms with: AND, OR, ANDNOT
        - Filter by category: cat:cs.AI
        
        Args:
            query: Search query string.
            max_results: Maximum results to return (1-2000), default 10.
            sort_by: Sort field for the arXiv API.
            sort_order: Sort direction for the arXiv API.

        Examples:
        - "machine learning"  (searches all fields)
        - ti:"neural networks" AND cat:cs.AI  (title with category)
        - au:bengio AND ti:"deep learning"  (author and title)
        """
        await self._wait_for_rate_limit()
        
        # Ensure max_results is within API limits
        max_results = min(max_results, 2000)  # API limit: 2000 per request
        
        params = {
            "search_query": query,
            "max_results": max_results,
            "sortBy": sort_by.value,
            "sortOrder": sort_order.value,
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status() # Raise an exception for bad status codes
                
                # Parse the Atom feed response
                feed = feedparser.parse(response.text)
                
                if not isinstance(feed, dict) or 'entries' not in feed:
                    logger.error("Invalid response from arXiv API")
                    logger.debug(f"Response text: {response.text[:1000]}...")
                    raise ValueError("Invalid response from arXiv API")

                # Extract total results from OpenSearch metadata
                total_results = 0
                if hasattr(feed, 'feed') and 'opensearch_totalresults' in feed.feed:
                    try:
                        total_results = int(feed.feed.opensearch_totalresults)
                    except (ValueError, TypeError):
                        logger.warning(
                            "Could not parse opensearch:totalResults from feed"
                        )

                if not feed.get('entries'):
                    return SearchResult(
                        papers=[],
                        total_results=total_results,
                        results_returned=0
                    )

                papers = [self._parse_entry(entry) for entry in feed.entries]
                if total_results == 0:
                    total_results = len(papers)
                return SearchResult(
                    papers=papers,
                    total_results=total_results,
                    results_returned=len(papers)
                )
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error while searching: {e}")
                raise ValueError(f"arXiv API HTTP error: {str(e)}")
            
    async def get_paper(self, paper_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific paper.
        
        Args:
            paper_id: arXiv paper ID (e.g., "2103.08220")
            
        Returns:
            Dictionary containing paper metadata, including:
            - Basic metadata (title, authors, dates)
            - Categories (primary and others)
            - Abstract and comments
            - URLs (abstract page, PDF version, HTML version if available)
            - DOI if available
        """
        await self._wait_for_rate_limit()
        
        params = {
            "id_list": paper_id,
            "max_results": 1
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                if not isinstance(feed, dict) or 'entries' not in feed:
                    logger.error("Invalid response from arXiv API")
                    logger.debug(f"Response text: {response.text[:1000]}...")
                    raise ValueError("Invalid response from arXiv API")
                
                if not feed.get('entries'):
                    raise ValueError(f"Paper not found: {paper_id}")
                    
                return self._parse_entry(feed.entries[0])
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error while fetching paper: {e}")
                raise ValueError(f"arXiv API HTTP error: {str(e)}")

    async def get_paper_text_from_pdf(self, paper_id: str) -> str:
        """
        Get the full paper text as Markdown using Docling.
        
        Downloads and converts the paper PDF to Markdown format.
        This operation may take 30-90 seconds depending on paper length and complexity.
        
        Args:
            paper_id: arXiv paper ID (e.g., "2103.08220")
            
        Returns:
            Markdown-formatted text of the paper, or an error message if conversion fails.
            
        Note:
            - Complex equations and figures may not convert perfectly
            - Very large papers may exceed typical context windows
            - Conversion is resource-intensive (CPU and memory)
        """
        await self._wait_for_rate_limit()
  
        paper = await self.get_paper(paper_id)
        if not paper["pdf_url"]:
            return f"No PDF URL found for paper: {paper_id}"

        # We have the PDF URL so we can proceed
        # Run the synchronous PDF conversion in a thread pool to avoid blocking
        try:
            loop = asyncio.get_event_loop()
             
            def convert_paper():
                converter = DocumentConverter()
                result = converter.convert(paper["pdf_url"])
                return result.document.export_to_markdown()
            
            # Add timeout to prevent hanging on very large or problematic PDFs    
            markdown = await asyncio.wait_for(
                loop.run_in_executor(None, convert_paper),
                timeout=120.0  # 2 minute timeout
            )
            return markdown
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout: PDF conversion exceeded 120 seconds for paper {paper_id}"
            logger.error(error_msg)
            return error_msg
            
        except Exception as e:
            logger.error(f"Error converting paper {paper_id} to Markdown: {e}", exc_info=True)
            return f"Error while converting paper to Markdown: {str(e)}"
