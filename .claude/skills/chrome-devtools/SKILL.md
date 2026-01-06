---
description: Browser automation with Chrome DevTools MCP. Use for web scraping, testing, screenshots, form filling, and browser interactions. Preferred over Playwright for direct browser control.
mcp:
  chrome-devtools:
    command: npx
    args: ["-y", "@anthropic/mcp-chrome-devtools"]
---

# Chrome DevTools Skill

Browser automation using the Chrome DevTools Protocol via MCP.

## When to Use

- Web scraping and data extraction
- UI testing and verification
- Taking screenshots of web pages
- Form filling and submission
- Browser-based automation tasks
- Debugging web applications

## Available Tools

### Navigation
- `navigate_page` - Navigate to URL, back, forward, or reload
- `new_page` - Create new browser tab
- `list_pages` - List all open pages
- `select_page` - Switch to a specific page
- `close_page` - Close a page

### Interaction
- `click` - Click on an element (supports double-click)
- `fill` - Type text into input/textarea or select option
- `fill_form` - Fill multiple form elements at once
- `hover` - Hover over an element
- `press_key` - Press keyboard keys or combinations
- `drag` - Drag element to another element
- `upload_file` - Upload file through file input

### Inspection
- `take_snapshot` - Get page content as a11y tree (preferred)
- `take_screenshot` - Capture page or element screenshot
- `list_console_messages` - Get browser console logs
- `get_console_message` - Get specific console message
- `list_network_requests` - List network activity
- `get_network_request` - Get request details

### Performance
- `performance_start_trace` - Start performance recording
- `performance_stop_trace` - Stop recording
- `performance_analyze_insight` - Analyze performance insights

### Dialogs & Emulation
- `handle_dialog` - Accept/dismiss browser dialogs
- `emulate` - Set network conditions, CPU throttling, geolocation
- `resize_page` - Resize browser window
- `wait_for` - Wait for text to appear

## Usage Pattern

1. **Start with snapshot**: Always use `take_snapshot` to get the current page state with element UIDs
2. **Use UIDs for interaction**: Elements in snapshot have `uid` identifiers - use these for clicks, fills, etc.
3. **Verify after actions**: Take another snapshot to verify state changes

## Example Workflow

```
1. navigate_page(url="https://example.com")
2. take_snapshot() -> get element UIDs
3. fill(uid="search-input", value="query")
4. click(uid="submit-button")
5. wait_for(text="Results")
6. take_snapshot() -> verify results
```

## Notes

- Prefer `take_snapshot` over `take_screenshot` for understanding page structure
- Use `wait_for` after navigation or clicks that trigger loading
- Console messages and network requests help debug issues
- Performance tracing is useful for optimization tasks
