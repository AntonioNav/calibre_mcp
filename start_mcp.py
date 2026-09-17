import os

from server import mcp

if __name__ == "__main__":
    mcp.run(
        transport="sse",
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8084")),
    )
