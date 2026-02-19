"""
Web server entry point for the ArXiv MCP server.
"""
import asyncio
import logging
from importlib.metadata import version

from mcp_simple_arxiv.server import create_app

# Get package version dynamically from pyproject.toml via importlib.metadata
_version = version("mcp-simple-arxiv")

def main():
    """Create and run the web server."""
    # Create the app, configuring it for web deployment
    # Host '0.0.0.0' is important for accessibility within Docker
    app = create_app()
    
    # Run the server with the streamable HTTP transport and web config
    app.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        stateless_http=False
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 
