"""A small form: python -m examples.first_app"""

from cellkit import App, Button, Checkbox, Label, Panel, TextInput, Theme


def build_app():
    app = App(min_width=52, min_height=23)
    app.add(Panel(2, 1, 48, 20, "Report request"))
    app.add(Label(5, 4, "Report name", width=40, style=Theme.muted))
    name = app.add(TextInput(5, 5, 40, placeholder="For example: Monthly summary"))
    preview = app.add(Checkbox(5, 9, "Preview only", checked=True))
    status = app.add(Label(5, 12, "Fill in a name, then choose Submit.", width=40))

    def submit():
        report_name = name.value.strip()
        if not report_name:
            app.notify("Enter a report name first.", kind="warning")
            name.flash()
            app.set_focus(name)
            return
        mode = "Preview" if preview.checked else "Report"

        def confirmed(answer):
            if answer == "Confirm":
                status.text = f"{mode} requested: {report_name}"
                submit_button.flash()
                app.notify("Demo request accepted; no files were created.", kind="success")
            else:
                status.text = "Request cancelled."

        app.show_dialog("Confirm request", f"{mode}: {report_name}",
                        buttons=("Cancel", "Confirm"), on_result=confirmed)

    submit_button = app.add(Button(5, 15, "Submit", submit, width=18))
    app.add(Button(27, 15, "Exit", app.stop, width=12))
    app.add(Label(2, 22, "Tab: move focus | Enter: press | Esc: exit", width=48, style=Theme.muted))
    app.set_focus(name)
    return app


if __name__ == "__main__":
    build_app().run()
