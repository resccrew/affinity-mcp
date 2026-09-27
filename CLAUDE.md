# affinity-mcp

## Purpose
MCP server (stdio) that drives the Affinity design app on macOS via screenshots + pyautogui:
the model looks at the screenshot and says where to click/drag/type. No API, no plugins.
Extracted from resccrew/telegram-mcp (its `affinity-gui` server) to be usable on its own.

## Stack
Python 3.13, uv, `mcp` 2.x SDK (`MCPServer`), pyautogui + Pillow, pytest + pytest-asyncio.

## Architecture
- `gui_core.py` — logic on a `Screen` protocol (screenshot downscale, image px → logical points,
  click/drag/type/scroll/hotkey). Returns `Result` (`result.py`), no business exceptions.
- `gui_screen.py` — real `MacScreen` (pyautogui lazily imported; Accessibility/Screen Recording checks).
- `server.py` — MCP tools; each action returns text + fresh screenshot; one lock for all GUI calls.
- `tests/test_gui.py` — `FakeScreen` (Retina-like 2880x1800 physical / 1440x900 logical).

## Key decisions
- Coordinates are always in the last screenshot's space (covers downscale + Retina).
- Before every action/screenshot Affinity is re-raised (`focus_app`) — the client's terminal steals
  focus between calls, and clicks/drags would land there.
- `open -a` + `osascript activate`: `open -a` alone doesn't raise an already-running app.
- Text typed via clipboard + cmd+v (Cyrillic/emoji), old clipboard restored; pbcopy with UTF-8 LANG.
- Nothing may print to stdout: it is the MCP protocol channel.

- Speed: `batch` runs many steps per call (one screenshot); `menu` goes through System Events
  (exact, no menu-bar clicks, which open Mission Control); `set_field` waits 0.35s so the panel re-focuses.
  Server INSTRUCTIONS hold the Affinity cheat-sheet (Tab hides panels, Enter opens Move/Duplicate...).

## Coding rules
Early returns, `Result` instead of raising; never modify existing tests to make them pass.

## Risks / limits
macOS only; controls the real mouse/keyboard; full-screen screenshots go to the model;
welcome-screen tiles ignore single synthetic clicks (use Cmd+N).

## Status
- 2026-09-28: fast tools (batch/menu/list_menu/set_field/modifier clicks), 29 tests; logo drawn live with them.
- 2026-09-27: 22 tests green, published as public repo, live-tested (new doc, rectangle via drag).
