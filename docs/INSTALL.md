# Copy CellKit into your project

CellKit has no pip dependencies and does not need to be installed globally.
Use Windows with Python 3.11 or newer, on the latest patch release of a
[supported Python version](https://devguide.python.org/versions/).
Python 3.10 is end-of-life and no longer recommended.

## 1. Copy this folder

Copy the complete **`cellkit`** folder from this repository into your project:

```text
your_project/
    main.py
    cellkit/          <-- copy this entire folder
        __init__.py
        app.py
        dialogs.py
        drawing.py
        effects.py
        tables.py
        terminal.py
        widgets.py
```

Keep all eight Python files together. You do **not** need `demos`, `examples`,
`tests`, `docs`, `tools`, or `__pycache__`. Copying the package is enough; there is
no `pip install` or `requirements.txt` step. Do not name your own script `cellkit.py`.

## 2. Create your application

Put this in `main.py`:

```python
from cellkit import App, Button, Label

app = App(min_width=40, min_height=12)
status = app.add(Label(2, 2, "Ready", width=35))

def clicked():
    status.text = "CellKit is working!"
    app.notify("Success", kind="success")

app.add(Button(2, 4, "Test", clicked))
app.add(Button(16, 4, "Exit", app.stop))

if __name__ == "__main__":
    app.run()
```

## 3. Run it in a terminal

Open PowerShell in `your_project` and run:

```powershell
python main.py
```

Use an interactive terminal, such as Windows Terminal or a Windows VS Code terminal.
An Output pane, PowerShell ISE, notebook or redirected input/output will not work.
This small app requires at least 41 physical columns and 12 rows; the library reserves
one terminal column to avoid wrapping.

## Running this repository's demos

From the repository root:

```powershell
python -m demos.background
python -m demos.dashboard
python -m demos.maze --theme violet
python -m demos.files
```

Or change into `demos` and run a script directly:

```powershell
cd demos
python background.py
python maze.py --theme amber
```

The demos include a small import-path bootstrap for direct execution. Your own
application does not need that bootstrap when `cellkit` is beside its script.

## If an import fails

Check that `cellkit/__init__.py` exists beside the script's directory and that you
copied every package file. Existing code written before the rename should use
`from cellkit import ...`. Restart a running demo after updating files; a Python
process keeps modules it has already imported in memory.

Continue with the [user guide](USER_GUIDE.md) or [API reference](API_REFERENCE.md).
