# affinity-mcp

An MCP server that lets Claude (Claude Code, Claude Desktop or any MCP client) use the
[Affinity](https://www.affinity.studio) design app on macOS the way a person would: it looks at
screenshots, then clicks, drags, types and presses shortcuts.

Affinity has no scripting API, so this works with any version and any studio (Vector, Pixel,
Layout). You don't need API keys or plugins.

## Tools

| Tool | What it does |
|---|---|
| `open_affinity` | Launch Affinity or bring it to the front |
| `screenshot` | Screenshot of the screen (downscaled to 1280 px); all coordinates refer to the last one |
| `click` | Left/right/middle click at (x, y) |
| `double_click` | Double-click at (x, y) |
| `drag` | Drag from (x1, y1) to (x2, y2): draw shapes, move objects, drag sliders |
| `type_text` | Type text (via clipboard, so Cyrillic and emoji work) |
| `press_key` | One key: `enter`, `esc`, `tab`, `v` (Move tool), `m` (Rectangle)... |
| `hotkey` | Key combo, e.g. `["command", "n"]` new document, `["command", "z"]` undo |
| `scroll` | Scroll, optionally over a given point |
| `set_field` | Set a panel field (X/Y/W/H, colour hex...) and commit it |
| `menu` | Choose any menu item by path, e.g. `["Vector","Geometry","Add"]`, with no clicks |
| `list_menu` | List menu names, so the model can find the exact path |
| `batch` | Run many steps in one call and return one screenshot at the end, which is the fast path |

`click` also accepts `modifiers` (e.g. `["command"]` for multi-select).

Every action returns a fresh screenshot by default (`screenshot_after=false` turns it off).
Before every action the server brings Affinity back to the front, so the terminal can't take the clicks.

## Requirements

- macOS, Python 3.13+, [uv](https://docs.astral.sh/uv/)
- Affinity installed (`/Applications/Affinity.app`)
- Permissions for the app that runs your MCP client (Terminal, iTerm, Ghostty, VS Code, Claude):
  **System Settings → Privacy & Security → Accessibility** and **Screen Recording**.
  Without them, macOS silently ignores clicks and returns an empty screenshot. The server detects
  this and tells you what's missing.

## Install

```bash
git clone https://github.com/resccrew/affinity-mcp.git
cd affinity-mcp
uv sync
```

### Claude Code

```bash
claude mcp add -s user affinity -- uv --directory /path/to/affinity-mcp run affinity-mcp
```

### Claude Desktop

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "affinity": {
      "command": "uv",
      "args": ["--directory", "/path/to/affinity-mcp", "run", "affinity-mcp"]
    }
  }
}
```

Restart the client, then ask e.g. *"open Affinity, create an A4 document and draw a red circle"*.

## Tips

- Keyboard shortcuts are more reliable than clicking small icons: `Cmd+N` creates a document
  (tiles on the welcome screen ignore single synthetic clicks).
- Coordinates are always relative to the **last** screenshot. The server maps them to real screen
  points, including Retina scaling.

## Safety

- The server moves your real mouse and keyboard, so don't use the computer while it works.
  To abort, move the mouse into any screen corner (pyautogui failsafe).
- Screenshots of the whole screen go to the model, so close windows with private data first.

## Development

```bash
uv run pytest
```

Tests use a fake screen and need no display or permissions.

## License

MIT
