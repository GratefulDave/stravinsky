---
description: Supabase database operations via MCP. Use for PostgreSQL queries, authentication, storage, and real-time subscriptions in Supabase projects.
mcp:
  supabase:
    command: npx
    args: ["-y", "@supabase/mcp-server-supabase@latest", "--read-only"]
---

# Supabase Skill

Database and backend operations using Supabase MCP server.

## When to Use

- PostgreSQL database queries and operations
- User authentication and session management
- File storage operations
- Real-time subscription setup
- Database schema exploration
- Row-level security (RLS) policy management

## Configuration

The MCP server requires environment variables:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

Or pass project reference directly:

```yaml
mcp:
  supabase:
    command: npx
    args: ["-y", "@supabase/mcp-server-supabase@latest", "--project-ref", "your-project-ref"]
```

## Available Operations

### Database
- Query tables with full SQL support
- Insert, update, delete operations
- Schema introspection
- View and function management

### Authentication
- User management
- Session handling
- OAuth provider configuration

### Storage
- Bucket management
- File upload/download
- Signed URL generation

### Real-time
- Channel subscription setup
- Broadcast configuration
- Presence tracking

## Usage Pattern

1. **Explore schema first**: List tables and columns before querying
2. **Use parameterized queries**: Avoid SQL injection
3. **Check RLS policies**: Understand row-level security before operations
4. **Prefer --read-only**: Use read-only mode for exploration tasks

## Notes

- `--read-only` flag prevents destructive operations (recommended for exploration)
- Service role key bypasses RLS - use with caution
- For production, prefer anon key with proper RLS policies
