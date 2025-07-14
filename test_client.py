import asyncio
import logging
from fastmcp.client import Client, StdioTransport

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """
    Test client for the mcp-simple-arxiv server.
    Connects to the stdio server, lists tools, and calls each tool to verify functionality.
    """
    logging.info("Starting test client for mcp-simple-arxiv...")
    
    # Configure the stdio transport to run the server as a module
    transport = StdioTransport(
        command="python",
        args=["-m", "mcp_simple_arxiv"]
    )
    
    # Create a client with the transport
    client = Client(transport)
    
    async with client:
        try:
            # 1. List available tools
            logging.info("--- Testing tools/list ---")
            tools = await client.list_tools()
            logging.info(f"Found {len(tools)} tools:")
            for tool in tools:
                logging.info(f"- {tool.name}: {tool.description.splitlines()[0]}")
            assert len(tools) == 4, "Expected 4 tools"
            logging.info("✅ tools/list test PASSED")
            
            # 2. Test search_papers
            logging.info("\n--- Testing search_papers ---")
            query = "electron"
            logging.info(f"Calling search_papers with query: '{query}'")
            result = await client.call_tool("search_papers", {"query": query, "max_results": 2})
            logging.info(f"Result:\n{result.data}")
            assert "Search Results" in result.data
            logging.info("✅ search_papers test PASSED")

            # 3. Test get_paper_data
            logging.info("\n--- Testing get_paper_data ---")
            paper_id = "0808.3772" # A known paper
            logging.info(f"Calling get_paper_data with paper_id: '{paper_id}'")
            result = await client.call_tool("get_paper_data", {"paper_id": paper_id})
            logging.info(f"Result:\n{result.data}")
            assert "A common mass scale for satellite galaxies of the Milky Way" in result.data
            logging.info("✅ get_paper_data test PASSED")
            
            # 4. Test list_categories
            logging.info("\n--- Testing list_categories ---")
            logging.info("Calling list_categories without a filter...")
            result = await client.call_tool("list_categories")
            logging.info(f"Result snippet:\n{result.data[:300]}...")
            assert "arXiv Categories" in result.data
            logging.info("✅ list_categories (no filter) test PASSED")
            
            logging.info("Calling list_categories with filter 'cs'...")
            result = await client.call_tool("list_categories", {"primary_category": "cs"})
            logging.info(f"Result snippet:\n{result.data[:300]}...")
            assert "cs: Computer Science" in result.data
            assert "math: Mathematics" not in result.data
            logging.info("✅ list_categories (with filter) test PASSED")

            # 5. Test update_categories - This might take a moment
            logging.info("\n--- Testing update_categories ---")
            logging.info("Calling update_categories...")
            result = await client.call_tool("update_categories")
            logging.info(f"Result:\n{result.data}")
            assert "Successfully updated category taxonomy" in result.data
            logging.info("✅ update_categories test PASSED")

        except Exception as e:
            logging.error(f"An error occurred during testing: {e}", exc_info=True)
        finally:
            logging.info("\nTest run finished.")

if __name__ == "__main__":
    asyncio.run(main()) 