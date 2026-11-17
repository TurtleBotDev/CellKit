# CellKit API reference

Import public classes from `cellkit`. This reference describes the current source;
see the [user guide](USER_GUIDE.md) for complete usage patterns.

```python
from cellkit import (
    App, Widget, Label, Panel, Button, Checkbox, TextInput,
    ProgressBar, Table, ListBox, Canvas, Theme,
)
```

All positions and dimensions are integer character cells. Coordinates are absolute,
zero-based screen positions. Times are seconds unless otherwise stated.

## Application

### `App(min_width=40, min_height=12)`

`min_width` is usable width: the terminal needs one extra physical column. Construct
widgets before calling `run()`. Minimum dimensions should accommodate the layout.

| Method | Behaviour |
| --- | --- |
| `add(widget)` | Append a widget in drawing/Tab order; return it. |
| `run()` | Enter the alternate screen, process input and draw until stopped. |
| `stop()` | Request exit from the loop. |
| `set_focus(widget)` | Focus an eligible widget. `None` or an unavailable widget clears focus. |
| `notify(message, kind="info", duration=3.0)` | Show a toast; return its toast object. |
| `show_dialog(title, message, buttons=("OK",), on_result=None)` | Open a message dialog; return immediately. |
| `close_dialog(result=None)` | Close the active dialog, restore focus, then deliver the result callback. |
| `cancel_press()` | Clear widget mouse capture and its pressed state. Useful when manually switching screens. |

| Callback/property | Meaning |
| --- | --- |
| `on_tick(seconds)` | Runs each frame after effect timers advance. Keep it short. |
| `on_resize(width, height)` | Called for a new valid terminal size; receives usable dimensions. |
| `width`, `height` | Current usable dimensions, initially zero before running. |
| `focus` | Currently focused widget, or `None`. Use `set_focus()` to change it. |
| `dialog` | Active dialog, or `None`; useful for checking whether one is open. |
| `mouse_clicks` | Counts completed press/release gestures on eligible widgets, including table selection. |
| `widgets` | Widgets in drawing order. Prefer `add()` and visibility changes over ad hoc list mutation. |

`dispatch(event)`, `update(seconds)` and `render()` are lower-level entry points used
by the loop and tests. `render()` returns a `Canvas`; it does not write to the
terminal. Normal applications do not need to call these methods.

## Shared widget interface

### `Widget(x, y, width, height=1)`

| Property/method | Meaning |
| --- | --- |
| `x`, `y`, `width`, `height` | Bounds in screen cells. |
| `bounds(x, y, width, height=None)` | Change position/size; omitted height keeps its existing value. |
| `contains(x, y)` | Hit test; left/top included, right/bottom excluded. |
| `visible=True` | Draw and accept input when true. |
| `enabled=True` | Accept input when true. Disabled widgets remain drawn. |
| `focusable=False` | Override to true for a custom interactive widget. |
| `focused`, `hovered`, `pressed` | Input state maintained by App. |
| `flash(duration=1.8, interval=0.3, style=None)` | Alternate highlight/normal appearance. Duration zero cancels. |
| `draw(canvas)` | Override to draw custom content. |
| `activate()` | Override for normal click/Enter/Space activation. |
| `key(event)` | Override to handle focused keys. Base implementation activates on Enter/Space. |
| `mouse(event)` | Override to handle pointer coordinates and scrolling. |
| `style()` | Standard control style based on disabled/pressed/focus/hover state. |

Flash duration must be finite and non-negative; interval must be finite and positive.
`style=None` uses `Theme.pressed`. Timers advance without blocking input. Flash
overlays apply to app widgets, not the built-in dialog's separately drawn buttons.
Hidden widget timers still advance; disabled widgets do not show the highlight.

## Basic widgets

### `Label(x, y, text="", width=40, style=None)`

One line, height 1. Change `.text` and `.colour`. A `None` colour uses the current
`Theme.normal`. Content is clipped/padded to width. The constructor parameter is
called `style`; the stored property is called `colour`.

### `Panel(x, y, width, height, title="")`

A decorative border with a title. Change `.title`. Draw it before its contents.
It does not own children, perform layout, or clip child drawing.

### `Button(x, y, text, on_click=None, width=None)`

Height 3. Default width is the initial caption length plus four cells. Change
`.text` or `.on_click`. Callback signature: `on_click()`.

### `Checkbox(x, y, text, checked=False, on_change=None, width=None)`

Height 1. Default width is the initial caption length plus four cells. Change
`.text`, `.checked`, or `.on_change`. Activation toggles the state and calls
`on_change(checked)`. Direct assignment to `.checked` does not call it.

### `TextInput(x, y, width, value="", placeholder="", max_length=80)`

Height 3; initial width is at least 3. Properties: `.value`, `.cursor`,
`.placeholder`, `.max_length`. Constructor/typed input are cleaned to the engine's
single-cell character rules and limited to `max_length`.

When assigning `.value` yourself, validate/limit it and set `.cursor` to an integer
between zero and the new string length. There is no automatic submit, change
callback, clipboard support or mouse-positioned caret. Read `.value` in a button
callback or compare it in `on_tick`.

### `ProgressBar(x, y, width, value=0)`

Height 1. Set `.value` to a fraction from 0 to 1. Drawing clamps the range and
reserves five cells for a percentage. Use a width greater than five for a visible bar.

