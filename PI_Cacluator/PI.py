import asyncio
import hashlib
import os
import random
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from mpmath import mp
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, ProgressBar, Static


def load_env_str(key: str, default: str = "") -> str:
    load_dotenv()
    return os.getenv(key, default)


class MatrixStream(Static):

    def on_mount(self) -> None:
        self.chars = [
            "0", "1", "2", "3", "4",
            "5", "6", "7", "8", "9",
            "π", "e", "i", "Σ", "√",
            "∞", "∫", "λ", "Δ", "Ω",
        ]

        self.set_interval(0.05, self.update_matrix)

    def update_matrix(self) -> None:
        width = max(self.size.width, 20)
        height = min(max(self.size.height, 4), 8)

        lines = [
            "".join(
                random.choice(self.chars)
                if random.random() > 0.32
                else " "
                for _ in range(width)
            )
            for _ in range(height)
        ]

        self.update("\n".join(f"[green]{line}[/green]" for line in lines))


class PiWorker:

    def __init__(self, digits: int):
        self.digits = digits
        self.result = None
        self.elapsed = 0.0
        self.error = None
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def calculate(self):
        try:
            start = time.perf_counter()

            mp.dps = self.digits + 20

            if self.cancel_event.is_set():
                return None

            result = mp.nstr(mp.pi, self.digits + 1)

            self.elapsed = time.perf_counter() - start
            self.result = result

            return result

        except Exception as exc:
            self.error = str(exc)
            return None


