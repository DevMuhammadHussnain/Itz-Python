#!/usr/bin/env python3
"""calc_service.py - runs the math engine in a separate process.

Why a process?  Some inputs (factoring a 100-digit semiprime, a huge integral ...)
can take forever.  Threads cannot be stopped, but a process can simply be killed.
When that happens the engine is restarted and your variables / functions / Ans /
memory are restored automatically.

This module only needs the standard library.
"""

from __future__ import annotations

import atexit
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

WORKER = Path(__file__).resolve().with_name("Calc_engine.py")


class EngineService:
    STARTUP_GRACE = 90.0        # extra seconds allowed while the engine (re)starts

    def __init__(self, timeout: float = 20.0, state: dict | None = None) -> None:
        self.timeout = timeout
        self.state: dict = state or {}          # latest restorable snapshot
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._proc: subprocess.Popen | None = None
        self._q: queue.Queue = queue.Queue()
        self._ready = False
        self._needs_restore = bool(self.state)
        self._spawn()                           # start importing SymPy right away
        atexit.register(self.close)

    # ---- process management ---------------------------------------------- #
    def _spawn(self) -> None:
        self._kill()
        self._ready = False
        extra = {}
        if sys.platform == "win32":
            extra["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [sys.executable, "-u", str(WORKER), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1, **extra)
        q: queue.Queue = queue.Queue()
        self._proc, self._q = proc, q
        threading.Thread(target=self._reader, args=(proc, q), daemon=True).start()

    @staticmethod
    def _reader(proc: subprocess.Popen, q: queue.Queue) -> None:
        try:
            for line in proc.stdout:            # type: ignore[union-attr]
                q.put(line)
        except Exception:
            pass
        finally:
            q.put(None)

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            pass
        try:
            proc.stdin.close()                  # type: ignore[union-attr]
        except Exception:
            pass

    def _respawn(self) -> None:
        self._needs_restore = bool(self.state)
        self._spawn()

    def close(self) -> None:
        proc = self._proc
        if proc is not None:
            try:
                proc.stdin.write(json.dumps({"op": "quit"}) + "\n")     # type: ignore[union-attr]
                proc.stdin.flush()                                      # type: ignore[union-attr]
            except Exception:
                pass
        self._kill()

    # ---- messaging ------------------------------------------------------------ #
    def _send(self, request: dict) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        self._proc.stdin.write(json.dumps(request) + "\n")
        self._proc.stdin.flush()

    def _receive(self, deadline: float):
        """Returns a reply dict, or one of the strings: cancelled / timeout / crashed."""
        while True:
            if self._cancel.is_set():
                return "cancelled"
            try:
                line = self._q.get(timeout=0.05)
            except queue.Empty:
                if time.monotonic() > deadline:
                    return "timeout"
                continue
            if line is None:
                return "crashed"
            msg = json.loads(line)
            if msg.get("ready"):
                self._ready = True
                continue
            return msg

    def _abort(self, reason: str, timeout: float) -> dict:
        self._respawn()
        text = {
            "cancelled": "Cancelled",
            "timeout": f"Stopped after {timeout:g}s - too slow (raise the limit with :timeout {int(timeout * 3)})",
            "crashed": "Engine crashed (out of memory?) and was restarted",
        }[reason]
        return {"ok": False, "error": text, "aborted": True}

    def call(self, request: dict, timeout: float | None = None, block: bool = True) -> dict | None:
        """Send one request and wait for the reply.

        block=False returns None immediately if the engine is busy (used by live preview).
        """
        if not self._lock.acquire(blocking=block):
            return None
        try:
            self._cancel.clear()
            timeout = timeout or self.timeout
            deadline = time.monotonic() + timeout + (0 if self._ready else self.STARTUP_GRACE)
            try:
                if self._needs_restore:
                    self._send({"op": "restore", "state": self.state})
                    reply = self._receive(deadline + 30)
                    if isinstance(reply, str):
                        return self._abort(reply, timeout)
                    self._needs_restore = False
                self._send(request)
            except (BrokenPipeError, OSError, ValueError):
                self._respawn()
                return {"ok": False, "error": "Engine restarted - please try again", "aborted": True}
            reply = self._receive(deadline)
            if isinstance(reply, str):
                return self._abort(reply, timeout)
            return reply
        finally:
            self._lock.release()

    def cancel(self) -> None:
        """Abort the running calculation (safe to call from any thread)."""
        self._cancel.set()