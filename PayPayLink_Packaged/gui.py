import asyncio
import datetime
import os
import re
import sys

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Button, Header, Footer, Input, Label, RichLog

from paypay_link import checker, generator

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Running in a bundle (e.g., PyInstaller)
        base_path = sys._MEIPASS
    else:
        # Running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

def get_user_file_path(filename):
    """ Get the absolute path for user-generated files. """
    if getattr(sys, 'frozen', False):
        # Running in a bundle (e.g., PyInstaller)
        return os.path.join(os.path.dirname(sys.executable), filename)
    else:
        # Running in a normal Python environment
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

class PayPayApp(App):
    """A Textual app to generate and check PayPay links."""

    CSS_PATH = get_resource_path("style.css")

    # Store cancellation events
    _generation_cancel_event: asyncio.Event | None = None
    _checking_cancel_event: asyncio.Event | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        with Container(id="app-grid"):
            with VerticalScroll(id="left-pane"):
                yield Label("Generator", classes="title")
                yield Label("Number of links:")
                yield Input(value="10", id="gen-count", type="integer")
                yield Label("Delay (seconds):")
                yield Input(value="0", id="gen-delay", type="number")
                yield Label("Output file:")
                yield Input(value="paylink.txt", id="gen-output")
                yield Button("Generate Links", id="generate-button", variant="primary")
                yield Button(
                    "Cancel Generation",
                    id="cancel-gen-button",
                    variant="error",
                    disabled=True,
                )

                yield Label("Checker", classes="title")
                yield Label("Input file:")
                yield Input(value="paylink.txt", id="check-input")
                yield Label("Delay (milliseconds):")
                yield Input(value="3000", id="check-delay", type="integer")
                yield Label("Output file (success):")
                yield Input(value="success_link.txt", id="check-output")
                yield Button("Check Links", id="check-button", variant="success")
                yield Button(
                    "Cancel Checking",
                    id="cancel-check-button",
                    variant="error",
                    disabled=True,
                )

                yield Label("Simultaneously", classes="title")
                yield Label("Number of links to generate and check:")
                yield Input(value="10", id="sim-count", type="integer")
                yield Label("Generation Delay (seconds):")
                yield Input(value="0", id="sim-gen-delay", type="number")
                yield Label("Checking Delay (milliseconds):")
                yield Input(value="3000", id="sim-check-delay", type="integer")
                yield Label("Output file (success):")
                yield Input(value="success_link.txt", id="sim-output")
                yield Button(
                    "Generate and Check Simultaneously",
                    id="simultaneous-button",
                    variant="warning",
                )
                yield Button(
                    "Cancel Simultaneous",
                    id="cancel-simultaneous-button",
                    variant="error",
                    disabled=True,
                )

                yield Label("", classes="title") # Spacer
                yield Label("Developed by [link='https://github.com/opevista']Nisesimadao[/link]")
                yield Label("Original project: [link='https://github.com/Tettu0530/PayPaylink-Gen-Checker']Tettu0530/PayPaylink-Gen-Checker[/link]")

            with VerticalScroll(id="right-pane"):
                yield RichLog(id="log", wrap=True, highlight=True)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        log = self.query_one(RichLog)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if event.button.id == "generate-button":
            log.clear()
            log.write(f"--- Generation started at {timestamp} ---")
            self.query_one("#generate-button").disabled = True
            self.query_one("#cancel-gen-button").disabled = False
            self._generation_cancel_event = asyncio.Event()
            self.run_worker(self.run_generation, exclusive=True)

        elif event.button.id == "check-button":
            log.clear()
            log.write(f"--- Checking started at {timestamp} ---")
            self.query_one("#check-button").disabled = True
            self.query_one("#cancel-check-button").disabled = False
            self._checking_cancel_event = asyncio.Event()
            self.run_worker(self.run_checking, exclusive=True)

        elif event.button.id == "simultaneous-button":
            log.clear()
            log.write(
                f"--- Simultaneous generation and checking started at {timestamp} ---"
            )
            self.query_one("#simultaneous-button").disabled = True
            self.query_one("#cancel-simultaneous-button").disabled = False
            self._generation_cancel_event = asyncio.Event()
            self._checking_cancel_event = asyncio.Event()
            self.run_worker(self.run_simultaneously, exclusive=True, thread=True)

        elif event.button.id == "cancel-gen-button":
            if self._generation_cancel_event:
                self._generation_cancel_event.set()
                log.write(f"--- Generation cancellation requested at {timestamp} ---")
                self.query_one("#cancel-gen-button").disabled = True

        elif event.button.id == "cancel-check-button":
            if self._checking_cancel_event:
                self._checking_cancel_event.set()
                log.write(f"--- Checking cancellation requested at {timestamp} ---")
                self.query_one("#cancel-check-button").disabled = True

        elif event.button.id == "cancel-simultaneous-button":
            if self._generation_cancel_event:
                self._generation_cancel_event.set()
            if self._checking_cancel_event:
                self._checking_cancel_event.set()
            log.write(
                f"--- Simultaneous operation cancellation requested at {timestamp} ---"
            )
            self.query_one("#cancel-simultaneous-button").disabled = True

    async def run_generation(self) -> None:
        """Run the link generation in a background worker."""
        log = self.query_one(RichLog)
        count = int(self.query_one("#gen-count").value)
        delay = float(self.query_one("#gen-delay").value)
        output = get_user_file_path(self.query_one("#gen-output").value)

        def log_message(message):
            self.call_from_thread(log.write, message)

        try:
            await asyncio.to_thread(
                generator.generate_links,
                count,
                delay,
                output,
                logger=log_message,
                cancel_event=self._generation_cancel_event,
            )
        finally:
            self.query_one("#generate-button").disabled = False
            self.query_one("#cancel-gen-button").disabled = True
            self._generation_cancel_event = None

    async def run_checking(self) -> None:
        """Run the link checking in a background worker."""
        log = self.query_one(RichLog)
        input_file = get_user_file_path(self.query_one("#check-input").value)
        delay_ms = int(self.query_one("#check-delay").value)
        output_file = get_user_file_path(self.query_one("#check-output").value)

        def log_message(message):
            message = re.sub(r"\x1b\[[0-9;]*m", "", message)
            self.call_from_thread(log.write, message)

        try:
            await asyncio.to_thread(
                checker.check_links,
                input_file,
                delay_ms,
                output_file,
                logger=log_message,
                cancel_event=self._checking_cancel_event,
            )
        finally:
            self.query_one("#check-button").disabled = False
            self.query_one("#cancel-check-button").disabled = True
            self._checking_cancel_event = None

    def run_simultaneously(self) -> None:
        """Run generation and checking alternately in a background worker."""
        log = self.query_one(RichLog)
        count = int(self.query_one("#sim-count").value)
        gen_delay = float(self.query_one("#sim-gen-delay").value)
        check_delay_ms = int(self.query_one("#sim-check-delay").value)
        output_file = get_user_file_path(self.query_one("#sim-output").value)

        def log_message(message):
            message = re.sub(r"\x1b\[[0-9;]*m", "", message)
            self.call_from_thread(log.write, message)

        try:
            for i in range(count):
                if (
                    self._generation_cancel_event.is_set()
                    or self._checking_cancel_event.is_set()
                ):
                    log_message("--- Simultaneous operation cancelled ---")
                    break

                log_message(f"--- Generating link {i+1}/{count} ---")
                link = generator.generate_single_link(gen_delay, logger=log_message)

                if link is None:
                    log_message("--- Link generation failed ---")
                    continue

                log_message(f"--- Checking link: {link} ---")
                checker.check_single_link(
                    link,
                    check_delay_ms,
                    output_file,
                    logger=log_message,
                )
        finally:
            self.call_from_thread(
                self.query_one("#simultaneous-button").__setattr__, "disabled", False
            )
            self.call_from_thread(
                self.query_one("#cancel-simultaneous-button").__setattr__,
                "disabled",
                True,
            )
            self._generation_cancel_event = None
            self._checking_cancel_event = None


if __name__ == "__main__":
    app = PayPayApp()
    app.run()
