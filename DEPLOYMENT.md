# Web Server Deployment Guide

This guide explains how to run the network-hostable version of the `mcp-simple-arxiv` server. This version uses the MCP Streamable HTTP transport and is ideal for deployments where clients connect over a network.

## Overview

The web server is a stateless service that exposes four tools for interacting with the arXiv API:
- `search_papers`: Search for papers by keyword.
- `get_paper_data`: Fetch detailed information for a specific paper ID.
- `list_categories`: List the available arXiv subject categories.
- `update_categories`: Refresh the locally cached category list from arXiv.

It runs using FastMCP’s built-in web server (based on Uvicorn/Starlette).

## Local Development

### 1. Install Dependencies

First, ensure you have a virtual environment set up and the project installed in editable mode:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 2. Run the Server

The server can be run directly using its Python module:
```bash
python -m mcp_simple_arxiv.web_server
```
This will start the server on `http://0.0.0.0:8000`.

### 3. Test the Server

You can test the running server from your command line using `curl`.

**List Tools Request:**
```bash
curl -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**Tool Call Request (`search_papers`):**
```bash
curl -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_papers","arguments":{"query": "quantum computing"}}}'
```

## Docker Deployment

The project includes a `Dockerfile.web` for easy containerization.

### 1. Build the Docker Image
```bash
docker build -f Dockerfile.web -t mcp-simple-arxiv:web .
```

### 2. Run the Docker Container

To run the container for use with a local reverse proxy (like Apache or Nginx), you should map the container’s port only to the host’s loopback interface:
```bash
docker run -d -p 127.0.0.1:8000:8000 --name arxiv-web mcp-simple-arxiv:web
```
This command does two important things:
1.  It runs the container in detached mode (`-d`).
2.  It maps port 8000 inside the container to port 8000 on the host machine’s `localhost` interface only (`-p 127.0.0.1:8000:8000`). This ensures the server is not directly accessible from the network, which is the recommended setup when placing it behind a reverse proxy.

For persistence, you can set the container to restart automatically:
```bash
docker run -d --restart always -p 127.0.0.1:8000:8000 --name arxiv-web mcp-simple-arxiv:web
```

### 3. Transferring the Image

If you built the image on a different machine, you can package it for transfer:
```bash
# On the source machine
docker save -o mcp-simple-arxiv-web.tar mcp-simple-arxiv:web
gzip mcp-simple-arxiv-web.tar

# On the destination machine
gunzip mcp-simple-arxiv-web.tar.gz
docker load -i mcp-simple-arxiv-web.tar
```

## Changing the Port

The server is configured to run on port 8000 inside the container. To map this to a different host port, change the first value in the `-p` parameter. The format is `-p <host_port>:<container_port>`.
```bash
# Map container's port 8000 to host's port 9001
docker run -d -p 127.0.0.1:9001:8000 --name arxiv-web mcp-simple-arxiv:web
```
The server will now be accessible at `http://127.0.0.1:9001` on the host.

## Apache Reverse Proxy Configuration

**Important**: MCP clients may request URLs with or without trailing slashes. Your Apache configuration must handle both cases to avoid 404 errors.

Example Configuration:
```apache
<VirtualHost *:443>
    ServerName mcp.yourdomain.com

    # SSL Configuration (recommended for production)
    # SSLEngine on
    # SSLCertificateFile /path/to/cert.pem
    # SSLCertificateKeyFile /path/to/key.pem

    # Main proxy configuration
    <Location /arxiv>
        ProxyPass http://127.0.0.1:8000/mcp/
        ProxyPassReverse http://127.0.0.1:8000/mcp/
    </Location>
</VirtualHost>
```
This configuration will make your arXiv MCP server available at `https://mcp.yourdomain.com/arxiv`. 