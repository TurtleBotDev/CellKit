"""The small example to read before exploring the larger dashboard demo."""


# Allow both `python FILE.py` here and `python -m demos.NAME` from the root.
if not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"

from cellkit import App, Button, Label, Panel

app = App(min_width=48, min_height=15)
app.add(Panel(2, 1, 44, 12, "My first terminal GUI"))
message = app.add(Label(5, 4, "Click the button below.", width=36))
clicks = 0


def say_hello():
    global clicks
    clicks += 1
    message.text = f"Hello! You pressed it {clicks} time(s)."


app.add(Button(5, 7, "Say hello", on_click=say_hello))
app.add(Button(23, 7, "Exit", on_click=app.stop))
app.add(Label(3, 14, "Mouse, Tab + Enter, or Esc to exit.", width=44))

if __name__ == "__main__":
    app.run()
