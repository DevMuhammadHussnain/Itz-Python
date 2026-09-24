#!/usr/bin/env python3
"""Advanced Calculator - exact math, symbolic algebra and huge numbers in your terminal."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.markup import escape
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.widgets import (Button, Footer, Header, Input, Label, OptionList, Static,
                             TabbedContent, TabPane)

# Absolute import works whether run as a script or as a package
from Modules.Calc_service import EngineService

DATA_FILE = Path.home() / ".textual_calculator_v2.json"
MAX_HISTORY = 200
DATA_FILE = Path.home() / ".textual_calculator_v2.json"
MAX_HISTORY = 200


# --------------------------------------------------------------------------- #
#  Persistence (history + variables/functions/Ans/memory)
# --------------------------------------------------------------------------- #
def load_data() -> dict:
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        history = [h for h in raw.get("history", [])
                   if isinstance(h, dict) and "expr" in h and "result" in h]
        state = raw.get("state")
        return {"history": history[-MAX_HISTORY:], "state": state if isinstance(state, dict) else {}}
    except Exception:
        return {"history": [], "state": {}}


def save_data(history: list[dict], state: dict) -> None:
    try:
        DATA_FILE.write_text(json.dumps({"history": history[-MAX_HISTORY:], "state": state},
                                        ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass                                    # never crash because of persistence


# --------------------------------------------------------------------------- #
#  Keys
# --------------------------------------------------------------------------- #
class CalcButton(Button):
    """A button that knows what it does. Not focusable, so the input keeps focus."""

    can_focus = False

    def __init__(self, label: str, calc_action: str, calc_value: str = "",
                 variant: str = "default", **kwargs) -> None:
        super().__init__(label, variant=variant, **kwargs)
        self.calc_action = calc_action
        self.calc_value = calc_value


# (label, action, value, variant)
KEYS = [
    ("(", "insert", "(", "default"), (")", "insert", ")", "default"),
    ("x", "insert", "x", "default"), ("xʸ", "insert", "^", "warning"),
    ("⌫", "back", "", "error"),

    ("7", "insert", "7", "default"), ("8", "insert", "8", "default"),
    ("9", "insert", "9", "default"), ("÷", "insert", "/", "primary"),
    ("AC", "clear", "", "error"),

    ("4", "insert", "4", "default"), ("5", "insert", "5", "default"),
    ("6", "insert", "6", "default"), ("×", "insert", "*", "primary"),
    ("√", "insert", "sqrt(", "warning"),

    ("1", "insert", "1", "default"), ("2", "insert", "2", "default"),
    ("3", "insert", "3", "default"), ("−", "insert", "-", "primary"),
    ("Ans", "insert", "ans", "default"),

    ("0", "insert", "0", "default"), (".", "insert", ".", "default"),
    ("π", "insert", "pi", "default"), ("+", "insert", "+", "primary"),
    ("=", "equals", "", "success"),

    ("n!", "insert", "!", "warning"), ("%", "insert", "%", "warning"),
    ("e", "insert", "e", "default"), (",", "insert", ",", "default"),
    ("≈", "insert", "N(", "warning"),

    ("DEG", "angle", "", "default"), ("M+", "m+", "", "default"),
    ("M−", "m-", "", "default"), ("MR", "mr", "", "default"),
    ("MC", "mc", "", "default"),
]

# Function palettes: every entry inserts "name("
FUNC_TABS = {
    "Trig & Log": ["sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sec", "csc", "cot",
                   "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "deg", "rad", "ln",
                   "log", "log2", "exp", "sqrt", "cbrt", "root", "abs", "floor", "ceil",
                   "round", "sign"],
    "Algebra": ["solve", "nsolve", "simplify", "expand", "factor", "cancel", "apart",
                "together", "trigsimp", "subs", "N", "nsimplify", "diff", "integrate",
                "limit", "series", "sum", "prod"],
    "Numbers": ["isprime", "nextprime", "prevprime", "prime", "primepi", "factorint",
                "primefactors", "divisors", "totient", "divisor_count", "gcd", "lcm",
                "modinv", "powmod", "isqrt", "binomial", "perm", "factorial", "fibonacci",
                "lucas", "catalan", "bell", "harmonic", "bin", "hex", "oct", "base",
                "frombase", "popcount", "bitlen", "xor", "mod"],
    "Stats & Matrix": ["mean", "median", "stdev", "variance", "pstdev", "pvariance", "min",
                       "max", "hypot", "matrix", "det", "inv", "transpose", "rank", "trace",
                       "eigenvals", "identity", "dot", "cross", "norm", "re", "im", "conj",
                       "arg", "gamma", "erf", "zeta"],
}

HELP_TEXT = (
    "Type an expression and press Enter. Results are EXACT (1/3 stays 1/3) with a decimal "
    "approximation underneath.\n\n"
    "Big numbers: 2^100000, 1000!, fib(10^6), isprime(2^127-1) ... integers up to ~1.2M digits.\n"
    "Symbolic: solve(x^2-4, x), diff(sin(x), x), integrate(x^2,(x,0,1)), limit(sin(x)/x,x,0), "
    "sum(k^2,(k,1,100)), simplify(...)\n"
    "Define: a = 5   |   f(x) = x^2+1   then f(3)   |   :vars  :del a  :reset\n"
    "Digits: N(pi, 100)   or   :prec 100    Angle: :deg / :rad (F2)\n"
    "Also: 5!  15%  2x  3(4+5)  √16  0xFF  0b101  I (imaginary)  ans  *2 (continues from ans)\n"
    "Matrices: matrix([[1,2],[3,4]]), det, inv, transpose ...\n"
    "Symbolic trig always uses radians. Slow? Esc cancels; :timeout 60 allows longer.\n"
    ":save file.txt writes the full last result to disk.\n"
    "Keys: F2 DEG/RAD · F3 clear history · F4 theme · F5 copy · F8 copy decimal · F6 history"
)


def make_input() -> Input:
    kwargs = dict(placeholder="Type an expression, e.g. 2^1000, solve(x^2-2,x), 100!   (F1 = help)",
                  id="expr")
    try:
        return Input(select_on_focus=False, **kwargs)
    except TypeError:                           # older Textual without select_on_focus
        return Input(**kwargs)


# --------------------------------------------------------------------------- #
#  App
# --------------------------------------------------------------------------- #
class CalculatorApp(App):
    TITLE = "Advanced Calculator"
    SUB_TITLE = "exact · symbolic · unlimited size"

    CSS = """
    #main { height: 1fr; }
    #calc { width: 1fr; padding: 1 2; }
    #preview { height: 1; color: $text-muted; padding: 0 1; }
    #result-box { height: auto; min-height: 5; max-height: 14; background: $boost; padding: 0 1; }
    #res-exact { width: 100%; text-style: bold; }
    #res-exact.error { color: $error; }
    #res-approx { width: 100%; color: $text-muted; }
    #res-pretty { width: 100%; }
    #res-info { height: 1; color: $text-muted; padding: 0 1; }
    #status { height: 1; color: $accent; padding: 0 1; margin-bottom: 1; }
    TabbedContent { height: auto; }
    TabPane { padding: 0; height: auto; }
    #keys { grid-size: 5; grid-rows: 3; grid-gutter: 0 1; height: 21; }
    .fn-grid { grid-size: 4; grid-rows: 1; grid-gutter: 0 1; margin-top: 1; }
    CalcButton { width: 100%; min-width: 5; }
    CalcButton.fn { height: 1; border: none; min-width: 8; }
    #history-panel { width: 38; border-left: tall $primary; }
    #history-title { padding: 0 1; text-style: bold; width: 100%; background: $boost; }
    #history { height: 1fr; }
    """

    BINDINGS = [
        Binding("escape", "cancel_or_clear", "Clear/Cancel"),
        Binding("f1", "show_help", "Help"),
        Binding("f2", "toggle_angle", "DEG/RAD"),
        Binding("f3", "clear_history", "Clear history"),
        Binding("f4", "toggle_theme", "Theme"),
        Binding("f5", "copy_result", "Copy"),
        Binding("f8", "copy_approx", "Copy ≈"),
        Binding("f6", "toggle_history", "History"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        data = load_data()
        self.history: list[dict] = data["history"]
        self.service = EngineService(timeout=20.0, state=data["state"])
        self.calc_status: dict = {"angle": "DEG", "prec": 30, "ans": "0", "memory": "", "defs": 0}
        self.busy = False
        self.last: dict = {}
        self._preview_timer = None

    # ---- layout ---------------------------------------------------------- #
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with VerticalScroll(id="calc"):
                yield make_input()
                yield Static("", id="preview", markup=False)
                with VerticalScroll(id="result-box"):
                    yield Static("0", id="res-exact", markup=False)
                    yield Static("", id="res-approx", markup=False)
                    yield Static("", id="res-pretty", markup=False)
                yield Static("", id="res-info", markup=False)
                yield Static("", id="status", markup=False)
                with TabbedContent(initial="tab-keypad"):
                    with TabPane("Keypad", id="tab-keypad"):
                        with Grid(id="keys"):
                            for label, action, value, variant in KEYS:
                                extra = {"id": "btn-angle"} if action == "angle" else {}
                                yield CalcButton(label, action, value, variant, **extra)
                    for i, (title, names) in enumerate(FUNC_TABS.items()):
                        with TabPane(title, id=f"tab-fn{i}"):
                            with Grid(classes="fn-grid") as grid:
                                grid.styles.height = -(-len(names) // 4)
                                for name in names:
                                    yield CalcButton(name, "insert", name + "(", "default",
                                                     classes="fn")
            with Vertical(id="history-panel"):
                yield Label("History  (click to reuse)", id="history-title")
                yield OptionList(id="history")
        yield Footer()

    def on_mount(self) -> None:
        self.expr_input.focus()
        self.rebuild_history()
        self.set_info("Starting math engine …")
        self._warm_up()

    def on_unmount(self) -> None:
        self.service.close()

    # ---- helpers ------------------------------------------------------------- #
    @property
    def expr_input(self) -> Input:
        return self.query_one("#expr", Input)

    def set_info(self, text: str) -> None:
        self.query_one("#res-info", Static).update(text)

    def apply_status(self, st: dict) -> None:
        self.calc_status = st
        self.query_one("#status", Static).update(
            f"{st['angle']}  ·  {st['prec']} digits  ·  M: {st.get('memory') or '–'}  ·  "
            f"Ans: {st['ans']}  ·  {st['defs']} defs")
        try:
            self.query_one("#btn-angle", CalcButton).label = st["angle"]
        except Exception:
            pass

    def show_result(self, res: dict) -> None:
        exact = res.get("exact", "")
        if res.get("name"):
            exact = f"{res['name']} = {exact}"
        widget = self.query_one("#res-exact", Static)
        widget.update(exact)
        widget.set_class(False, "error")
        widget.styles.text_align = "right" if (len(exact) < 45 and "\n" not in exact) else "left"
        approx = res.get("approx", "")
        self.query_one("#res-approx", Static).update(f"≈ {approx}" if approx else "")
        self.query_one("#res-pretty", Static).update(res.get("pretty", ""))
        elapsed = res.get("elapsed", 0.0)
        parts = [res.get("info", "")]
        if elapsed >= 0.05:
            parts.append(f"{elapsed * 1000:.0f} ms" if elapsed < 1 else f"{elapsed:.2f} s")
        self.set_info("  ·  ".join(p for p in parts if p))

    def show_error(self, message: str) -> None:
        widget = self.query_one("#res-exact", Static)
        widget.update(message)
        widget.set_class(True, "error")
        widget.styles.text_align = "left"
        self.query_one("#res-approx", Static).update("")
        self.query_one("#res-pretty", Static).update("")
        self.set_info("")

    def rebuild_history(self) -> None:
        option_list = self.query_one("#history", OptionList)
        option_list.clear_options()
        if self.history:
            option_list.add_options([
                Text.assemble((h["expr"] + "\n", "dim"), ("= " + h["result"], "bold"))
                for h in reversed(self.history)
            ])

    # ---- engine workers (run in threads so the UI never blocks) --------------------- #
    @work(thread=True, group="warmup")
    def _warm_up(self) -> None:
        reply = self.service.call({"op": "ping"})
        self.call_from_thread(self._engine_ready, reply)

    def _engine_ready(self, reply: dict | None) -> None:
        if reply and reply.get("ok") and reply.get("status"):
            self.apply_status(reply["status"])
            self.set_info("Ready")
        elif reply and reply.get("error"):
            self.set_info("Engine problem: " + reply["error"])

    @work(thread=True, exclusive=True, group="calc")
    def _eval_worker(self, text: str, from_input: bool) -> None:
        reply = self.service.call({"op": "eval", "text": text, "commit": True})
        self.call_from_thread(self._finish_eval, text, reply, from_input)

    @work(thread=True, exclusive=True, group="calc")
    def _memory_worker(self, action: str, text: str) -> None:
        reply = self.service.call({"op": "memory", "action": action, "text": text})
        self.call_from_thread(self._finish_memory, action, reply)

    @work(thread=True, exclusive=True, group="preview")
    def _preview_worker(self, text: str) -> None:
        reply = self.service.call({"op": "eval", "text": text, "commit": False, "light": True},
                                  timeout=4.0, block=False)
        value = ""
        if reply and reply.get("ok"):
            res = reply["result"]
            if res.get("full", "") != text:
                value = "= " + res["exact"].split("\n")[0]
                if res.get("approx"):
                    value += "   ≈ " + res["approx"]
                if len(value) > 90:
                    value = value[:89] + "…"
        self.call_from_thread(self._set_preview, text, value)

    def _set_preview(self, text: str, value: str) -> None:
        if self.expr_input.value.strip() == text:
            self.query_one("#preview", Static).update(value)

    def _start_eval(self, text: str, from_input: bool = True) -> None:
        if self.busy:
            self.notify("Still calculating - press Esc to cancel", severity="warning")
            return
        self.busy = True
        self.set_info("Calculating …  (Esc to cancel)")
        self._eval_worker(text, from_input)

    def _finish_eval(self, text: str, reply: dict | None, from_input: bool) -> None:
        self.busy = False
        if not reply:
            self.show_error("Engine unavailable")
            return
        if reply.get("status"):
            self.apply_status(reply["status"])
        if reply.get("state") is not None:
            self.service.state = reply["state"]
        if not reply.get("ok"):
            self.show_error(reply.get("error") or "Error")
            return

        res = reply["result"]
        self.last = res
        self.show_result(res)
        if res.get("kind") not in ("command", "memory"):
            short = res.get("exact", "").replace("\n", " ")
            if res.get("name"):
                short = f"{res['name']} = {short}"
            self.history.append({"expr": text, "result": short if len(short) <= 60 else short[:59] + "…"})
            self.history = self.history[-MAX_HISTORY:]
            self.rebuild_history()
        save_data(self.history, self.service.state)
        if from_input:
            self.expr_input.value = ""

    def _finish_memory(self, action: str, reply: dict | None) -> None:
        self.busy = False
        if not reply:
            return
        if reply.get("status"):
            self.apply_status(reply["status"])
        if reply.get("state") is not None:
            self.service.state = reply["state"]
            save_data(self.history, self.service.state)
        if not reply.get("ok"):
            self.notify(escape(reply.get("error") or "Error"), severity="error")
            return
        res = reply["result"]
        if action == "mr":
            self.expr_input.insert_text_at_cursor(res.get("full", "0"))
        else:
            self.notify(escape(res.get("exact", "")))

    # ---- events ---------------------------------------------------------------------- #
    def on_input_changed(self, event: Input.Changed) -> None:
        if self._preview_timer is not None:
            self._preview_timer.stop()
        text = event.value.strip()
        if not text or text.startswith(":"):
            self.query_one("#preview", Static).update("")
            return
        self._preview_timer = self.set_timer(0.3, lambda: self._preview_worker(text))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.calculate()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        if isinstance(button, CalcButton):
            self.handle_key(button.calc_action, button.calc_value)
            self.expr_input.focus()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.expr_input.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        entries = self.history[::-1]
        if 0 <= event.option_index < len(entries):
            inp = self.expr_input
            inp.value = entries[event.option_index]["expr"]
            inp.focus()
            inp.cursor_position = len(inp.value)

    # ---- actions ---------------------------------------------------------------------- #
    def handle_key(self, action: str, value: str) -> None:
        inp = self.expr_input
        if action == "insert":
            inp.insert_text_at_cursor(value)
        elif action == "back":
            inp.action_delete_left()
        elif action == "clear":
            self.action_clear_input()
        elif action == "equals":
            self.calculate()
        elif action == "angle":
            self.action_toggle_angle()
        elif action in ("m+", "m-", "mr", "mc"):
            if self.busy:
                return
            self.busy = True
            self._memory_worker(action, inp.value)

    def calculate(self) -> None:
        text = self.expr_input.value.strip()
        if not text:
            return
        if text.lower().startswith(":timeout"):
            try:
                seconds = float(text.split()[1])
                if not 1 <= seconds <= 3600:
                    raise ValueError
                self.service.timeout = seconds
                self.show_result({"exact": f"Time limit per calculation: {seconds:g} s"})
            except (IndexError, ValueError):
                self.show_error("Usage: :timeout 60   (seconds, 1..3600)")
            self.expr_input.value = ""
            return
        self._start_eval(text, from_input=True)

    def action_clear_input(self) -> None:
        self.expr_input.value = ""
        self.show_result({"exact": "0"})
        self.query_one("#preview", Static).update("")

    def action_cancel_or_clear(self) -> None:
        if self.busy:
            self.service.cancel()
        else:
            self.action_clear_input()

    def action_toggle_angle(self) -> None:
        self._start_eval(":rad" if self.calc_status.get("angle") == "DEG" else ":deg", from_input=False)

    def action_clear_history(self) -> None:
        self.history.clear()
        save_data(self.history, self.service.state)
        self.rebuild_history()
        self.notify("History cleared")

    def action_toggle_theme(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

    def action_toggle_history(self) -> None:
        panel = self.query_one("#history-panel")
        panel.display = not panel.display

    def _copy(self, text: str, what: str) -> None:
        if not text:
            self.notify("Nothing to copy yet", severity="warning")
            return
        try:
            self.copy_to_clipboard(text)
            self.notify(f"Copied {what} ({len(text):,} characters)")
        except Exception:
            self.notify("Clipboard not available here - use  :save file.txt", severity="warning")

    def action_copy_result(self) -> None:
        self._copy(self.last.get("full", ""), "result")

    def action_copy_approx(self) -> None:
        self._copy(self.last.get("approx", ""), "decimal value")

    def action_show_help(self) -> None:
        self.notify(escape(HELP_TEXT), title="Advanced Calculator", timeout=30)


def main() -> None:
    import importlib.util
    if importlib.util.find_spec("sympy") is None:
        sys.exit("SymPy is required.  Install everything with:  pip install -r requirements.txt")
    engine_path = Path(__file__).resolve().parent / "Modules" / "Calc_engine.py"
    if not engine_path.exists():
        sys.exit(f"calc_engine.py must be at {engine_path}")

    CalculatorApp().run()          # ← add this line

if __name__ == "__main__":
    main()