## Tables and lists

### `Table(x, y, width, height, columns, rows=(), title="", on_select=None, on_activate=None)`

- `columns`: `(heading, positive_integer_width)` pairs.
- `rows`: iterable of rows; each row is converted to a tuple.
- `on_select(index)`: selected integer index, or `None` for an empty table.
- `on_activate(index)`: called on Enter/Space or a completed double-click.

Construction selects the first row when present, without firing `on_select`.
Single clicks select but do not activate. `select()` and `set_rows()` fire
`on_select`, including repeated selection of the same row.

| Method/property | Meaning |
| --- | --- |
| `set_rows(rows, selected=0)` | Replace rows, reset scrolling, select/reveal the requested clamped index. |
| `select(index)` | Clamp an integer index, reveal it and call `on_select`. |
| `selected` | Current row index, or `None`; use `select()` instead of assigning directly. |
| `selected_row` | Selected tuple, or `None`. |
| `rows`, `columns`, `title` | Data, column definitions, title. Use `set_rows()` when replacing data. |
| `offset` | Index of first visible row. |
| `page_size` | Visible data rows: `height - 3` with a header, minimum 1. |
| `scroll(amount)` | Move viewport by a signed row count; positive moves down. Does not change selection. |
| `open_selection()` | Call `on_activate` if a row is selected. |

Text area width is `width - 3`. Each column separator uses three cells. Extra
content clips; there is no horizontal scrolling. Headers do not sort automatically.
Mouse-wheel input moves three rows per notch and does not steal focus. Row sorting
and filtering are application responsibilities.

### `ListBox(x, y, width, height, items=(), **kwargs)`

A Table with one column and no header. Optional keywords are `title`, `on_select`
and `on_activate`. `set_items(items, selected=0)` replaces items. Selection callbacks
and methods match Table; `.selected_row` is a one-element tuple. Page size is
`height - 2`, minimum 1.

## Dialogs and toasts

Use `App.show_dialog()` rather than constructing internal dialog classes.

- `buttons` must contain one to three non-empty string labels.
- `on_result(label)` runs after the dialog closes and focus is restored.
- Esc returns `None`; Ctrl+C exits the application.
- Only one dialog can be active; a second simultaneous `show_dialog()` raises
  `RuntimeError`. A result callback can open a follow-up dialog.
- Background input is blocked. Background updates continue.
- Text wraps and is shortened to fit. Dialogs have no scroll area or text fields.

`App.notify()` accepts `info`, `success`, `warning`, or `error`, and a finite,
positive duration. Up to three toasts are retained; only those fitting the screen
are drawn. Text is shortened after three wrapped lines. Notifications are drawn
behind an active modal dialog and do not take focus. Clicking dismisses a toast;
the click cannot reach underlying widgets. Dialog and toast validation errors are
raised as `ValueError` where applicable.

## Custom widgets and drawing

### Input event fields

The internal `Event` dataclass is available from `cellkit.terminal` for custom
integration/testing. Ordinary widgets receive events from App.

| Field | Meaning |
| --- | --- |
| `kind` | Widget hooks receive `key`, `down`, `move`, `up`, or `scroll` as appropriate. |
| `key` | Named key, or an empty string for an unnamed character key. |
| `text` | Character associated with a key; it may be empty or a control character. |
| `x`, `y` | Absolute screen-cell coordinates for pointer events. |
| `shift` | Whether Shift is held for a key event. |
| `delta` | Scroll notches; positive down, negative up. |
| `clicks` | Normally 1; 2 on the second press of a Windows double-click. |

Named keys include `backspace`, `tab`, `enter`, `escape`, `space`, `pageup`,
`pagedown`, `end`, `home`, `left`, `up`, `right`, `down`, `delete`, and `quit`
(Ctrl+C). App handles Tab, Esc and Ctrl+C before forwarding ordinary keys.

`resize` and `blur` are handled by App and are not forwarded to widget hooks. They
cancel capture. Mouse capture can deliver outside-bound drag/releases; `.pressed`
indicates whether the held pointer is currently over the captured control and is
cleared before `mouse(up)`. Normal release also calls `activate()` when appropriate.
Horizontal wheel events are currently ignored.

### `Canvas(width, height)`

| Method | Behaviour |
| --- | --- |
| `text(x, y, value, style=None, width=None)` | Single-line text. Optional width clips and pads; `None` style uses `Theme.normal`. |
| `box(x, y, width, height, title="", style=None)` | Border and filled interior. Default style is `Theme.border`. |
| `highlight(x, y, width, height, style)` | Recolour existing characters in a rectangle. |
| `changes(previous=None)` | Return ANSI output for changed rows. Used by App's renderer. |

Drawing clips to the canvas. Text is converted to strings. Unsupported wide
characters, combining marks and controls become `?`; embedded ANSI escapes in
text are not executed. Styles themselves are trusted application-defined numeric
ANSI parameters, such as `"1;38;2;91;224;197;48;2;16;22;34"`.

### `Theme`

Process-wide style roles: `normal`, `muted`, `accent`, `border`, `button`, `focus`,
`hover`, `pressed`, `disabled`, `warning`, `error`, and `input`. Configure them
before building widgets. An explicit style argument is a string snapshot; changing
the role later does not update that stored string automatically.
