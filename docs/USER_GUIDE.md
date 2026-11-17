# CellKit user guide

CellKit helps you build clickable interfaces inside a Windows terminal using plain
Python. The Python package is called `cellkit`: you create an `App`, add widgets,
connect functions to their callbacks, and run the app.

There are no pip dependencies. Drawing uses character cells and colour sequences;
Python's built-in `ctypes` reads mouse and keyboard events from Windows.

This guide teaches the working patterns. The [API reference](API_REFERENCE.md)
lists the constructors, methods, callback arguments, and defaults.

## Contents

1. [Getting started](#getting-started)
2. [Your first application](#your-first-application)
3. [Coordinates, sizing and layout](#coordinates-sizing-and-layout)
4. [Widgets and callbacks](#widgets-and-callbacks)
5. [Tables and lists](#tables-and-lists)
6. [Dialogs and notifications](#dialogs-and-notifications)
7. [Colours and flashing](#colours-and-flashing)
8. [Updates and background work](#updates-and-background-work)
9. [Custom widgets](#custom-widgets)
10. [Switching screens](#switching-screens)
11. [Troubleshooting](#troubleshooting)
12. [How the engine works](#how-the-engine-works)

## Getting started

### Requirements

Use Windows and Python 3.10 or newer in an interactive terminal. Windows Terminal,
the Windows console, and Windows-based VS Code integrated terminals are the
intended hosts. Mouse forwarding and colours depend on the terminal host, so test
the terminal you actually use at work.

PowerShell is the shell that launches Python; the interface is drawn inside its
terminal. PowerShell ISE and IDE Output/Debug Console panes are not supported.
Neither are redirected input/output, Linux, macOS, or WSL Python.

### Run the examples

Open PowerShell in the project folder and run:

```powershell
python -m demos.hello
```

The larger demos need at least **80 columns and 31 rows**. Around 110 columns and
36 rows gives them more space. Enlarge the terminal or reduce its font size if the
app asks for more room.

| Command | What it demonstrates |
| --- | --- |
| `python -m demos.hello` | A label, two buttons and a callback |
| `python -m demos.dashboard` | Forms, simulated jobs, progress, charts, toasts and flashes |
| `python -m demos.maze --theme violet` | Drawing with the mouse, custom widgets and animated pathfinding |
| `python -m demos.maze --theme amber` | The same application in warm colours |
| `python -m demos.maze --theme ocean` | The same application in navy and teal |
| `python -m demos.files` | Lists, tables, filtering, folders and dialogs |
| `python -m demos.files "C:\Projects"` | Start the file browser in a particular folder |
| `python -m demos.background` | Hands-free recording: a repeating 60-second showcase |
| `python -m examples.first_app` | The small form explained below |
| `python -m examples.background_job` | A worker thread, progress and cancellation |

The operations dashboard and maze use simulated data. The file browser reads real
directories but does not edit, delete, or launch files. Its text preview reads at
most 4 KiB; it is not a full document viewer. Directory scans are capped at 2,000
entries and run on the UI thread, so slow network folders can delay input.

The automatic `background` showcase uses a synthetic file listing, requires no
interaction and cycles through all three larger demos. Use `--once` to stop after
one loop, or Esc to exit. From inside the `demos` folder you can also run
`python background.py` directly. This is separate from the worker-thread teaching
example in `examples/background_job.py`.

### Use CellKit in another project

Copy the entire `cellkit` directory beside your application file:

```text
my_tool/
    main.py
    cellkit/
        __init__.py
        app.py
        dialogs.py
        drawing.py
        effects.py
        tables.py
        terminal.py
        widgets.py
```

Then use `from cellkit import App, Button`. There is no installation step and the
demo files are not required. Avoid naming your application `cellkit.py`, which
would shadow the package.

See the [installation guide](INSTALL.md) for a complete copy-folder checklist and
a minimal application to verify the setup.

## Your first application

Save this complete example as `main.py` beside the `cellkit` directory:

```python
from cellkit import App, Button, Label, Panel


def build_app():
    app = App(min_width=50, min_height=16)
    app.add(Panel(2, 1, 46, 13, "My first tool"))
    status = app.add(Label(5, 4, "Ready when you are.", width=38))

    def run_task():
        status.text = "The button called a Python function."
        run_button.flash()
        app.notify("Task complete", kind="success")

    run_button = app.add(Button(5, 7, "Run task", on_click=run_task))
    app.add(Button(23, 7, "Exit", on_click=app.stop))
    app.add(Label(2, 15, "Click, or use Tab and Enter. Esc exits.", width=48))
    app.set_focus(run_button)
    return app


if __name__ == "__main__":
    build_app().run()
```

Run it with `python main.py`. Click **Run task**: the label changes, the button
flashes, and a success message appears.

`app.add()` returns the widget you added. Keep that object when you need to change
its properties later. `on_click=run_task` passes the function to the button;
`on_click=run_task()` would call it immediately, while building the interface.

`app.run()` owns the loop until the user exits. You do not need to call draw,
refresh, or update after changing a widget. The next frame picks up the change.

The [first-app example](../examples/first_app.py) extends this into a form with a
text field, a checkbox and confirmation. The snippets in the following sections
are building blocks: add them to an application before calling `app.run()`.

## Coordinates, sizing and layout

Everything is measured in **character cells**, not pixels. `(0, 0)` is the top-left
corner. `x` increases to the right; `y` increases downwards. Width and height include
a widget's border. A button and a text field are each three rows tall.

```python
panel = app.add(Panel(2, 2, 40, 12, "Settings"))
status = app.add(Label(4, 4, "Inside the panel", width=34))
```

Panels are decorative boxes. They do not contain or position other widgets: the
label's `(4, 4)` is still relative to the terminal. Hiding a panel does not hide the
widgets drawn over it. Add panels first, then their contents, because later widgets
draw on top of earlier ones. Drawing clips at the screen edge, not at panel borders.

### Terminal size and resizing

`min_width` is the required **usable** width. The engine reserves one physical
terminal column to prevent wrapping at the bottom-right corner. Consequently,
`App(min_width=79, min_height=31)` requires 80 terminal columns and 31 rows.

Use `app.on_resize` when positions should adapt:

```python
def layout(width, height):
    panel.bounds(2, 2, width - 4, height - 5)
    status.bounds(4, 4, width - 8)

app.on_resize = layout
```

The callback receives usable width and height. It runs on the initial valid size
and subsequent size changes large enough for the app. Keep minimum dimensions
large enough for your layout calculations. Below the minimum, a resize message
replaces the interface and ordinary input is ignored; updates still run. Esc and
Ctrl+C remain available.

### Visibility, enabled state and focus

```python
run_button.enabled = False
status.visible = False
app.set_focus(run_button)  # A disabled widget cannot receive focus.
```

Hidden and disabled widgets are skipped during keyboard navigation and hit testing.
Disabled controls remain drawn; not every decorative/custom widget changes its
colour when disabled. Set `enabled=True` before focusing a control again.

Tab and Shift+Tab follow the order in which you added focusable widgets. Clicking
a control gives it focus; clicking empty space normally clears focus. Set the
initial focus explicitly if you want Enter to work immediately.

| Input | Behaviour |
| --- | --- |
| Left press and release inside the same button | Activate the button |
| Press a button, drag outside, release | Cancel the activation |
| Tab / Shift+Tab | Next / previous available control |
| Enter / Space | Activate a focused button, checkbox or table/list row |
| Esc | Close a dialog, otherwise exit |
| Ctrl+C | Exit even when a dialog is open |

## Widgets and callbacks

### Labels and buttons

```python
from cellkit import Label, Button, Theme

status = app.add(Label(3, 3, "Ready", width=40, style=Theme.accent))

def refresh_status():
    status.text = "Updated"

refresh = app.add(Button(3, 5, "Refresh", on_click=refresh_status, width=14))
```

Labels are a single line. `width` clips long text and pads short text, clearing any
previous content. A button's callback takes no arguments. Change `button.text` to
update its caption; its width does not automatically grow with the new caption.

### Checkboxes

```python
from cellkit import Checkbox

def mode_changed(checked):
    status.text = "Preview mode" if checked else "Normal mode"

preview = app.add(Checkbox(3, 9, "Preview only", checked=True,
                           on_change=mode_changed))
```

The callback receives the new Boolean state. Read `preview.checked` whenever you
need it. Assigning `.checked` directly updates the state without calling the
callback; mouse/keyboard activation toggles it and calls the callback.

### Text fields

```python
from cellkit import TextInput

name = app.add(TextInput(3, 11, 40, placeholder="Job name", max_length=60))

def read_name():
    value = name.value.strip()
    if not value:
        app.notify("Please enter a name", kind="warning")
        app.set_focus(name)
        return
    status.text = "Selected: " + value
```

Text fields support arrows, Home, End, Backspace and Delete. Long values scroll
horizontally around the caret. Clicking focuses the field but does not place the
caret at the clicked character. Enter does not submit a form automatically; provide
a button for submission. There is no text-change callback. To react while typing,
compare `.value` with its previous value from `on_tick`, as `demos/files.py` does.

When replacing a field programmatically, update its cursor too:

```python
name.value = "Monthly report"[:name.max_length]
name.cursor = len(name.value)
```

The constructor and typed input apply the engine's single-cell text rules.
Direct property assignments do not enforce validation or the length limit. For
external text, use `clean_text` from `cellkit.drawing` before assigning a value.

### Progress bars

```python
from cellkit import ProgressBar

progress = app.add(ProgressBar(3, 15, 40, value=0))
progress.value = 0.65
```

Progress values are fractions: `0` means 0%, `0.65` means 65%, and `1` means 100%.
Rendering clamps values to that range. Reserve at least five cells for the
percentage, and more for the bar itself.

## Tables and lists

Tables keep row data separate from the screen. The callback receives a row index,
so you can map it to an object in your own list.

```python
from cellkit import Table

jobs = [("Monthly report", "Ready"), ("Invoice export", "Waiting")]

def open_job(index):
    title, state = table.rows[index]
    app.show_dialog(title, "Current state: " + state)

table = app.add(Table(2, 2, 60, 14,
    columns=[("Job", 32), ("State", 16)],
    rows=jobs, title="Jobs", on_activate=open_job))
```

Clicking selects; Enter, Space, or double-click activates. `on_select(index)` runs
when selection is applied, including programmatic `select()`/`set_rows()` calls.
It can receive `None` for an empty table, and can run even if the index did not
change. Construction chooses an initial row without calling `on_select`.

Use `table.selected_row` to read the selected tuple or `None`. Use
`table.select(index)` to select and reveal a row. Do not assign `.selected` directly
or mutate `.rows` in place when changing a dataset:

```python
table.set_rows([("Monthly report", "Complete")])
```

`set_rows()` resets selection to the first row and resets scrolling. Pass
`selected=some_index` to request a different selection; the index is clamped and
the viewport adjusted to reveal it. Sorting and filtering belong to your app.

The mouse wheel scrolls three rows per notch over a table without changing its
selection or taking focus. Arrow keys change selection. Page Up/Down move by a page;
Home/End select the first/last row. Clicking or dragging the scrollbar moves the
viewport. Keyboard selection brings an off-screen selected row back into view.

### Sizing a table

Column definitions are `(heading, width)` pairs. Use positive integer widths.
Three cells separate adjacent columns. The available text area is `table.width - 3`:

```text
sum(column widths) + 3 * (number of columns - 1) <= table.width - 3
```

Extra content is clipped; there is no horizontal scrolling or clickable-header
sorting. A table with a header shows `height - 3` data rows. A list shows
`height - 2`. Choose at least four rows of height for a table and three for a list.

### Lists

```python
from cellkit import ListBox

def open_place(index):
    app.notify("Selected: " + places.selected_row[0])

places = app.add(ListBox(2, 2, 24, 10,
    items=["Overview", "Reports", "History"],
    title="Sections", on_activate=open_place))
```

A `ListBox` is a one-column table without a header. It shares table navigation and
callbacks. Its selected row is still a tuple, such as `("Reports",)`. Replace data
with `places.set_items([...])`. The labels alone do not create pages or navigation.

## Dialogs and notifications

### Dialogs that wait for a choice

```python
def answered(choice):
    if choice == "Start":
        status.text = "Starting the job"
    else:
        status.text = "Cancelled"

app.show_dialog("Confirm", "Start this job?",
                buttons=("Cancel", "Start"), on_result=answered)
```

`show_dialog()` returns immediately. Put work that depends on the answer inside
`on_result`. The callback receives the chosen label, or `None` for Esc. Tab cycles
between the dialog's buttons. Mouse and keyboard input cannot reach background
widgets, but `on_tick` continues to run.

Closing a dialog restores the previous focus, if it is still available, before
calling the result callback. That callback may open a follow-up dialog. Opening
another dialog while one is already active raises `RuntimeError`.

Dialogs accept one to three non-empty button labels. Text wraps and is shortened
to fit; they do not have a scrolling document area or embedded form fields.
Call `app.close_dialog()` to close programmatically; this also calls `on_result`
with `None` unless you supply another result.

### Toast notifications

```python
app.notify("Report saved", kind="success", duration=3)
app.notify("Enter a job name", kind="warning")
app.notify("Could not read the file", kind="error", duration=5)
```

Kinds are `info`, `success`, `warning`, and `error`. Toasts do not take keyboard
focus. They expire automatically or dismiss when clicked. Their clicks are
consumed, so a button underneath will not activate accidentally.

Up to three toasts are retained, with the newest at the bottom right. Only those
that fit are drawn. Text wraps to at most three lines and is shortened if needed.
Treat toasts as brief feedback; use a dialog or log for longer explanations.

## Colours and flashing

### Flash an existing widget

```python
run_button.flash()  # 1.8 seconds, switching phase every 0.3 seconds
status.flash(duration=3, interval=0.4, style=Theme.accent)
run_button.flash(duration=0)  # Cancel
```

For white text on a **red background**, specify the full highlight style:

```python
run_button.flash(duration=2, style="1;38;2;255;255;255;48;2;180;35;45")
```

`Theme.error` uses red foreground text on the theme's normal background. The explicit
example above fills the button background red.

Flashing alternates a highlight with the widget's normal appearance. It does not
change the text, block callbacks, or pause the app. Disabled widgets do not flash.
The flash overlay works on ordinary app widgets and custom widgets; built-in
dialog buttons are drawn separately and do not use that overlay.

### Set colours

`Theme` stores ANSI style strings. These are numeric settings, not strings with
escape prefixes or CSS colour names. For example:

```python
from cellkit import Theme

Theme.accent = "1;38;2;241;159;217;48;2;28;19;43"
```

This means bold (`1`), foreground RGB `(241, 159, 217)` (`38;2`), and background RGB
`(28, 19, 43)` (`48;2`). The engine adds the escape sequence when it draws.

Theme settings are process-wide. Configure them **before creating widgets**.
Default label colours follow `Theme.normal`, but an explicit style such as
`Label(..., style=Theme.accent)` stores the style string passed at construction.
Changing `Theme.accent` later does not rewrite that label's `.colour` property.

For a complete palette, change the background in all relevant roles: `normal`,
`muted`, `accent`, `border`, `button`, `focus`, `hover`, `pressed`, `disabled`,
`warning`, `error`, and `input`. Custom drawings may have their own colours too.
See `PALETTES` and `apply_palette()` in [the maze demo](../demos/maze.py) for a working
RGB-hex example. `--theme` is an option in that demo, not a universal library option.

## Updates and background work

### Animate small amounts of work

`app.on_tick` receives the elapsed seconds since the previous frame:

```python
def tick(seconds):
    progress.value = min(1.0, progress.value + seconds * 0.1)

app.on_tick = tick
```

Use elapsed time instead of assuming a fixed frame rate. The event loop normally
waits up to 30 milliseconds for input, but callback time and terminal behaviour
affect the actual rate. Assigning `on_tick` or `on_resize` replaces the previous
callback; combine related updates in one function.

The maze demonstrates incremental work: expand a few cells, return control, then
continue on a later tick. This works well for algorithms you can split into short
steps.

### Keep slow work off the UI thread

A callback that calls `time.sleep()`, waits on a network request, or performs a long
loop prevents drawing and input processing. The UI does not run in another thread.

For blocking work, use `threading.Thread` and `queue.Queue` from the standard library:

1. A button starts a worker.
2. The worker puts progress/results into a queue.
3. `on_tick` drains that queue and updates widgets on the UI thread.
4. A `threading.Event` lets the worker notice cancellation.

The complete [background-job example](../examples/background_job.py) implements
this pattern, handles worker errors, prevents overlapping runs, and requests
cancellation on exit. Its short waits simulate work **inside the worker**. For a
real job, give blocking operations timeouts and define how they shut down; Python
cannot forcibly cancel an arbitrary thread.

Do not update widgets from a worker. Do not call `print()` or `input()` while the
interface is running: use labels, dialogs or a log widget instead.

## Custom widgets

Subclass `Widget`. Implement `draw(canvas)` and, for a clickable widget,
`activate()`. This example can be added to any app:

```python
from cellkit import Widget, Theme


class Counter(Widget):
    focusable = True

    def __init__(self, x, y):
        super().__init__(x, y, width=24, height=3)
        self.count = 0

    def draw(self, canvas):
        canvas.box(self.x, self.y, self.width, self.height, style=self.style())
        canvas.text(self.x + 2, self.y + 1, f"Count: {self.count}",
                    self.style(), width=self.width - 4)

    def activate(self):
        self.count += 1


counter = app.add(Counter(3, 3))
```

The base `key(event)` calls `activate()` for Enter/Space. App handles normal mouse
press/release activation and focus. Draw from current state, without changing that
state inside `draw()`; callbacks and updates should perform changes.

For more control, override `key(event)` and `mouse(event)`. Mouse events use absolute
screen-cell coordinates. Subtract `self.x` and `self.y` to obtain local coordinates.
The mouse hook receives `down`, `move`, `up`, and `scroll`. A captured widget can
receive drag/release events outside its rectangle. Check coordinates and
`self.pressed` before painting. On release, App clears `.pressed` before calling
the mouse hook. Resizing or losing window focus cancels capture.

Normal mouse release calls `activate()` after `mouse(event)` when the release is
over the pressed widget. Do not call `activate()` yourself from `mouse(up)` unless
you deliberately override the normal activation mechanism. The table keeps its
double-click action separate for this reason.

The canvas provides clipped `text()`, `box()` and `highlight()` methods. Text is
single-line; newlines and control characters do not create layout. See the
[event and drawing reference](API_REFERENCE.md#custom-widgets-and-drawing) for
field names and call signatures.

## Switching screens

There is no built-in page stack, router, or automatic Back history. For two small
screens, keep lists of their widgets and switch visibility. For example, after
creating `home_widgets`, `settings_widgets` and a focusable `settings_button`:

```python
def show_settings():
    app.cancel_press()
    for widget in home_widgets:
        widget.visible = False
    for widget in settings_widgets:
        widget.visible = True
    app.set_focus(settings_button)
```

Add all widgets once, keep inactive screen widgets hidden, and restore appropriate
focus when returning. Store your own history if needed. File-browser **Back** is
an example of application-owned folder history, not a generic page system.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `No module named cellkit` | Keep the full package beside your script; run the bundled `-m examples...` commands from the repository root. |
| The app asks for an interactive terminal | Use a real terminal, not ISE, an Output pane, a notebook, or redirected stdin/stdout. |
| Mouse clicks select text | Release Shift. The engine disables Windows Quick Edit while running, but the host may intercept clicks. Try another supported terminal and use Tab/Enter to distinguish host input issues. |
| Mouse wheel does nothing | Put the pointer over a table/list. Other widgets have no built-in scrolling. |
| Enter does nothing | Set focus on a button or row. Text fields do not automatically submit. |
| Widgets overlap or disappear | Check absolute coordinates, dimensions, and addition order. Panels do not lay out their contents. |
| Interface freezes during a task | Keep callbacks short; use incremental steps or a worker and queue. |
| Changing a theme leaves some old colours | Explicit styles are stored strings. Set the theme before construction or update those widgets' styles too. |
| The table is empty after filtering | `selected` and `selected_row` are `None`; handle that case before opening a row. |
| Characters become `?` | Wide characters, combining marks and controls are deliberately replaced to keep cell widths predictable. |

Basic Latin text and box drawing work best. Full emoji/CJK/grapheme support, text
selection, clipboard integration, screen-reader widget semantics, menus, dropdowns,
automatic layout, general scrolling containers and cross-platform input are not
implemented. Dialogs are messages with buttons, not general form containers.

## How the engine works

Each loop checks terminal size, advances effects, runs `on_tick`, draws a fresh
cell grid, writes changed rows, then reads and dispatches input. Windows events
arrive with character coordinates. App finds the eligible widget, tracks where a
press started, and routes the matching release or focused key event.

The alternate screen preserves the previous shell display. A context manager
restores console modes and returns to that display on normal exit and Python
exceptions. Abrupt process termination cannot run Python cleanup.

| File | Read it to understand |
| --- | --- |
| `cellkit/widgets.py` | Basic widget state, callbacks and flashes |
| `cellkit/tables.py` | Selection, viewport offsets, rows and scrollbars |
| `cellkit/app.py` | Input routing, focus, modal dialogs and the loop |
| `cellkit/drawing.py` | Cell grid, colours and changed-row rendering |
| `cellkit/effects.py` | Toast lifetime and placement |
| `cellkit/dialogs.py` | Dialog wrapping, size and buttons |
| `cellkit/terminal.py` | Isolated Windows API structures and console calls |

Run the tests from the repository root:

```powershell
python -m unittest discover -s tests -v
```

They include a separate hidden Windows console for native mouse/key/wheel input,
rendering and cleanup checks. They never inject input into your open PowerShell
window. Physical mouse forwarding still needs a check in your chosen terminal.

For the underlying platform behaviour, see Microsoft's documentation for
[console input](https://learn.microsoft.com/en-us/windows/console/reading-input-buffer-events),
[mouse records](https://learn.microsoft.com/en-us/windows/console/mouse-event-record-str),
and [terminal output sequences](https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences).
