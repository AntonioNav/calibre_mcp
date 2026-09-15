import uvicorn
####from mcp.server.fastmcp import FastMCP
from server import mcp  # Aquí importamos tu instancia de FastMCP

if __name__ == "__main__":
    # La propia instancia de FastMCP tiene un método para correr en modo SSE
    # Esto abstrae cualquier cambio de versión de la librería
    mcp.run(transport="sse", host="0.0.0.0", port=8084)
