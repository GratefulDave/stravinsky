#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


def get_project_dir():
    return Path(os.environ.get("CLAUDE_CWD", "."))


def get_dependency_graph():
    graph_file = get_project_dir() / ".claude/task_dependencies.json"
    if graph_file.exists():
        try:
            return json.loads(graph_file.read_text())
        except Exception:
            pass
    return {"dependencies": {}}


def save_dependency_graph(graph):
    graph_file = get_project_dir() / ".claude/task_dependencies.json"
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    graph_file.write_text(json.dumps(graph, indent=2))


DEPENDENCY_KEYWORDS = ["after", "depends on", "requires", "once", "when", "then"]
PARALLEL_KEYWORDS = ["also", "meanwhile", "simultaneously", "and", "plus"]


def parse_todo_dependencies(todos):
    dependencies = {}

    for todo in todos:
        todo_id = todo.get("id")
        content = todo.get("content", "").lower()

        has_dependency = any(kw in content for kw in DEPENDENCY_KEYWORDS)
        is_parallel = any(kw in content for kw in PARALLEL_KEYWORDS)

        dependencies[todo_id] = {
            "deps": [],
            "independent": not has_dependency,
            "parallel_safe": is_parallel or not has_dependency,
        }

    return dependencies


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "TodoWrite":
        return 0

    tool_input = hook_input.get("tool_input", {})
    todos = tool_input.get("todos", [])

    graph = get_dependency_graph()
    dependencies = parse_todo_dependencies(todos)
    graph["dependencies"] = dependencies
    save_dependency_graph(graph)

    return 0


if __name__ == "__main__":
    sys.exit(main())
