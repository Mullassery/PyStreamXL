"""Example: PyStreamXL MCP 2.0 Integration"""

import asyncio
from pystreamxl import PerceptionEngine  # Adjust import based on project

async def main():
    # Initialize with MCP 2.0 support
    engine = PerceptionEngine()
    
    # Start MCP connector
    mcp_url = engine.start_mcp_connector()
    print(f"✓ PyStreamXL MCP 2.0 running at {mcp_url}")
    
    # Use the tools
    # Example: handler = YourHandler(engine)
    # result = await handler.your_tool(...)
    
    # Keep server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        engine.stop_mcp_connector()
        print("✓ MCP server stopped")

if __name__ == "__main__":
    asyncio.run(main())