class PiMatrixEngine(App):

    TITLE = "PI MATRIX COMPUTATION ENGINE"

    CSS = """
    Screen {
        background: #050505;
        align: center middle;
    }

    #main-container {
        width: 95;
        height: 38;
        min-width: 80;
        min-height: 30;
        border: double #00ff00;
        background: #0b0b0b;
        padding: 1 2;
    }

    .title-banner {
        width: 100%;
        text-align: center;
        background: #002400;
        color: #00ff00;
        text-style: bold;
        border: solid #00aa00;
        margin-bottom: 1;
    }

    #input-block {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }

    #input-label {
        color: #00ff00;
        padding-top: 1;
    }

    Input {
        width: 30;
        border: solid #00aa00;
        color: #00ff00;
        background: #050505;
    }

    Input:focus {
        border: solid #00ff00;
    }

    Button {
        width: 22;
        background: #004400;
        color: white;
        border: none;
        margin-left: 1;
    }

    Button:hover {
        background: #00cc00;
        color: black;
    }

    Button:disabled {
        background: #222222;
        color: #666666;
    }

    #matrix-box {
        height: 7;
        border: solid #222222;
        margin: 1 0;
        overflow: hidden;
        background: #020202;
    }

    ProgressBar {
        width: 100%;
        margin-top: 1;
        margin-bottom: 1;
    }

    .status-panel {
        height: 8;
        background: #111111;
        border: tall #333333;
        padding: 0 1;
        margin-top: 1;
    }

    #metrics-panel {
        height: 7;
        background: #090909;
        border: solid #222222;
        padding: 0 1;
        margin-top: 1;
    }

    #preview-box {
        height: 5;
        background: #030303;
        color: #ff00ff;
        border: dashed #333333;
        padding: 0 1;
        overflow: hidden;
        margin-top: 1;
    }

    #checksum-box {
        color: #888888;
        margin-top: 1;
    }

    .green {
        color: #00ff00;
    }
    """

    BINDINGS = [
        ("q", "quit", "Exit"),
        ("c", "cancel", "Cancel"),
        ("r", "reset", "Reset"),
    ]

    status_msg = reactive("SYSTEM READY // IDLE")
    preview_msg = reactive("No calculation performed yet.")
    metrics_msg = reactive("Digits: -- | Time: -- | Speed: --")
    checksum_msg = reactive("SHA-256: --")
    calculating = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            yield Static(
                "PI MATRIX COMPUTATION ENGINE // ULTRA PRECISION",
                classes="title-banner",
            )

            with Horizontal(id="input-block"):
                yield Label(
                    "TARGET DIGITS:",
                    id="input-label",
                )

                yield Input(
                    placeholder="100000",
                    value="25000",
                    id="digit-input",
                )

                yield Button(
                    "LAUNCH ENGINE",
                    id="run-btn",
                )

                yield Button(
                    "CANCEL",
                    id="cancel-btn",
                    disabled=True,
                )

            with Container(id="matrix-box"):
                yield MatrixStream()

            yield Label("[bold yellow] COMPUTATION PIPELINE[/bold yellow]")

            yield ProgressBar(
                total=100,
                id="engine-progress",
            )

            with Vertical(classes="status-panel"):
                yield Label("[bold cyan] ENGINE LOG[/bold cyan]")

                self.log_label = Label(self.status_msg)

                yield self.log_label

            with Vertical(id="metrics-panel"):
                yield Label("[bold cyan] LIVE METRICS[/bold cyan]")

                self.metrics_label = Label(self.metrics_msg)

                yield self.metrics_label

            yield Label("[bold purple] PI PREVIEW[/bold purple]")

            self.preview_label = Static(
                self.preview_msg,
                id="preview-box",
            )

            self.checksum_label = Label(
                self.checksum_msg,
                id="checksum-box",
            )

        yield Footer()

    def watch_status_msg(self, message: str) -> None:
        if hasattr(self, "log_label"):
            self.log_label.update(message)

    def watch_preview_msg(self, message: str) -> None:
        if hasattr(self, "preview_label"):
            self.preview_label.update(message)

    def watch_metrics_msg(self, message: str) -> None:
        if hasattr(self, "metrics_label"):
            self.metrics_label.update(message)

    def watch_checksum_msg(self, message: str) -> None:
        if hasattr(self, "checksum_label"):
            self.checksum_label.update(message)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-btn":
            await self.start_engine()

        elif event.button.id == "cancel-btn":
            self.cancel_engine()

    async def start_engine(self) -> None:
        if self.calculating:
            return

        input_widget = self.query_one("#digit-input", Input)
        run_button = self.query_one("#run-btn", Button)
        cancel_button = self.query_one("#cancel-btn", Button)
        progress = self.query_one("#engine-progress", ProgressBar)

        raw = input_widget.value.strip()

        if not raw.isdigit():
            self.status_msg = "[bold red]ERROR: Invalid digit count.[/bold red]"
            return

        digits = int(raw)

        if digits <= 0:
            self.status_msg = (
                "[bold red]ERROR: Digit count must be positive.[/bold red]"
            )
            return

        if digits > 5_000_000:
            self.status_msg = (
                "[bold red]"
                "ERROR: Maximum configured limit is 5,000,000 digits."
                "[/bold red]"
            )
            return

        self.calculating = True

        run_button.disabled = True
        cancel_button.disabled = False
        input_widget.disabled = True

        progress.update(progress=0)

        self.preview_msg = "Initializing computation engine..."
        self.checksum_msg = "SHA-256: --"
        self.metrics_msg = f"Digits: {digits:,} | Time: -- | Speed: --"

        self.status_msg = (
            "[yellow]"
            "STAGE 01 // ALLOCATING PRECISION CONTEXT"
            "[/yellow]"
        )

        for value in range(20):
            progress.update(progress=value)
            await asyncio.sleep(0.015)

        self.status_msg = (
            "[cyan]"
            "STAGE 02 // INITIALIZING PRECISION ENGINE"
            "[/cyan]"
        )

        await asyncio.sleep(0.2)

        worker = PiWorker(digits)

        task = asyncio.create_task(
            asyncio.to_thread(worker.calculate)
        )

        while not task.done():
            if worker.cancel_event.is_set():
                self.status_msg = (
                    "[bold yellow]"
                    "CANCELLING COMPUTATION..."
                    "[/bold yellow]"
                )
                break

            current = progress.progress or 20

            if current < 82:
                progress.update(progress=current + 1)

            await asyncio.sleep(0.08)

        pi_str = await task

        if worker.cancel_event.is_set():
            self.status_msg = (
                "[bold yellow]"
                "COMPUTATION CANCELLED"
                "[/bold yellow]"
            )

            progress.update(progress=0)

            self.finish_engine(
                run_button,
                cancel_button,
                input_widget,
            )

            return

        if pi_str is None:
            self.status_msg = (
                "[bold red]"
                f"CALCULATION FAILED: {worker.error}"
                "[/bold red]"
            )

            self.finish_engine(
                run_button,
                cancel_button,
                input_widget,
            )

            return

        progress.update(progress=85)

        self.status_msg = (
            "[magenta]"
            "STAGE 03 // SERIALIZING HIGH-DENSITY PI STREAM"
            "[/magenta]"
        )

        await asyncio.sleep(0.2)

        filename = f"pi_matrix_{digits}_digits.txt"

        output_dir = Path(
            load_env_str(
                "PI_OUTPUT_DIR",
                "./DB/.TXT",
            )
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = output_dir / filename

        try:
            output_path.write_text(
                pi_str,
                encoding="utf-8",
            )

        except Exception as exc:
            self.status_msg = (
                "[bold red]"
                f"FILE ERROR: {exc}"
                "[/bold red]"
            )

            self.finish_engine(
                run_button,
                cancel_button,
                input_widget,
            )

            return

        progress.update(progress=92)

        self.status_msg = (
            "[cyan]"
            "STAGE 04 // GENERATING SHA-256 INTEGRITY HASH"
            "[/cyan]"
        )

        checksum = hashlib.sha256(
            pi_str.encode("utf-8")
        ).hexdigest()

        self.checksum_msg = f"SHA-256: {checksum}"

        progress.update(progress=97)

        elapsed = worker.elapsed

        speed = (
            digits / elapsed
            if elapsed > 0
            else 0
        )

        file_size = output_path.stat().st_size

        self.metrics_msg = (
            f"Digits: {digits:,} | "
            f"Time: {elapsed:.4f}s | "
            f"Speed: {speed:,.0f} digits/s | "
            f"File: {file_size:,} bytes"
        )

        preview_length = min(len(pi_str), 80)

        self.preview_msg = (
            pi_str[:preview_length]
            + ("..." if len(pi_str) > preview_length else "")
        )

        progress.update(progress=100)

        self.status_msg = (
            "[bold green]"
            f"SUCCESS // {digits:,} DIGITS COMPUTED"
            f" // {elapsed:.5f}s"
            "[/bold green]"
        )

        self.finish_engine(
            run_button,
            cancel_button,
            input_widget,
        )

    def cancel_engine(self) -> None:
        self.status_msg = (
            "[yellow]"
            "CANCEL REQUEST RECEIVED"
            "[/yellow]"
        )

    def action_reset(self) -> None:
        progress = self.query_one(
            "#engine-progress",
            ProgressBar,
        )

        input_widget = self.query_one(
            "#digit-input",
            Input,
        )

        input_widget.value = "25000"

        progress.update(progress=0)

        self.status_msg = "SYSTEM READY // IDLE"
        self.preview_msg = "No calculation performed yet."
        self.metrics_msg = "Digits: -- | Time: -- | Speed: --"
        self.checksum_msg = "SHA-256: --"

    def finish_engine(
        self,
        run_button: Button,
        cancel_button: Button,
        input_widget: Input,
    ) -> None:
        self.calculating = False

        run_button.disabled = False
        cancel_button.disabled = True
        input_widget.disabled = False


if __name__ == "__main__":
    app = PiMatrixEngine()
    app.run()