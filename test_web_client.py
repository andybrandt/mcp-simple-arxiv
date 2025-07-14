import asyncio
import httpx
import logging
import subprocess
import time
import sys
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SERVER_URL = "http://127.0.0.1:8000/mcp/"
HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json"
}

async def check_server_ready(client: httpx.AsyncClient):
    """Polls the server until it is ready to accept connections."""
    for _ in range(20):  # Poll for up to 10 seconds
        try:
            response = await client.post(SERVER_URL, json={"jsonrpc": "2.0", "id": 0, "method": "tools/list"}, headers=HEADERS)
            if response.status_code == 200:
                logging.info("Web server is up and running.")
                return True
        except httpx.ConnectError:
            pass
        await asyncio.sleep(0.5)
    logging.error("Web server did not start in time.")
    return False

async def call_tool(client: httpx.AsyncClient, tool_name: str, params: dict = None) -> dict:
    """Helper function to call a tool via JSON-RPC."""
    method = "tools/call" if tool_name != "tools/list" else "tools/list"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }

    if method == "tools/call":
        payload["params"] = {"name": tool_name, "arguments": params or {}}
    
    response = await client.post(SERVER_URL, json=payload, headers=HEADERS)
    response.raise_for_status()
    # The response is Server-Sent Events, we need to parse it
    for line in response.text.strip().split('\n'):
        if line.startswith('data:'):
            import json
            return json.loads(line[len('data:'):].strip())
    raise ValueError("Did not receive a valid data event from the server.")


async def main():
    """
    Test client for the mcp-simple-arxiv web server.
    Starts the server, runs tests, and then stops it.
    """
    server_process = None
    try:
        logging.info("Starting web server process...")
        # Start the server as a subprocess
        server_process = subprocess.Popen(
            [sys.executable, "-m", "mcp_simple_arxiv.web_server"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            if not await check_server_ready(client):
                raise RuntimeError("Could not connect to the web server.")

            # 1. List available tools
            logging.info("\n--- Testing tools/list ---")
            response_json = await call_tool(client, "tools/list") # Using call_tool to simplify logic
            tools = response_json['result']['tools']
            logging.info(f"Found {len(tools)} tools.")
            assert len(tools) == 4
            logging.info("✅ tools/list test PASSED")

            # 2. Test search_papers
            logging.info("\n--- Testing search_papers ---")
            query = "dark matter"
            response_json = await call_tool(client, "search_papers", {"query": query, "max_results": 1})
            result = response_json['result']['structuredContent']['result']
            logging.info(f"Result for '{query}':\n{result}")
            assert "Search Results" in result
            logging.info("✅ search_papers test PASSED")

            # 3. Test get_paper_data
            logging.info("\n--- Testing get_paper_data ---")
            paper_id = "0808.3772"  # Using the same ID as the stdio test for consistency
            response_json = await call_tool(client, "get_paper_data", {"paper_id": paper_id})
            result = response_json['result']['structuredContent']['result']
            logging.info(f"Result for paper '{paper_id}':\n{result}")
            assert "A common mass scale for satellite galaxies of the Milky Way" in result
            logging.info("✅ get_paper_data test PASSED")

            # 4. Test list_categories
            logging.info("\n--- Testing list_categories ---")
            response_json = await call_tool(client, "list_categories")
            result = response_json['result']['structuredContent']['result']
            logging.info("Result snippet:\n" + result[:200] + "...")
            assert "arXiv Categories" in result
            logging.info("✅ list_categories test PASSED")

            # 5. Test update_categories
            logging.info("\n--- Testing update_categories ---")
            response_json = await call_tool(client, "update_categories")
            result = response_json['result']['structuredContent']['result']
            logging.info(f"Result:\n{result}")
            assert "Successfully updated category taxonomy" in result
            logging.info("✅ update_categories test PASSED")

    except Exception as e:
        logging.error(f"An error occurred during testing: {e}", exc_info=True)
    finally:
        if server_process:
            logging.info("\nStopping web server process...")
            server_process.send_signal(signal.SIGINT)  # Send Ctrl+C
            try:
                server_process.wait(timeout=10)
                logging.info("Web server stopped gracefully.")
            except subprocess.TimeoutExpired:
                logging.warning("Web server did not stop gracefully, killing.")
                server_process.kill()
        logging.info("Test run finished.")

if __name__ == "__main__":
    asyncio.run(main()) 