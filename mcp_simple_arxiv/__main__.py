"""
Main entry point for the MCP server.
"""

from .server import app

def main():
    """Run the MCP server."""
    app.run()

if __name__ == "__main__":
    main()