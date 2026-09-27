"""MCP server that drives the Affinity app through screenshots and mouse/keyboard (pyautogui)."""

import logging
import threading
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import Image, MCPServer

from . import gui_core
from .gui_core import Screen, ScreenState
from .result import Err, Result

log = logging.getLogger("affinity_mcp")

INSTRUCTIONS = """\
Controls the Affinity app (vector, pixel and layout design) on macOS through screenshots, mouse and keyboard.

SPEED: plan the whole step, then send it as ONE `batch` call (one screenshot at the end) instead of
many single calls. Use `menu` for anything that lives in a menu - it is exact and never misses.
Coordinates are pixels in the LAST screenshot; take a fresh one after the layout changes.

Batch step actions: click{x,y,button?,modifiers?}, double_click{x,y}, drag{x1,y1,x2,y2,duration?},
type{text,press_enter?}, key{key}, hotkey{keys}, scroll{amount,x?,y?}, field{x,y,value},
menu{path}, wait{seconds}.

Affinity facts (learned the hard way):
- New document: hotkey command+n, then Create Document (welcome tiles ignore synthetic clicks).
  Change size later with the Document Setup button (context toolbar, Move tool active).
- Shapes: draw a rough drag on the pasteboard, then type exact X/Y/W/H in the Transform panel
  (bottom right) and the fill in the Colour panel "#" field, each via a `field` step.
  Fields are committed with Enter; Tab jumps X -> Y -> W -> H.
- Press esc before drawing a new shape: while a panel field has focus the next drag edits the old shape.
- NEVER press Tab or Enter with the canvas focused: Tab hides all panels (press Tab again to restore),
  Enter opens Move/Duplicate. Pasting with the canvas focused creates a text object.
- Context-toolbar fields at the top (Corner %, stroke width) ignore synthetic clicks - use a shape
  that already has the property (Rounded Rectangle = 25% corners) or the Transform/Colour panels.
- Do not click the macOS menu bar - use `menu` (clicks there can open Mission Control).
- Multi-select layers: click the first row in the Layers panel, then click{modifiers:["command"]}.
- Booleans: menu ["Vector","Geometry","Add"|"Subtract"|"Intersect"|"Xor"|"Divide"] (prefix
  "Destructive " to bake the result). Subtract removes the upper shapes from the bottom one.
- Shortcuts: V move, A node, P pen, M rectangle, E ellipse, T text, command+j duplicate,
  command+g group, command+0 fit page, command+z undo, delete removes the selection.
- Export: menu ["File","Export…"] or the Export button in the top toolbar.
- Moving the mouse into a screen corner aborts automation (pyautogui failsafe).
Actions are performed as the user: confirm with them before overwriting, closing without saving or deleting files.
"""

APP = "Affinity"

mcp = MCPServer(name="affinity", instructions=INSTRUCTIONS)
state = ScreenState()
_screen: Screen | None = None
# The SDK runs sync tools in worker threads; parallel tool calls must not move the mouse at the same time.
_gui_lock = threading.Lock()


def get_screen() -> Screen:
    global _screen
    if _screen is None:
        from .gui_screen import MacScreen

        _screen = MacScreen()
    return _screen


def set_screen(screen: Screen) -> None:
    """Swap the screen (used by tests)."""
    global _screen
    _screen = screen
    state.image_width = state.image_height = 0


def snapshot(note: str) -> list[Any]:
    try:
        shot = gui_core.take_screenshot(get_screen(), state)
    except Exception as exc:
        log.exception("screenshot failed")
        return [f"{note}\nscreenshot failed: {type(exc).__name__}: {exc}"]
    if isinstance(shot, Err):
        return [f"{note}\nscreenshot failed: {shot.error}"]
    return [f"{note}\nscreenshot {shot.value.width}x{shot.value.height}", Image(data=shot.value.png, format="png")]


def act(operation: Callable[[Screen], Result[str]], screenshot_after: bool) -> list[str | Image]:
    with _gui_lock:
        return _act(operation, screenshot_after)


def _act(operation: Callable[[Screen], Result[str]], screenshot_after: bool) -> list[str | Image]:
    try:
        # another window (e.g. the terminal running the client) may take focus between calls
        get_screen().focus_app(APP)
        result = operation(get_screen())
    except Exception as exc:  # pyautogui failsafe, missing Accessibility permission, ...
        log.exception("GUI action failed")
        return [f"error: {type(exc).__name__}: {exc}"]
    if isinstance(result, Err):
        return [f"error: {result.error}"]
    if not screenshot_after:
        return [result.value]
    return snapshot(result.value)


