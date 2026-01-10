"""
Session Manager Tools

Tools for navigating and searching Claude Code session history.
Sessions are stored in ~/.claude/projects/ as JSONL files.
"""

import json
from datetime import datetime
from pathlib import Path


def get_sessions_directory() -> Path:
    """Get the Claude sessions directory."""
    return Path.home() / ".claude" / "projects"


def list_sessions(
    project_path: str | None = None,
    limit: int = 20,
    from_date: str | None = None,
    to_date: str | None = None,
) -> str:
    """
    List Claude Code sessions with optional filtering.
    
    Args:
        project_path: Filter by project path
        limit: Maximum sessions to return
        from_date: Filter from date (ISO format)
        to_date: Filter until date (ISO format)
        
    Returns:
        Formatted list of sessions.
    """
    sessions_dir = get_sessions_directory()
    if not sessions_dir.exists():
        return "No sessions directory found"
    
    sessions = []
    
    # Walk through project directories
    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue
        
        # Check project path filter
        if project_path:
            # Project dirs are hashed, so we'd need a mapping
            # For now, skip this filter
            pass
        
        # Find session files
        for session_file in project_dir.glob("*.jsonl"):
            try:
                stat = session_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                # Date filters
                if from_date:
                    from_dt = datetime.fromisoformat(from_date)
                    if mtime < from_dt:
                        continue
                if to_date:
                    to_dt = datetime.fromisoformat(to_date)
                    if mtime > to_dt:
                        continue
                
                sessions.append({
                    "id": session_file.stem,
                    "path": str(session_file),
                    "project": project_dir.name,
                    "modified": mtime.isoformat(),
                    "size": stat.st_size,
                })
            except Exception:
                continue
    
    # Sort by modified time, newest first
    sessions.sort(key=lambda s: s["modified"], reverse=True)
    sessions = sessions[:limit]
    
    if not sessions:
        return "No sessions found"
    
    lines = [f"Found {len(sessions)} sessions:\n"]
    for s in sessions:
        lines.append(f"  {s['id'][:12]}... ({s['modified'][:10]})")
    
    return "\n".join(lines)


def read_session(
    session_id: str,
    limit: int | None = None,
    include_metadata: bool = False,
) -> str:
    """
    Read messages from a session.
    
    Args:
        session_id: Session ID (filename stem)
        limit: Maximum messages to read
        include_metadata: Include message metadata
        
    Returns:
        Formatted session content.
    """
    sessions_dir = get_sessions_directory()
    
    # Find session file
    session_file = None
    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / f"{session_id}.jsonl"
        if candidate.exists():
            session_file = candidate
            break
        # Also check partial matches
        for f in project_dir.glob(f"{session_id}*.jsonl"):
            session_file = f
            break
    
    if not session_file or not session_file.exists():
        return f"Session not found: {session_id}"
    
    messages = []
    try:
        with open(session_file) as f:
            for line in f:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        return f"Error reading session: {e}"
    
    if limit and limit > 0:
        messages = messages[:limit]
    
    if not messages:
        return "Session is empty"
    
    lines = [f"Session: {session_id}\nMessages: {len(messages)}\n"]
    
    for i, msg in enumerate(messages[:50]):  # Limit display
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
        content = content[:200] + "..." if len(content) > 200 else content
        lines.append(f"[{i+1}] {role}: {content}")
    
    if len(messages) > 50:
        lines.append(f"\n... and {len(messages) - 50} more messages")
    
    return "\n".join(lines)


def search_sessions(
    query: str,
    session_id: str | None = None,
    case_sensitive: bool = False,
    limit: int = 20,
) -> str:
    """
    Search across session messages.
    
    Args:
        query: Search query
        session_id: Search in specific session only
        case_sensitive: Case-sensitive search
        limit: Maximum results
        
    Returns:
        Search results with context.
    """
    sessions_dir = get_sessions_directory()
    results = []
    
    search_query = query if case_sensitive else query.lower()
    
    # Find session files to search
    session_files = []
    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue
        
        if session_id:
            for f in project_dir.glob(f"{session_id}*.jsonl"):
                session_files.append(f)
        else:
            session_files.extend(project_dir.glob("*.jsonl"))
    
    for session_file in session_files[:50]:  # Limit sessions to search
        try:
            with open(session_file) as f:
                for line_num, line in enumerate(f):
                    if not line.strip():
                        continue
                    
                    check_line = line if case_sensitive else line.lower()
                    if search_query in check_line:
                        try:
                            msg = json.loads(line)
                            content = msg.get("content", "")
                            if isinstance(content, list):
                                content = " ".join(
                                    str(c.get("text", "")) for c in content if isinstance(c, dict)
                                )
                            
                            results.append({
                                "session": session_file.stem[:12],
                                "line": line_num,
                                "role": msg.get("role", "unknown"),
                                "snippet": content[:150],
                            })
                            
                            if len(results) >= limit:
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception:
            continue
        
        if len(results) >= limit:
            break
    
    if not results:
        return f"No results for: {query}"
    
    lines = [f"Found {len(results)} matches for '{query}':\n"]
    for r in results:
        lines.append(f"  [{r['session']}] {r['role']}: {r['snippet']}...")
    
    return "\n".join(lines)


def get_session_info(session_id: str) -> str:
    """
    Get metadata about a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Session metadata and statistics.
    """
    sessions_dir = get_sessions_directory()
    
    # Find session file
    session_file = None
    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for f in project_dir.glob(f"{session_id}*.jsonl"):
            session_file = f
            break
        if session_file:
            break
    
    if not session_file or not session_file.exists():
        return f"Session not found: {session_id}"
    
    try:
        stat = session_file.stat()
        message_count = 0
        user_count = 0
        assistant_count = 0
        
        with open(session_file) as f:
            for line in f:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        message_count += 1
                        role = msg.get("role", "")
                        if role == "user":
                            user_count += 1
                        elif role == "assistant":
                            assistant_count += 1
                    except json.JSONDecodeError:
                        continue
        
        lines = [
            f"Session: {session_id}",
            f"File: {session_file}",
            f"Size: {stat.st_size / 1024:.1f} KB",
            f"Modified: {datetime.fromtimestamp(stat.st_mtime).isoformat()}",
            f"Messages: {message_count}",
            f"  User: {user_count}",
            f"  Assistant: {assistant_count}",
        ]
        return "\n".join(lines)
        
    except Exception as e:
        return f"Error: {e}"
