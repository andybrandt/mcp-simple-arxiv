"""
MCP server for accessing arXiv papers.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

import asyncio
import logging

from fastmcp import FastMCP

from .arxiv_client import ArxivClient
from .update_taxonomy import load_taxonomy, update_taxonomy_file

logger = logging.getLogger(__name__)

def get_first_sentence(text: str, max_len: int = 200) -> str:
    """Extract first sentence from text, limiting length."""
    # Look for common sentence endings
    for end in ['. ', '! ', '? ']:
        pos = text.find(end)
        if pos != -1 and pos < max_len:
            return text[:pos + 1]
    # If no sentence ending found, just take first max_len chars
    if len(text) > max_len:
        return text[:max_len].rstrip() + '...'
    return text

def create_app():
    """Creates and configures the FastMCP app instance and its tools."""
    app = FastMCP("arxiv-server")
    arxiv_client = ArxivClient()

    @app.tool(
        annotations={
            "title": "Search arXiv Papers",
            "readOnlyHint": True,
            "openWorldHint": True
        }
    )
    async def search_papers(query: str, max_results: int = 10) -> str:
        """
Search for papers on arXiv by title and abstract content.

You can use advanced search syntax:
- Search in title: ti:"search terms"
- Search in abstract: abs:"search terms"
- Search by author: au:"author name"
- Combine terms with: AND, OR, ANDNOT
- Filter by category: cat:cs.AI (use list_categories tool to see available categories)

Examples:
- "machine learning"  (searches all fields)
- ti:"neural networks" AND cat:cs.AI  (title with category)
- au:bengio AND ti:"deep learning"  (author and title)
        """
        max_results = min(max_results, 50)
        papers = await arxiv_client.search(query, max_results)
        
        # Format results in a readable way
        result = "Search Results:\n\n"
        for i, paper in enumerate(papers, 1):
            result += f"{i}. {paper['title']}\n"
            result += f"   Authors: {', '.join(paper['authors'])}\n"
            result += f"   ID: {paper['id']}\n"
            result += f"   Categories: "
            if paper['primary_category']:
                result += f"Primary: {paper['primary_category']}"
            if paper['categories']:
                result += f", Additional: {', '.join(paper['categories'])}"
            result += f"\n   Published: {paper['published']}\n"
            
            # Add first sentence of abstract
            abstract_preview = get_first_sentence(paper['summary'])
            result += f"   Preview: {abstract_preview}\n"
            result += "\n"
        
        return result

    @app.tool(
        annotations={
            "title": "Get arXiv Paper Data",
            "readOnlyHint": True,
            "openWorldHint": True
        }
    )
    async def get_paper_data(paper_id: str) -> str:
        """Get detailed information about a specific paper including abstract and available formats."""
        paper = await arxiv_client.get_paper(paper_id)
        
        # Format paper details in a readable way with clear sections
        result = f"Title: {paper['title']}\n\n"
        
        # Metadata section
        result += "Metadata:\n"
        result += f"- Authors: {', '.join(paper['authors'])}\n"
        result += f"- Published: {paper['published']}\n"
        result += f"- Last Updated: {paper['updated']}\n"
        result += "- Categories: "
        if paper['primary_category']:
            result += f"Primary: {paper['primary_category']}"
        if paper['categories']:
            result += f", Additional: {', '.join(paper['categories'])}"
        result += "\n"
        
        if paper['doi']:
            result += f"- DOI: {paper['doi']}\n"
        if paper["journal_ref"]:
            result += f"- Journal Reference: {paper['journal_ref']}\n"
        
        # Abstract section
        result += "\nAbstract:\n"
        result += paper["summary"]
        result += "\n"
        
        # Access options section
        result += "\nAccess Options:\n"
        result += "- Abstract page: " + paper["abstract_url"] + "\n"
        if paper["html_url"]:  # Add HTML version if available
            result += "- Full text HTML version: " + paper["html_url"] + "\n"
        result += "- PDF version: " + paper["pdf_url"] + "\n"
        
        # Additional information section
        if paper["comment"] or "code" in paper["comment"].lower():
            result += "\nAdditional Information:\n"
            if paper["comment"]:
                result += "- Comment: " + paper["comment"] + "\n"
                
        return result

    @app.tool(
        annotations={
            "title": "List arXiv Categories",
            "readOnlyHint": True,
            "openWorldHint": False
        }
    )
    def list_categories(primary_category: str = None) -> str:
        """List all available arXiv categories and how to use them in search."""
        try:
            taxonomy = load_taxonomy()
        except Exception as e:
            logger.error(f"Error loading taxonomy: {e}")
            return f"Error loading category taxonomy. Try using update_categories tool to refresh it."

        result = "arXiv Categories:\n\n"
        
        for primary, data in taxonomy.items():
            if primary_category and primary != primary_category:
                continue
                
            result += f"{primary}: {data['name']}\n"
            for code, desc in data['subcategories'].items():
                result += f"  {primary}.{code}: {desc}\n"
            result += "\n"
            
        result += "\nUsage in search:\n"
        result += '- Search in specific category: cat:cs.AI\n'
        result += '- Combine with other terms: "neural networks" AND cat:cs.AI\n'
        result += '- Multiple categories: (cat:cs.AI OR cat:cs.LG)\n'
        result += '\nNote: If categories seem outdated, use the update_categories tool to refresh them.\n'
        
        return result

    @app.tool(
        annotations={
            "title": "Update arXiv Categories",
            "readOnlyHint": False,
            "openWorldHint": True
        }
    )
    def update_categories() -> str:
        """Update the stored category taxonomy by fetching the latest version from arxiv.org"""
        try:
            taxonomy = update_taxonomy_file()
            result = "Successfully updated category taxonomy.\n\n"
            result += f"Found {len(taxonomy)} primary categories:\n"
            for primary, data in taxonomy.items():
                result += f"- {primary}: {data['name']} ({len(data['subcategories'])} subcategories)\n"
            return result
        except Exception as e:
            logger.error(f"Error updating taxonomy: {e}")
            # FastMCP will handle raising this as a proper JSON-RPC error
            raise e
            
    return app

app = create_app()

def main():
    """Run the MCP server."""
    app.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()