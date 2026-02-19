#!/bin/bash
docker build --progress=plain -f Dockerfile.web -t mcp-simple-arxiv:web . 2>&1 | tee build_log.txt
docker images
echo "Saving"
docker save mcp-simple-arxiv:web -o mcp-simple-arxiv.tar
echo "Compressing"
gzip -9 mcp-simple-arxiv.tar
echo "Done"
