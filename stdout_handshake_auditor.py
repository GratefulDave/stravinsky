import importlib
import sys
import io
import time
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

def audit_modules():
    print("🔍 Stravinsky Protocol Hygiene Audit Starting...")
    print("-" * 50)
    
    # List of modules to audit
    modules = [
        "mcp_bridge",
        "mcp_bridge.server",
        "mcp_bridge.hooks",
        "mcp_bridge.hooks.manager",
        "mcp_bridge.hooks.truncator",
        "mcp_bridge.hooks.edit_recovery",
        "mcp_bridge.hooks.directory_context",
        "mcp_bridge.hooks.compaction",
        "mcp_bridge.hooks.budget_optimizer",
        "mcp_bridge.auth",
        "mcp_bridge.auth.token_store",
        "mcp_bridge.auth.oauth",
        "mcp_bridge.auth.openai_oauth",
        "mcp_bridge.auth.cli",
        "mcp_bridge.tools",
        "mcp_bridge.tools.model_invoke",
        "mcp_bridge.tools.project_context",
        "mcp_bridge.tools.agent_manager",
        "mcp_bridge.tools.task_runner",
        "mcp_bridge.tools.code_search",
        "mcp_bridge.tools.lsp",
        "mcp_bridge.tools.lsp.tools",
        "mcp_bridge.tools.lsp.server_manager",
    ]
    
    results = []
    total_leaks = 0
    
    for mod_name in modules:
        f = io.StringIO()
        e = io.StringIO()
        
        start_time = time.time()
        try:
            with redirect_stdout(f), redirect_stderr(e):
                # We need to reload to ensure we are auditing the impact properly
                # But for the first pass, just importing is enough if the venv is fresh
                if mod_name in sys.modules:
                    importlib.reload(sys.modules[mod_name])
                else:
                    importlib.import_module(mod_name)
        except Exception as ex:
            print(f"❌ {mod_name:.<40} CRASHED: {ex}")
            continue
            
        elapsed = (time.time() - start_time) * 1000
        stdout_content = f.getvalue()
        stderr_content = e.getvalue()
        
        status = "✅ CLEAN"
        if stdout_content:
            status = f"⚠️  LEAK ({len(stdout_content)} bytes)"
            total_leaks += 1
            
        latency_warning = ""
        if elapsed > 300:
            latency_warning = f" ⏳ SLOW ({elapsed:.1f}ms)"
            
        print(f"{status} [{elapsed:4.1f}ms] {mod_name}{latency_warning}")
        
        if stdout_content:
            print(f"      STDOUT: {repr(stdout_content[:100])}{'...' if len(stdout_content) > 100 else ''}")
            
    print("-" * 50)
    if total_leaks == 0:
        print("🎉 SUCCESS: No stdout pollution detected during module imports.")
    else:
        print(f"🚨 FAILURE: Found {total_leaks} modules polluting stdout.")
        sys.exit(1)

if __name__ == "__main__":
    audit_modules()
