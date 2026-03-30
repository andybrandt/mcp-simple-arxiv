# mcp-simple-arxiv

[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/andybrandt/mcp-simple-arxiv)](https://archestra.ai/mcp-catalog/andybrandt__mcp-simple-arxiv)
[![smithery badge](https://smithery.ai/badge/mcp-simple-arxiv)](https://smithery.ai/server/mcp-simple-arxiv)
[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/dc95dba9-149a-4eaa-bf08-36e0cb0f3a5a)

An MCP server that provides access to arXiv papers through their API.

<a href="https://glama.ai/mcp/servers/p38q3nagwb"><img width="380" height="200" src="https://glama.ai/mcp/servers/p38q3nagwb/badge" alt="mcp-simple-arxiv MCP server" /></a>

## Hosted deployment

A hosted deployment is available on [Fronteir AI](https://fronteir.ai/mcp/andybrandt-mcp-simple-arxiv).

## Features

This server allows LLM clients (like Claude Desktop) to:
- Search for scientific papers on arXiv by title and abstract content
- Filter search results by submission date range
- Control search result sorting (by submission date, update date, or relevance)
- See total matching results count to gauge search specificity
- Get paper metadata and abstracts
- Retrieve full paper text as Markdown (converted from PDF)
- Access links to available paper formats (PDF/HTML)
- Browse and search arXiv subject categories

To use the web version just add this connector to Claude.ai https://mcp.andybrandt.net/arxiv .
You can also install & use it locally. 

## Installation and Deployment

This server can be run in two modes: as a local `stdio` server for desktop clients or as a network-accessible web server.

### Installing via Smithery

To install Simple Arxiv for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-simple-arxiv):

```bash
npx -y @smithery/cli install mcp-simple-arxiv --client claude
```

### Manual Installation
```bash
pip install mcp-simple-arxiv
```

## Usage with Claude Desktop

Add this configuration to your `claude_desktop_config.json`:

(Mac OS)

```json
{
  "mcpServers": {
    "simple-arxiv": {
      "command": "python",
      "args": ["-m", "mcp_simple_arxiv"]
      }
  }
}
```

(Windows version):

```json
{
  "mcpServers": {
    "simple-arxiv": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",
      "args": [
        "-m",
        "mcp_simple_arxiv"
      ]
    }
  }
}
```

After restarting Claude Desktop, the following capabilities will be available:

### Searching Papers

You can ask Claude to search for papers using queries like:
```
Can you search arXiv for recent papers about large language models?
```

The LLM can sort results by submission date, update date, or relevance:
```
Search arXiv for papers about transformers, sorted by relevance.
```

Date filtering lets you focus on specific time periods:
```
Find papers about quantum computing published in 2024.
Search for recent machine learning papers from the last 6 months.
```

Search results include:
- Total number of matching papers (e.g., "Found 15,234 total results, showing first 10")
- Paper title, authors, and arXiv ID
- Categories (primary and additional)
- Publication date
- Abstract preview

### Getting Paper Details

Once you have a paper ID, you can ask for more details:
```
Can you show me the details for paper 2103.08220?
```

This will return:
- Full paper title
- Authors
- Publication and update dates
- Journal reference (if available)
- Paper abstract
- Links to available formats (PDF/HTML)


*For web deployment see [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md)*.

## Development

To install for development:
```bash
git clone https://github.com/andybrandt/mcp-simple-arxiv
cd mcp-simple-arxiv
pip install -e .
```

### arXiv API Guidelines

This server follows arXiv API usage guidelines:
- Rate limiting to max 1 request per 3 seconds
- Single connection at a time
- Proper error handling and retry logic

## License

MIT