@mcp.tool()
def screenshot() -> list[str | Image]:
    """Take a screenshot of the whole screen. Coordinates for other tools refer to this image."""
    with _gui_lock:
        # another window (e.g. the terminal running the client) may take focus between calls
        get_screen().focus_app(APP)
        return snapshot("ok")


@mcp.tool()
def click(x: int, y: int, button: str = "left", modifiers: list[str] | None = None,
          screenshot_after: bool = True) -> list[str | Image]:
    """Click at (x, y) in the last screenshot. button: left/right/middle; modifiers e.g. ["command"]."""
    return act(lambda s: gui_core.click(s, state, x, y, button, modifiers), screenshot_after)


@mcp.tool()
def double_click(x: int, y: int, screenshot_after: bool = True) -> list[str | Image]:
    """Double-click at (x, y) in the last screenshot."""
    return act(lambda s: gui_core.double_click(s, state, x, y), screenshot_after)


@mcp.tool()
def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5,
         screenshot_after: bool = True) -> list[str | Image]:
    """Drag with the left button from (x1, y1) to (x2, y2) in the last screenshot."""
    return act(lambda s: gui_core.drag(s, state, x1, y1, x2, y2, duration), screenshot_after)


@mcp.tool()
def type_text(text: str, press_enter: bool = False, screenshot_after: bool = True) -> list[str | Image]:
    """Type text into the focused field (via clipboard, so any language works). press_enter sends it."""
    return act(lambda s: gui_core.type_text(s, text, press_enter), screenshot_after)


@mcp.tool()
def press_key(key: str, screenshot_after: bool = True) -> list[str | Image]:
    """Press one key, e.g. enter, esc, tab, up, down, backspace."""
    return act(lambda s: gui_core.press_key(s, key), screenshot_after)


@mcp.tool()
def hotkey(keys: list[str], screenshot_after: bool = True) -> list[str | Image]:
    """Press a key combination, e.g. ["command", "n"] for a new document."""
    return act(lambda s: gui_core.hotkey(s, keys), screenshot_after)


@mcp.tool()
def scroll(amount: int, x: int | None = None, y: int | None = None, screenshot_after: bool = True) -> list[str | Image]:
    """Scroll: positive = up, negative = down. Pass x, y (last screenshot) to scroll over a specific area."""
    return act(lambda s: gui_core.scroll(s, state, amount, x, y), screenshot_after)


@mcp.tool()
def set_field(x: int, y: int, value: str, screenshot_after: bool = False) -> list[str | Image]:
    """Replace the value of a panel field at (x, y) (X/Y/W/H, colour hex, ...) and commit with Enter."""
    return act(lambda s: gui_core.set_field(s, state, x, y, value), screenshot_after)


@mcp.tool()
def menu(path: list[str], screenshot_after: bool = True) -> list[str | Image]:
    """Choose a menu item by path, e.g. ["Vector", "Geometry", "Add"]. Exact, no clicking."""
    return act(lambda s: gui_core.menu(s, APP, path), screenshot_after)


@mcp.tool()
def list_menu(path: list[str] | None = None) -> list[str | Image]:
    """List menu names: [] = menu bar, ["Vector"] = its items, ["Vector", "Geometry"] = submenu."""
    return act(lambda s: gui_core.menu_items(s, APP, path or []), False)


@mcp.tool()
def batch(steps: list[dict], screenshot_after: bool = True) -> list[str | Image]:
    """Run many GUI steps in one call, one screenshot at the end. Stops at the first failing step.

    Each step: {"action": ..., ...}. Actions: click{x,y,button?,modifiers?}, double_click{x,y},
    drag{x1,y1,x2,y2,duration?}, type{text,press_enter?}, key{key}, hotkey{keys},
    scroll{amount,x?,y?}, field{x,y,value}, menu{path}, wait{seconds}.
    Coordinates refer to the last screenshot taken before this call.
    """
    return act(lambda s: gui_core.batch(s, state, APP, steps), screenshot_after)


@mcp.tool()
def open_affinity(screenshot_after: bool = True) -> list[str | Image]:
    """Launch or bring the Affinity app to the front."""
    return act(lambda s: gui_core.open_app(s, APP), screenshot_after)


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
