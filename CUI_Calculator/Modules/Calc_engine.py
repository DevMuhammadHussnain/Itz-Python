#!/usr/bin/env python3
"""calc_engine.py - exact, arbitrary-precision math engine (SymPy based).

Normally this module is run as a *worker process* by calc_service.py, so a
runaway calculation can be cancelled by simply killing the process.

Highlights
  * exact integers of any practical size, exact fractions (1/3 stays 1/3)
  * symbolic algebra & calculus (solve, diff, integrate, limit, series ...)
  * arbitrary-precision decimals (default 30 digits, up to 5000)
  * number theory (primes, factorisation, modular arithmetic ...)
  * matrices, statistics, base conversion, bit operations
  * expressions are parsed with `ast` and evaluated by a whitelist - no eval()
"""

from __future__ import annotations

import ast
import io
import json
import math
import re
import sys
import time
from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import reduce
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):      # lift Python's 4300 digit str() limit
    sys.set_int_max_str_digits(0)

import sympy as sp                              # noqa: E402
from sympy import Integer, Rational, S          # noqa: E402

# --------------------------------------------------------------------------- #
#  Limits
# --------------------------------------------------------------------------- #
MAX_BITS = 4_000_000          # largest integer produced (~1.2 million digits)
LIGHT_MAX_BITS = 100_000      # tighter limit for live preview
MAX_PREC = 5_000              # max decimal digits for approximations
MAX_INPUT = 20_000            # max expression length
SHOW_DIGITS = 600             # ints longer than this are shown as head…tail
SHOW_CHARS = 4_000            # other long outputs are clipped to this
STATE_CAP = 20_000            # values longer than this are not persisted

CONSTS = {
    "pi": sp.pi, "e": sp.E, "tau": 2 * sp.pi, "phi": sp.GoldenRatio,
    "inf": sp.oo, "oo": sp.oo, "euler": sp.EulerGamma,
}

# Functions skipped while previewing (they can be slow)
HEAVY = {
    "integrate", "solve", "nsolve", "limit", "lim", "series", "taylor", "simplify",
    "factor", "factorint", "primefactors", "divisors", "totient", "divisor_count",
    "prime", "primepi", "bell", "det", "inv", "eigenvals", "sum", "prod",
    "nextprime", "prevprime", "apart", "together", "trigsimp", "expand_trig",
}


class CalcError(Exception):
    """A user-facing calculation error."""


class Skip(CalcError):
    """Raised in preview mode for things not worth previewing."""


class Factors(dict):
    """{prime: exponent} - lets the formatter print 2^3 · 3^2."""


@dataclass
class Result:
    exact: str = ""       # main display string
    approx: str = ""      # decimal approximation, if any
    pretty: str = ""      # multi-line unicode rendering, if it adds something
    info: str = ""        # e.g. "2,568 digits"
    full: str = ""        # complete plain text (for copy / restore)
    kind: str = ""        # int, rational, real, complex, symbolic, bool, str, ...
    name: str = ""        # assigned variable, if any
    elapsed: float = 0.0


# --------------------------------------------------------------------------- #
#  Text helpers
# --------------------------------------------------------------------------- #
def _group(digits: str) -> str:
    n = len(digits)
    first = n % 3 or 3
    return ",".join([digits[:first]] + [digits[i:i + 3] for i in range(first, n, 3)])


def _prettify(s: str) -> str:
    s = s.replace("**", "^")
    s = re.sub(r"\bpi\b", "π", s)
    s = re.sub(r"\boo\b", "∞", s)
    s = re.sub(r"\bI\b", "i", s)
    return s


def _trim_num_text(s: str) -> str:
    s = re.sub(r"(\d+)\.0*(?=\D|$)", r"\1", s)
    s = re.sub(r"(\d+\.\d*?[1-9])0+(?=\D|$)", r"\1", s)
    return s


def _clip(s: str, limit: int = SHOW_CHARS) -> tuple[str, bool]:
    if len(s) <= limit:
        return s, False
    head = int(limit * 0.8)
    return f"{s[:head]} … {s[-(limit - head):]}", True


def _bits(x) -> int:
    if x.is_Integer:
        return max(1, int(x.p).bit_length())
    return max(1, int(x.p).bit_length(), int(x.q).bit_length())


def _flat(items) -> list:
    out: list = []
    for it in items:
        if isinstance(it, (list, tuple)):
            out.extend(_flat(it))
        elif isinstance(it, sp.MatrixBase):
            out.extend(list(it))
        else:
            out.append(it)
    return out


def _fib_fast(n: int) -> int:
    a, b = 0, 1
    for bit in bin(n)[2:]:
        c = a * (2 * b - a)
        d = a * a + b * b
        a, b = (d, c + d) if bit == "1" else (c, d)
    return a


