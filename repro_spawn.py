
import asyncio
import os
from mcp_bridge.tools.agent_manager import agent_spawn, agent_list, agent_output

async def test_spawn():
    print("Spawning agent...")
    result = await agent_spawn(
        prompt="Tell me a joke about robots.",
        agent_type="explore",
        model="gemini-3-flash"
    )
    print(f"Spawn Result: {result}")
    
    # Wait a bit
    await asyncio.sleep(2)
    
    print("\nListing agents:")
    agents = await agent_list()
    print(agents[0].text)
    
    # Check output
    task_id = result.split("ID: ")[1].split(".")[0]
    print(f"\nChecking output for {task_id}...")
    output = await agent_output(task_id=task_id)
    print(f"Output: {output[0].text[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_spawn())
