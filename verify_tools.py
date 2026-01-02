import asyncio
import sys
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def verify():
    server_params = StdioServerParameters(
        command="stravinsky",
        args=[],
        env={}
    )
    
    print("Testing Stravinsky MCP Server Tool Advertisement...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("\n--- Tools ---")
                tools_result = await session.list_tools()
                print(f"Total tools: {len(tools_result.tools)}")
                for tool in tools_result.tools:
                    print(f"- {tool.name}: {tool.description[:60]}...")
                
                print("\n--- Prompts ---")
                prompts_result = await session.list_prompts()
                print(f"Total prompts: {len(prompts_result.prompts)}")
                for prompt in prompts_result.prompts:
                    print(f"- {prompt.name}: {prompt.description[:60]}...")
                    
                if not tools_result.tools:
                    print("\n❌ CRITICAL: No tools advertised!")
                else:
                    print("\n✅ Tool advertisement verified.")
                    
    except Exception as e:
        print(f"\n❌ FAILED to connect or initialize: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())
