import asyncio
from mcp_bridge.tools.model_invoke import invoke_gemini
from mcp_bridge.auth.token_store import TokenStore

async def test_agent_understanding():
    print("\n--- Testing Agent Understanding of Truncation ---")
    
    # Simulate truncated output from a tool
    truncated_content = "This is some code content...\n" * 10
    truncated_content += "\n\n[Output truncated. Showing first and last 50 characters. Use offset/limit parameters to read specific parts of the file.]"
    
    prompt = f"""
    I just read a file and got this output:
    
    {truncated_content}
    
    Did you get the full file? If not, what should you do to see the middle part?
    Answer in one short sentence.
    """
    
    token_store = TokenStore()
    try:
        response = await invoke_gemini(
            token_store=token_store,
            prompt=prompt,
            model="gemini-3-flash"
        )
        print(f"Agent Response: {response}")
        
        # Check if response acknowledges truncation/offset/limit
        lower_resp = response.lower()
        if "truncated" in lower_resp or "limit" in lower_resp or "offset" in lower_resp or "middle" in lower_resp:
            print("✅ Agent correctly understood the truncation guidance.")
        else:
            print("❌ Agent did not explicitly acknowledge truncation mechanics.")
            
    except Exception as e:
        print(f"Error calling Gemini: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent_understanding())