_ASSIGN = re.compile(r"^\s*([A-Za-z_]\w*)\s*=(?!=)\s*(.+?)\s*$", re.S)
_FUNC_DEF = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*\(\s*([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*\)\s*=(?!=)\s*(.+?)\s*$", re.S)


# --------------------------------------------------------------------------- #
#  Engine
# --------------------------------------------------------------------------- #
class Engine:
    def __init__(self) -> None:
        self.angle = "DEG"
        self.prec = 30
        self.vars: dict[str, object] = {}
        self.funcs: dict[str, tuple] = {}         # name -> (Lambda, source text)
        self.ans = Integer(0)
        self.memory = Integer(0)
        self.last_full = ""
        self._light = False
        self._max_bits = MAX_BITS
        self._scope: dict[str, object] = {}
        self._src = ""
        self.functions = self._build_functions()

    # ------------------------------------------------------------------ #
    #  Names
    # ------------------------------------------------------------------ #
    def _is_reserved(self, name: str) -> bool:
        low = name.lower()
        return (name in self.functions or (low in self.functions and low != "n")
                or low in CONSTS or name == "I" or low == "ans")

    def _name(self, name: str):
        if name in self._scope:
            return self._scope[name]
        if name in self.vars:
            return self.vars[name]
        low = name.lower()
        if low == "ans":
            return self.ans
        if name == "I":
            return sp.I
        if low in CONSTS:
            return CONSTS[low]
        if name in self.funcs or name in self.functions or (low in self.functions and low != "n"):
            raise CalcError(f"'{name}' is a function - use {name}(...)")
        return sp.Symbol(name)

    # ------------------------------------------------------------------ #
    #  Function table
    # ------------------------------------------------------------------ #
    def _build_functions(self) -> dict:
        eng = self

        def numeric(x):
            return not getattr(x, "free_symbols", None)

        def to_rad(x):      # symbolic arguments are always radians (so calculus works)
            return x * sp.pi / 180 if eng.angle == "DEG" and numeric(x) else x

        def from_rad(x):
            return x * 180 / sp.pi if eng.angle == "DEG" and numeric(x) else x

        def T(fn):
            return lambda x: fn(to_rad(x))

        def A(fn):
            return lambda x: from_rad(fn(x))

        def need_int(x, what="an integer"):
            if not isinstance(x, sp.Integer):
                raise CalcError(f"{what} required")
            return int(x)

        def too_large():
            return CalcError(f"Result too large (limit ≈ {int(eng._max_bits * 0.30103):,} digits)")

        def log(x, base=10):
            return sp.log(x, base)

        def round_(x, n=0):
            n = n if isinstance(n, int) else need_int(n)
            if not 0 <= n <= 1000:
                raise CalcError("round: digits must be 0..1000")
            v = sp.N(x, eng.prec + n + 10)
            if v.free_symbols:
                raise CalcError("round needs a numeric value")
            r = sp.floor(v * 10 ** n + Rational(1, 2))
            return Rational(r, 10 ** n)

        # ---- combinatorics with size guards -------------------------------- #
        def factorial(n):
            if isinstance(n, sp.Integer):
                k = int(n)
                if k < 0:
                    raise CalcError("factorial of a negative integer is undefined")
                if math.lgamma(k + 1) / math.log(2) > eng._max_bits:
                    raise too_large()
                return Integer(math.factorial(k))
            return sp.factorial(n)

        def comb(n, k):
            if isinstance(n, sp.Integer) and isinstance(k, sp.Integer) and n >= 0:
                ni, ki = int(n), int(k)
                if ki < 0 or ki > ni:
                    return Integer(0)
                ki = min(ki, ni - ki)
                if min(ki * math.log2(max(ni, 2)), ni) > eng._max_bits:
                    raise too_large()
                return Integer(math.comb(ni, ki))
            return sp.binomial(n, k)

        def perm(n, k=None):
            if k is None:
                k = n
            ni, ki = need_int(n), need_int(k)
            if ki < 0 or ni < 0 or ki > ni:
                return Integer(0)
            if ki * math.log2(max(ni, 2)) > eng._max_bits:
                if (math.lgamma(ni + 1) - math.lgamma(ni - ki + 1)) / math.log(2) > eng._max_bits:
                    raise too_large()
            return Integer(math.perm(ni, ki))

        def fibonacci(n):
            if isinstance(n, sp.Integer):
                k = int(n)
                if abs(k) * 0.6943 > eng._max_bits:
                    raise too_large()
                val = _fib_fast(abs(k))
                return Integer(-val if (k < 0 and k % 2 == 0) else val)
            return sp.fibonacci(n)

        def lucas(n):
            if isinstance(n, sp.Integer) and n >= 0:
                k = int(n)
                if k * 0.6943 > eng._max_bits:
                    raise too_large()
                return Integer(2 * _fib_fast(k + 1) - _fib_fast(k))
            return sp.lucas(n)

        def catalan(n):
            if isinstance(n, sp.Integer) and n >= 0:
                k = int(n)
                if 2 * k > eng._max_bits:
                    raise too_large()
                return Integer(math.comb(2 * k, k) // (k + 1))
            return sp.catalan(n)

        def bell(n):
            if need_int(n) > 3000:
                raise CalcError("bell: n limited to 3000")
            return sp.bell(n)

        def harmonic(n):
            if isinstance(n, sp.Integer) and n > 20000:
                raise CalcError("harmonic: n limited to 20000")
            return sp.harmonic(n)

        # ---- number theory --------------------------------------------------- #
        def isprime(n):
            return sp.isprime(need_int(n))

        def nextprime(n):
            return sp.nextprime(need_int(n))

        def prevprime(n):
            return sp.prevprime(need_int(n))

        def prime(n):
            k = need_int(n)
            if not 1 <= k <= 2_000_000:
                raise CalcError("prime(n): n must be 1..2,000,000")
            return sp.prime(k)

        def primepi(n):
            if need_int(n) > 10 ** 12:
                raise CalcError("primepi: n limited to 10^12")
            return sp.primepi(n)

        def factorint(n):
            return Factors(sp.factorint(need_int(n)))

        def primefactors(n):
            return [Integer(p) for p in sp.primefactors(need_int(n))]

        def divisors(n):
            if need_int(n) < 1:
                raise CalcError("divisors needs a positive integer")
            return [Integer(d) for d in sp.divisors(int(n))]

        def totient(n):
            return sp.totient(need_int(n))

        def divisor_count(n):
            return sp.divisor_count(need_int(n))

        def gcd(*a):
            return reduce(sp.gcd, _flat(a))

        def lcm(*a):
            return reduce(sp.lcm, _flat(a))

        def modinv(a, m):
            try:
                return Integer(pow(need_int(a), -1, need_int(m)))
            except ValueError:
                raise CalcError("no modular inverse (numbers are not coprime)") from None

        def powmod(a, b, m):
            return Integer(pow(need_int(a), need_int(b), need_int(m)))

        def isqrt(n):
            return Integer(math.isqrt(need_int(n)))

        def popcount(n):
            return Integer(bin(abs(need_int(n))).count("1"))

        def bitlen(n):
            return Integer(abs(need_int(n)).bit_length())

        def xor(a, b):
            return Integer(need_int(a) ^ need_int(b))

        def bin_(n):
            return bin(need_int(n))

        def hex_(n):
            return hex(need_int(n))

        def oct_(n):
            return oct(need_int(n))

        def base_(n, b):
            n, b = need_int(n), need_int(b)
            if not 2 <= b <= 36:
                raise CalcError("base must be 2..36")
            if b in (2, 8, 16):
                return format(n, {2: "b", 8: "o", 16: "x"}[b])
            if abs(n).bit_length() > 200_000:
                raise CalcError("number too large for this base conversion")
            if n == 0:
                return "0"
            digits = "0123456789abcdefghijklmnopqrstuvwxyz"
            sign, n, out = ("-" if n < 0 else ""), abs(n), []
            while n:
                n, r = divmod(n, b)
                out.append(digits[r])
            return sign + "".join(reversed(out))

        def frombase(s, b):
            if not isinstance(s, str):
                raise CalcError('frombase("ff", 16): first argument must be quoted text')
            return Integer(int(s, need_int(b)))

        # ---- statistics ---------------------------------------------------- #
        def values(a):
            v = _flat(a)
            if not v:
                raise CalcError("at least one value required")
            return v

        def mean(*a):
            v = values(a)
            return sp.Add(*v) / len(v)

        def median(*a):
            v = sorted(values(a), key=lambda t: sp.N(t, 30))
            n = len(v)
            return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2

        def variance(*a, ddof=1):
            v = values(a)
            if len(v) <= ddof:
                raise CalcError("not enough values")
            m = sp.Add(*v) / len(v)
            return sp.Add(*[(x - m) ** 2 for x in v]) / (len(v) - ddof)

        def sum_(*a):
            if len(a) >= 2 and isinstance(a[1], tuple):
                return sp.summation(a[0], a[1])
            return sp.Add(*_flat(a))

        def prod_(*a):
            if len(a) >= 2 and isinstance(a[1], tuple):
                return sp.product(a[0], a[1])
            return sp.Mul(*_flat(a))

        # ---- calculus / algebra ---------------------------------------------- #
        def N_(x, digits=None):
            d = eng.prec if digits is None else need_int(digits)
            if not 1 <= d <= MAX_PREC:
                raise CalcError(f"digits must be 1..{MAX_PREC}")
            if eng._light and d > 200:
                raise Skip()
            return sp.N(x, d)

        def nsolve(f, x, guess):
            return sp.nsolve(f, x, guess, prec=eng.prec)

        def limit(f, x, x0, d="+"):
            if d not in ("+", "-", "+-"):
                raise CalcError('limit direction must be "+", "-" or "+-"')
            return sp.limit(f, x, x0, d)

        def series(f, x, x0=0, n=6):
            return sp.series(f, x, x0, need_int(n))

        def subs(expr, old, new):
            return sp.sympify(expr).subs(old, new)

        # ---- matrices ---------------------------------------------------------- #
        def mat(x):
            if not isinstance(x, sp.MatrixBase):
                raise CalcError("matrix expected - use matrix([[1,2],[3,4]])")
            return x

        def matrix(*rows):
            if len(rows) == 1 and isinstance(rows[0], sp.MatrixBase):
                return sp.ImmutableMatrix(rows[0])
            data = rows[0] if len(rows) == 1 else list(rows)
            if not isinstance(data, list) or not data:
                raise CalcError("matrix([[1,2],[3,4]]) expected")
            if sum(len(r) if isinstance(r, list) else 1 for r in data) > 2500:
                raise CalcError("matrix too large")
            return sp.ImmutableMatrix(data)

        def inv(m):
            try:
                return mat(m).inv()
            except ValueError:
                raise CalcError("matrix is not invertible") from None

        def identity(n):
            k = need_int(n)
            if not 1 <= k <= 50:
                raise CalcError("identity size 1..50")
            return sp.ImmutableMatrix(sp.eye(k))

        def to_degrees(x):
            return x * 180 / sp.pi

        def to_radians(x):
            return x * sp.pi / 180

        return {
            # trig (angle mode aware)
            "sin": T(sp.sin), "cos": T(sp.cos), "tan": T(sp.tan),
            "sec": T(sp.sec), "csc": T(sp.csc), "cot": T(sp.cot),
            "asin": A(sp.asin), "acos": A(sp.acos), "atan": A(sp.atan), "acot": A(sp.acot),
            "atan2": lambda y, x: from_rad(sp.atan2(y, x)),
            "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
            "asinh": sp.asinh, "acosh": sp.acosh, "atanh": sp.atanh,
            "deg": to_degrees, "rad": to_radians,
            # powers / logs
            "hypot": lambda *a: sp.sqrt(sp.Add(*[x ** 2 for x in values(a)])),
            "sqrt": sp.sqrt, "cbrt": lambda x: sp.real_root(x, 3), "root": sp.real_root,
            "exp": sp.exp, "ln": sp.log, "log": log, "log2": lambda x: sp.log(x, 2),
            "log10": lambda x: sp.log(x, 10),
            # rounding / misc scalar
            "abs": sp.Abs, "sign": sp.sign, "floor": sp.floor, "ceil": sp.ceiling,
            "ceiling": sp.ceiling, "round": round_, "mod": sp.Mod,
            "min": lambda *a: sp.Min(*values(a)), "max": lambda *a: sp.Max(*values(a)),
            "re": sp.re, "im": sp.im, "conj": sp.conjugate, "arg": sp.arg,
            "gamma": sp.gamma, "beta": sp.beta, "erf": sp.erf, "zeta": sp.zeta,
            "lambertw": sp.LambertW,
            # combinatorics
            "factorial": factorial, "fact": factorial, "factorial2": sp.factorial2,
            "comb": comb, "binomial": comb, "ncr": comb, "perm": perm, "npr": perm,
            "fibonacci": fibonacci, "fib": fibonacci, "lucas": lucas,
            "catalan": catalan, "bell": bell, "harmonic": harmonic,
            # number theory
            "isprime": isprime, "nextprime": nextprime, "prevprime": prevprime,
            "prime": prime, "primepi": primepi, "factorint": factorint,
            "primefactors": primefactors, "divisors": divisors, "totient": totient,
            "divisor_count": divisor_count, "gcd": gcd, "lcm": lcm, "modinv": modinv,
            "powmod": powmod, "isqrt": isqrt,
            # bits / bases
            "bin": bin_, "hex": hex_, "oct": oct_, "base": base_, "frombase": frombase,
            "popcount": popcount, "bitlen": bitlen, "xor": xor,
            # stats
            "mean": mean, "median": median,
            "variance": variance, "var": variance,
            "stdev": lambda *a: sp.sqrt(variance(*a)),
            "pvariance": lambda *a: variance(*a, ddof=0),
            "pstdev": lambda *a: sp.sqrt(variance(*a, ddof=0)),
            "sum": sum_, "prod": prod_,
            # algebra / calculus
            "N": N_, "nsimplify": sp.nsimplify, "simplify": sp.simplify, "expand": sp.expand,
            "factor": sp.factor, "cancel": sp.cancel, "apart": sp.apart,
            "together": sp.together, "trigsimp": sp.trigsimp, "expand_trig": sp.expand_trig,
            "diff": sp.diff, "integrate": sp.integrate, "limit": limit, "lim": limit,
            "series": series, "taylor": series, "solve": sp.solve, "nsolve": nsolve,
            "subs": subs,
            # matrices
            "matrix": matrix, "det": lambda m: mat(m).det(), "inv": inv,
            "transpose": lambda m: mat(m).T, "rank": lambda m: mat(m).rank(),
            "trace": lambda m: mat(m).trace(), "eigenvals": lambda m: mat(m).eigenvals(),
            "identity": identity, "dot": lambda a, b: mat(a).dot(mat(b)),
            "cross": lambda a, b: mat(a).cross(mat(b)), "norm": lambda m: mat(m).norm(),
        }

    # ------------------------------------------------------------------ #
    #  Pre-processing (user text -> valid Python expression)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _preprocess(text: str) -> str:
        s = text.strip()

        # Continue from the previous answer: "*2" -> "ans*2"
        if re.match(r"[+*/^%]|<<|>>", s):
            s = "ans" + s

        for old, new in (("×", "*"), ("÷", "/"), ("−", "-"), ("–", "-"), ("π", "pi"),
                         ("∞", "oo"), ("²", "**2"), ("³", "**3"), ("^", "**")):
            s = s.replace(old, new)

        s = re.sub(r"(?<=\d)_(?=\d)", "", s)                       # 1_000 -> 1000
        s = re.sub(r"(?<![\w.])0[xX][0-9a-fA-F]+|(?<![\w.])0[bB][01]+|(?<![\w.])0[oO][0-7]+",
                   lambda m: str(int(m.group(0), 0)), s)           # 0xFF -> 255
        s = re.sub(r"(?<![\w.])0+(?=\d)", "", s)                   # 007 -> 7

        s = re.sub(r"√\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", s)         # √9
        s = re.sub(r"√\s*([A-Za-z_]\w*)(?!\w|\()", r"sqrt(\1)", s)  # √x
        s = s.replace("√", "sqrt")                                 # √(...)

        s = re.sub(r"\(([^()]*)\)!(?!=)", r"factorial(\1)", s)                        # (2+3)!
        s = re.sub(r"(?<![\w.])(\d+|[A-Za-z_]\w*)!(?!=)", r"factorial(\1)", s)      # 5!
        s = re.sub(r"(\d+(?:\.\d+)?)\s*%(?!\s*[\d(.A-Za-z_])", r"(\1/100)", s)      # 15%

        # implicit multiplication: 2x, 2pi, 3(4+5), (1+2)(3+4)
        s = re.sub(r"(?<![\w.])(\d+(?:\.\d+)?|\.\d+)\s*(?=[A-Za-z_(])(?![eE][+-]?\d)",
                   r"\1*", s)
        s = re.sub(r"\)\s*(?=[\d.A-Za-z_(])", ")*", s)
        return s

    # ------------------------------------------------------------------ #
    #  Evaluation
    # ------------------------------------------------------------------ #
    def _evaluate(self, text: str):
        expr = self._preprocess(text)
        try:
            tree = ast.parse(expr, mode="eval")
        except (SyntaxError, ValueError, MemoryError):
            raise CalcError("Syntax error") from None
        prev, self._src = self._src, expr
        try:
            value = self._eval(tree.body)
        except CalcError:
            raise
        except ZeroDivisionError:
            raise CalcError("Division by zero") from None
        except OverflowError:
            raise CalcError("Number too large") from None
        except MemoryError:
            raise CalcError("Out of memory") from None
        except RecursionError:
            raise CalcError("Expression too complex") from None
        except TypeError as exc:
            if "operand" in str(exc):
                raise CalcError("Incompatible operand types (e.g. matrix + number)") from None
            raise CalcError(f"Invalid argument(s): {str(exc)[:100]}") from None
        except ValueError as exc:
            raise CalcError(f"Math error: {str(exc)[:120]}") from None
        except Exception as exc:                                     # sympy raises many types
            raise CalcError(f"{type(exc).__name__}: {str(exc)[:120]}") from None
        finally:
            self._src = prev
        return self._check(self._norm(value))

    @staticmethod
    def _norm(v):
        if isinstance(v, bool):
            return S.true if v else S.false
        if isinstance(v, int):
            return Integer(v)
        if isinstance(v, float):
            return sp.Float(v)
        return v

    def _check(self, v):
        if isinstance(v, sp.Basic):
            if v.is_Integer:
                if int(v.p).bit_length() > self._max_bits:
                    raise CalcError(f"Result too large (limit ≈ {int(self._max_bits * 0.30103):,} digits)")
            elif v.is_Rational:
                if max(int(v.p).bit_length(), int(v.q).bit_length()) > self._max_bits:
                    raise CalcError(f"Result too large (limit ≈ {int(self._max_bits * 0.30103):,} digits)")
            elif v is S.ComplexInfinity or v.has(S.ComplexInfinity):
                raise CalcError("Division by zero / undefined")
            elif v is S.NaN or v.has(S.NaN):
                raise CalcError("Undefined result")
        return v

    def _num(self, node):
        v = self._eval(node)
        if not isinstance(v, (sp.Basic, sp.MatrixBase)):
            raise CalcError("Invalid operand")
        return v

    def _arg(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return self._eval(node)

    def _decimal(self, seg: str):
        seg = seg.replace("_", "")
        m = re.search(r"[eE]([+-]?\d+)$", seg)
        if m and abs(int(m.group(1))) > 100_000:
            raise CalcError("Exponent too large")
        fr = Fraction(seg)
        return Rational(fr.numerator, fr.denominator)

    def _eval(self, node):
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                return S.true if v else S.false
            if isinstance(v, int):
                return Integer(v)
            if isinstance(v, float):
                return self._decimal(ast.get_source_segment(self._src, node) or repr(v))
            if isinstance(v, str):
                raise CalcError("Text is only allowed as a function argument")
            raise CalcError("Unsupported literal (use I for the imaginary unit)")

        if isinstance(node, ast.BinOp):
            return self._check(self._binop(type(node.op), self._num(node.left), self._num(node.right)))

        if isinstance(node, ast.UnaryOp):
            v = self._num(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return v
            if isinstance(node.op, ast.Invert):
                return Integer(~self._int(v))
            raise CalcError("Unsupported operator")

        if isinstance(node, ast.Name):
            return self._name(node.id)

        if isinstance(node, ast.Call):
            return self._call(node)

        if isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise CalcError("Chained comparisons are not supported")
            rel = {ast.Eq: sp.Eq, ast.NotEq: sp.Ne, ast.Lt: sp.Lt, ast.Gt: sp.Gt,
                   ast.LtE: sp.Le, ast.GtE: sp.Ge}.get(type(node.ops[0]))
            if rel is None:
                raise CalcError("Unsupported comparison")
            return rel(self._num(node.left), self._num(node.comparators[0]))

        if isinstance(node, ast.List):
            return [self._arg(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._arg(e) for e in node.elts)

        raise CalcError("Unsupported syntax")

    @staticmethod
    def _int(v) -> int:
        if not isinstance(v, sp.Integer):
            raise CalcError("Integer required for this operator")
        return int(v)

    def _binop(self, op, a, b):
        if op is ast.Add:
            return a + b
        if op is ast.Sub:
            return a - b
        if op is ast.Mult:
            return a * b
        if op is ast.Div:
            return a / b
        if op is ast.FloorDiv:
            return sp.floor(a / b)
        if op is ast.Mod:
            return a % b
        if op is ast.Pow:
            return self._pow(a, b)
        if op in (ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr):
            x, y = self._int(a), self._int(b)
            if op is ast.BitAnd:
                return Integer(x & y)
            if op is ast.BitOr:
                return Integer(x | y)
            if y < 0:
                raise CalcError("Negative shift count")
            if op is ast.LShift:
                if y + x.bit_length() > self._max_bits:
                    raise CalcError("Result too large")
                return Integer(x << y)
            return Integer(x >> y)
        raise CalcError("Unsupported operator")

    def _pow(self, a, b):
        if isinstance(a, sp.MatrixBase):
            if not (isinstance(b, sp.Integer) and abs(int(b)) <= 1000):
                raise CalcError("Matrix power must be a small integer")
            return a ** b
        if isinstance(b, sp.MatrixBase):
            raise CalcError("Invalid exponent")
        if a.is_number and b.is_Rational and a not in (0, 1, -1):
            if a.is_Rational:
                base_bits = _bits(a)
            else:
                try:
                    base_bits = max(1, int(math.log2(max(float(abs(sp.N(a, 15))), 2.0))))
                except Exception:
                    base_bits = 1
            steps = int(abs(b.p)) // int(b.q) + 1
            if steps * base_bits > self._max_bits:
                raise CalcError(f"Result too large (limit ≈ {int(self._max_bits * 0.30103):,} digits)")
        return a ** b

    def _variable_args(self, low: str, node) -> dict:
        """Names (that hold stored values) used as the variable of solve/diff/sum/... calls."""
        names: list[str] = []
        rest = node.args[1:]
        if low in ("diff", "integrate", "solve"):
            for a in rest:
                if isinstance(a, ast.Name):
                    names.append(a.id)
        elif low in ("limit", "lim", "series", "taylor", "nsolve", "subs") and rest:
            if isinstance(rest[0], ast.Name):
                names.append(rest[0].id)
        if low in ("integrate", "sum", "prod"):
            for a in rest:
                if isinstance(a, ast.Tuple) and a.elts and isinstance(a.elts[0], ast.Name):
                    names.append(a.elts[0].id)
        return {n: sp.Symbol(n) for n in names if n in self.vars}

    def _call(self, node):
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise CalcError("Unsupported function call")
        fname = node.func.id
        low = fname.lower()
        # In calculus/solve-style calls, the *variable* arguments stay symbols even if the
        # user stored a value under that name (x = 7 must not break solve(x^2-49, x)).
        shadow = self._variable_args(low, node)
        prev_scope = self._scope
        if shadow:
            self._scope = {**prev_scope, **shadow}
        try:
            args = [self._arg(a) for a in node.args]
        finally:
            self._scope = prev_scope

        if fname in self.funcs:
            lam = self.funcs[fname][0]
            if len(args) != len(lam.variables):
                raise CalcError(f"{fname} expects {len(lam.variables)} argument(s)")
            return self._check(self._norm(lam(*args)))

        fn = self.functions.get(fname)
        if fn is None and low != "n":
            fn = self.functions.get(low)
        if fn is None:
            raise CalcError(f"Unknown function '{fname}'")
        if self._light and low in HEAVY:
            raise Skip()
        try:
            result = fn(*args)
        except TypeError as exc:
            if "argument" in str(exc) and "positional" in str(exc):
                raise CalcError(f"Wrong number of arguments for {fname}()") from None
            raise
        return self._check(self._norm(result))

    # ------------------------------------------------------------------ #
    #  Formatting
    # ------------------------------------------------------------------ #
    def _approx(self, v, digits: int | None = None) -> str:
        if (not isinstance(v, sp.Basic) or v.free_symbols or not v.is_number
                or v.is_Float or v in (sp.oo, -sp.oo)):
            return ""
        try:
            s = str(sp.N(v, digits or self.prec))
        except Exception:
            return ""
        if "nan" in s or "zoo" in s:
            return ""
        out = _prettify(_trim_num_text(s))
        return "" if out in (_prettify(str(v)), "1*i") else out

    @staticmethod
    def _disp(v) -> str:
        if isinstance(v, sp.Integer):
            return str(int(v))
        return _prettify(str(v))

    def _plain(self, v):
        if isinstance(v, sp.Integer):
            return str(int(v))
        if isinstance(v, (sp.Basic, sp.MatrixBase)):
            return str(v)
        return None

    def _pretty2d(self, v) -> str:
        if self._light:
            return ""
        try:
            if len(str(v)) > 800:
                return ""
            out = sp.pretty(v, use_unicode=True, wrap_line=False)
            return out if "\n" in out else ""
        except Exception:
            return ""

    def _make_result(self, value) -> Result:
        r = Result()

        if isinstance(value, sp.MatrixBase):
            r.kind, r.full = "matrix", str(value)
            r.exact, _ = _clip(_prettify(r.full))
            r.pretty = self._pretty2d(value)
            r.info = f"{value.rows}×{value.cols} matrix"
            return r

        if isinstance(value, Factors):
            r.kind = "factors"
            r.exact = " · ".join(f"{p}^{e}" if e > 1 else f"{p}" for p, e in sorted(value.items())) or "1"
            r.full = r.exact
            return r

        if isinstance(value, dict):
            r.kind = "dict"
            r.exact = "; ".join(f"{self._disp(k)} (×{v})" for k, v in value.items())
            r.full = str({str(k): int(v) for k, v in value.items()})
            return r

        if isinstance(value, (list, tuple, set, frozenset)):
            items = list(value)
            r.kind = "list"
            r.exact, clipped = _clip("[" + ", ".join(self._disp(i) for i in items) + "]")
            r.full = "[" + ", ".join(str(i) for i in items) + "]"
            approx = [self._approx(i) or self._disp(i) for i in items]
            if any(self._approx(i) for i in items if isinstance(i, sp.Basic) and not i.is_Rational):
                r.approx, _ = _clip("[" + ", ".join(approx) + "]")
            r.info = f"{len(items)} item(s)"
            return r

        if isinstance(value, str):
            r.kind, r.full = "str", value
            r.exact, clipped = _clip(value)
            r.info = f"{len(value):,} characters"
            return r

        if not isinstance(value, sp.Basic):
            r.kind, r.full = "other", str(value)
            r.exact, _ = _clip(r.full)
            return r

        if value is S.true or value is S.false:
            r.kind = "bool"
            r.exact = r.full = "True" if value is S.true else "False"
            return r

        if value.is_Integer:
            n = int(value)
            digits = str(abs(n))
            r.kind, r.full = "int", str(n)
            sign = "-" if n < 0 else ""
            if len(digits) <= SHOW_DIGITS:
                r.exact = sign + (_group(digits) if len(digits) >= 5 else digits)
            else:
                r.exact = f"{sign}{digits[:500]} … {digits[-100:]}"
            if len(digits) > 15:
                sci = _prettify(_trim_num_text(str(sp.N(value, min(self.prec, 20)))))
                r.approx = sci if "e" in sci else ""
                r.info = f"{len(digits):,} digits · {abs(n).bit_length():,} bits"
            return r

        if value.is_Rational:
            r.kind, r.full = "rational", str(value)
            r.exact, clipped = _clip(r.full)
            r.approx = self._approx(value)
            r.info = "exact fraction"
            return r

        if value.is_Float:
            r.kind, r.full = "real", str(value)
            r.exact = _prettify(_trim_num_text(r.full))
            return r

        r.full = str(value)
        r.exact, _ = _clip(_prettify(r.full))
        if value.free_symbols:
            r.kind = "symbolic"
            r.pretty = self._pretty2d(value)
        elif value.is_number:
            r.kind = "complex" if value.is_real is False else "real"
            r.approx = self._approx(value)
            r.pretty = self._pretty2d(value)
        else:
            r.kind = "symbolic"
        return r

    def _short(self, v) -> str:
        if isinstance(v, sp.Integer) and len(str(abs(int(v)))) > 18:
            return self._approx(v, 12) or "big"
        s = _prettify(str(v))
        return s if len(s) <= 28 else s[:27] + "…"

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def run(self, text: str, commit: bool = True, light: bool = False) -> Result:
        t0 = time.perf_counter()
        self._light = light
        self._max_bits = LIGHT_MAX_BITS if light else MAX_BITS
        try:
            text = text.strip()
            if not text:
                raise CalcError("Empty expression")
            if len(text) > MAX_INPUT:
                raise CalcError("Expression too long")
            if text.startswith(":"):
                if light:
                    raise Skip()
                res = self._command(text)
            else:
                res = self._run_expr(text, commit)
        finally:
            self._light = False
            self._max_bits = MAX_BITS
        res.elapsed = time.perf_counter() - t0
        return res

    def _run_expr(self, text: str, commit: bool) -> Result:
        fm = _FUNC_DEF.match(text)
        if fm:
            if self._light:
                raise Skip()
            return self._define_function(fm.group(1), fm.group(2), fm.group(3), commit)

        name = None
        am = _ASSIGN.match(text)
        if am:
            name, text = am.group(1), am.group(2)
            if self._is_reserved(name):
                raise CalcError(f"'{name}' is a reserved name")

        value = self._evaluate(text)
        res = self._make_result(value)
        if name:
            res.name = name
            if not isinstance(value, (sp.Basic, sp.MatrixBase)):
                raise CalcError("Only numbers, expressions and matrices can be stored in a variable")
        if commit:
            if name:
                self.vars[name] = value
            if isinstance(value, (sp.Basic, sp.MatrixBase)):
                self.ans = value
            self.last_full = res.full
        return res

    def _define_function(self, name: str, params_text: str, body_text: str, commit: bool) -> Result:
        params = [p.strip() for p in params_text.split(",")]
        if self._is_reserved(name):
            raise CalcError(f"'{name}' is a reserved name")
        if len(set(params)) != len(params):
            raise CalcError("Duplicate parameter names")
        syms = {p: sp.Symbol(p) for p in params}
        prev, self._scope = self._scope, syms
        try:
            body = self._evaluate(body_text)
        finally:
            self._scope = prev
        if not isinstance(body, sp.Basic):
            raise CalcError("Function body must be an expression")
        lam = sp.Lambda(tuple(syms.values()), body)
        header = f"{name}({', '.join(params)})"
        if commit:
            self.funcs[name] = (lam, f"{header} = {body}")
        r = Result(kind="define", full=f"{header} = {body}")
        r.exact, _ = _clip(f"{header} = {_prettify(str(body))}")
        r.info = "function defined"
        return r

    # ---- ":" commands ---------------------------------------------------- #
    def _command(self, text: str) -> Result:
        parts = text[1:].split()
        if not parts:
            raise CalcError("Empty command")
        cmd, args = parts[0].lower(), parts[1:]

        if cmd in ("deg", "rad"):
            self.angle = cmd.upper()
            msg = f"Angle mode: {self.angle}"
        elif cmd == "prec":
            try:
                n = int(args[0])
            except (IndexError, ValueError):
                raise CalcError("Usage: :prec 50") from None
            if not 1 <= n <= MAX_PREC:
                raise CalcError(f"Precision must be 1..{MAX_PREC}")
            self.prec = n
            msg = f"Precision: {n} digits"
        elif cmd == "vars":
            lines = [f"{k} = {self._short(v)}" for k, v in self.vars.items()]
            lines += [_prettify(src) for _, src in self.funcs.values()]
            msg = "\n".join(lines) or "(no variables or functions defined)"
        elif cmd == "del":
            if not args:
                raise CalcError("Usage: :del name")
            found = self.vars.pop(args[0], None) is not None
            found = (self.funcs.pop(args[0], None) is not None) or found
            if not found:
                raise CalcError(f"'{args[0]}' is not defined")
            msg = f"Deleted {args[0]}"
        elif cmd == "reset":
            self.vars.clear()
            self.funcs.clear()
            self.ans = self.memory = Integer(0)
            msg = "Cleared all variables, functions, memory and Ans"
        elif cmd == "save":
            if not args:
                raise CalcError("Usage: :save filename.txt")
            if not self.last_full:
                raise CalcError("Nothing to save yet")
            Path(args[0]).write_text(self.last_full, encoding="utf-8")
            msg = f"Saved {len(self.last_full):,} characters to {args[0]}"
        else:
            raise CalcError(f"Unknown command ':{cmd}'")
        return Result(kind="command", exact=msg, full=msg)

    # ---- memory keys ------------------------------------------------------- #
    def memory_op(self, action: str, text: str) -> Result:
        if action == "mc":
            self.memory = Integer(0)
        elif action in ("m+", "m-"):
            v = self._evaluate(text) if text.strip() else self.ans
            if not isinstance(v, sp.Basic):
                raise CalcError("Memory needs a numeric value")
            self.memory = self.memory + v if action == "m+" else self.memory - v
        elif action != "mr":
            raise CalcError("Unknown memory action")
        plain = self._plain(self.memory) or "0"
        return Result(kind="memory", exact=f"M = {self._disp(self.memory)}", full=plain)

    # ---- status / persistence -------------------------------------------------- #
    def status(self) -> dict:
        return {
            "angle": self.angle, "prec": self.prec, "ans": self._short(self.ans),
            "memory": "" if self.memory == 0 else self._short(self.memory),
            "defs": len(self.vars) + len(self.funcs),
        }

    def export_state(self) -> dict:
        def keep(v):
            p = self._plain(v)
            return p if p is not None and len(p) <= STATE_CAP else None

        state = {"angle": self.angle, "prec": self.prec,
                 "vars": {}, "funcs": {n: src for n, (_, src) in self.funcs.items()}}
        for k, v in self.vars.items():
            p = keep(v)
            if p is not None:
                state["vars"][k] = p
        for key, v in (("ans", self.ans), ("memory", self.memory)):
            p = keep(v)
            if p is not None:
                state[key] = p
        return state

    def import_state(self, state: dict) -> None:
        if state.get("angle") in ("DEG", "RAD"):
            self.angle = state["angle"]
        if isinstance(state.get("prec"), int) and 1 <= state["prec"] <= MAX_PREC:
            self.prec = state["prec"]
        for src in state.get("funcs", {}).values():
            try:
                self.run(src)
            except Exception:
                pass
        for name, plain in state.get("vars", {}).items():
            try:
                self.vars[name] = self._evaluate(plain)
            except Exception:
                pass
        for key in ("ans", "memory"):
            if key in state:
                try:
                    setattr(self, key, self._evaluate(state[key]))
                except Exception:
                    pass


# --------------------------------------------------------------------------- #
#  Worker process entry point (JSON lines over stdin/stdout)
# --------------------------------------------------------------------------- #
def worker_main() -> None:
    proto = sys.stdout
    sys.stdout = sys.stderr            # stray prints must never corrupt the protocol
    try:
        import resource                # Unix only: cap memory so a bad input can't eat the machine
        limit = 4 * 1024 ** 3
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except Exception:
        pass

    stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")

    def send(obj: dict) -> None:
        proto.write(json.dumps(obj) + "\n")
        proto.flush()

    eng = Engine()
    send({"ready": True})

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            op = req.get("op")
            if op == "eval":
                commit = req.get("commit", True)
                res = eng.run(req["text"], commit=commit, light=req.get("light", False))
                reply = {"ok": True, "result": asdict(res), "status": eng.status()}
                if commit:
                    reply["state"] = eng.export_state()
                send(reply)
            elif op == "memory":
                res = eng.memory_op(req["action"], req.get("text", ""))
                send({"ok": True, "result": asdict(res), "status": eng.status(),
                      "state": eng.export_state()})
            elif op == "restore":
                eng.import_state(req.get("state") or {})
                send({"ok": True, "status": eng.status()})
            elif op == "quit":
                break
            else:                       # "ping": lets the UI wait until the engine is ready
                send({"ok": True, "status": eng.status()})
        except Skip:
            send({"ok": False, "skip": True, "error": ""})
        except CalcError as exc:
            send({"ok": False, "error": str(exc)})
        except MemoryError:
            send({"ok": False, "error": "Out of memory"})
        except Exception as exc:
            send({"ok": False, "error": f"Internal error: {type(exc).__name__}: {str(exc)[:200]}"})


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker_main()
    else:
        print("calc_engine.py is the calculation engine. Run calculator.py instead.")