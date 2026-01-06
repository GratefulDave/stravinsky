---
description: SQLite database operations via MCP. Use for local database queries, schema exploration, and data manipulation in SQLite files.
mcp:
  sqlite:
    command: npx
    args: ["-y", "@anthropic/mcp-server-sqlite", "--db-path", "./data.db"]
---

# SQLite Skill

Local SQLite database operations using MCP server.

## When to Use

- Local database queries and operations
- Prototyping before moving to production database
- Data analysis on SQLite files
- Schema exploration and documentation
- Test database setup and teardown

## Configuration

Specify the database path in the args:

```yaml
mcp:
  sqlite:
    command: npx
    args: ["-y", "@anthropic/mcp-server-sqlite", "--db-path", "./path/to/database.db"]
```

For in-memory database:

```yaml
mcp:
  sqlite:
    command: npx
    args: ["-y", "@anthropic/mcp-server-sqlite", "--db-path", ":memory:"]
```

## Available Tools

### Query Operations
- `read_query` - Execute SELECT queries (safe, read-only)
- `write_query` - Execute INSERT/UPDATE/DELETE queries
- `create_table` - Create new tables with schema

### Schema Operations
- `list_tables` - List all tables in the database
- `describe_table` - Get table schema (columns, types, constraints)

### Data Operations
- `insert_rows` - Bulk insert data
- `export_query` - Export query results

## Usage Pattern

1. **List tables first**: Use `list_tables` to understand database structure
2. **Describe before querying**: Use `describe_table` for column names and types
3. **Use read_query for exploration**: Safe, cannot modify data
4. **Backup before writes**: Always backup important data before modifications

## Example Workflow

```
1. list_tables() -> see available tables
2. describe_table(table_name="users") -> see columns
3. read_query(query="SELECT * FROM users LIMIT 10") -> preview data
4. write_query(query="UPDATE users SET status = 'active' WHERE id = 1")
```

## Notes

- Database file is created if it doesn't exist
- In-memory databases are lost when server stops
- Use `--db-path` to point to existing SQLite files
- Supports standard SQLite syntax and functions
