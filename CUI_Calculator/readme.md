<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=220&section=header&text=CUI%20Calculator&fontSize=52&fontColor=ffffff&fontAlignY=35&animation=fadeIn" width="100%"/>

# CUI Calculator

### A terminal calculator that actually respects math.

<p>
Exact arithmetic · Symbolic algebra · Calculus · Big integers · Number theory
</p>

<p>
Process isolation · Cancellation · Persistence · Live preview
</p>

<br>

<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/Textual-TUI-6C5CE7?style=for-the-badge">
<img src="https://img.shields.io/badge/SymPy-Symbolic%20Mathematics-3B5526?style=for-the-badge">
<img src="https://img.shields.io/badge/Rich-Terminal%20Rendering-000000?style=for-the-badge">
<img src="https://img.shields.io/badge/License-MIT-2EA44F?style=for-the-badge">

<br><br>

<img src="https://skillicons.dev/icons?i=python,git,github&theme=dark" />

<br><br>

<a href="#quick-start">Quick Start</a> · <a href="#features">Features</a> · <a href="#architecture">Architecture</a> · <a href="#testing">Testing</a> · <a href="#contributing">Contributing</a>

</div>

---

# Overview

**CUI Calculator** is a scientific calculator implemented as a Terminal User Interface (TUI).

It combines a responsive terminal interface with the symbolic mathematics capabilities of SymPy.

The project is designed around a simple principle:

> **Mathematical results should remain exact whenever an exact representation exists.**

For example:

```text
1 / 3
```

produces:

```text
1/3
```

rather than immediately converting the result to:

```text
0.3333333333
```

An approximation can still be displayed separately:

```text
≈ 0.333333333333333333333333333333
```

This distinction between exact and approximate mathematics is one of the central design goals of the project.

---

# Table of Contents

- [Overview](#overview)

- [Core Design](#core-design)
- [Features](#features)
  - [Exact Arithmetic](#exact-arithmetic)
  - [Symbolic Algebra](#symbolic-algebra)
  - [Calculus](#calculus)
  - [Trigonometry](#trigonometry)
  - [Big Integers](#big-integers)
  - [Number Theory](#number-theory)
  - [Combinatorics](#combinatorics)
  - [Matrices and Linear Algebra](#matrices-and-linear-algebra)
  - [Statistics](#statistics)
  - [Bases and Bit Operations](#bases-and-bit-operations)
  - [Variables](#variables)
  - [Functions](#functions)
  - [Memory](#memory)
  - [History](#history)
  - [Live Preview](#live-preview)
  - [Cancellation](#cancellation)
  - [Persistence](#persistence)
  - [Themes](#themes)

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Testing](#testing)
- [Limits](#limits)
- [Security](#security)
- [Configuration](#configuration)
- [Roadmap](#roadmap)
- [License](#license)
- [Credits](#credits)

---

# Core Design

CUI Calculator is built around four major components:

<pre>
                    CUI Calculator
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
       Textual          Service           Engine
          |                |                |
          |                |                |
          v                v                v
        UI              Process          SymPy
                       Management       Mathematics
                           |
                           v
                     State Recovery
</pre>

The application intentionally separates the interface from the mathematical engine.

This makes it possible to terminate an expensive calculation without terminating the entire user interface.

---

# Features

## Exact Arithmetic

CUI Calculator attempts to preserve exact mathematical values.

```text
1 / 3
```

Result:

```text
1/3
```

```text
1/3 + 1/6
```

Result:

```text
1/2
```

```text
0.1 + 0.2
```

Result:

```text
3/10
```

```text
(1/7) * 7
```

Result:

```text
1
```

Irrational expressions remain symbolic:

```text
sqrt(2)
```

Result:

```text
√2
```

with an optional approximation:

```text
≈ 1.41421356237309504880168872421
```

---

# Symbolic Algebra

SymPy expressions can be manipulated symbolically.

### Equation solving

```text
solve(x^2 - 4, x)
```

Result:

```text
[-2, 2]
```

### Simplification

```text
simplify(sin(x)^2 + cos(x)^2)
```

Result:

```text
1
```

### Factorization

```text
factor(x^2 - 1)
```

Result:

```text
(x - 1)*(x + 1)
```

### Expansion

```text
expand((x + 1)^3)
```

Result:

```text
x^3 + 3*x^2 + 3*x + 1
```

### Partial fractions

```text
apart(1/(x^2 - 1), x)
```

Result:

```text
1/(2*(x - 1)) - 1/(2*(x + 1))
```

Supported symbolic operations include:

```text
solve
nsolve
simplify
expand
factor
cancel
apart
together
trigsimp
expand_trig
diff
integrate
limit
lim
series
taylor
subs
N
nsimplify
sum
prod
```

---

# Calculus

## Derivatives

```text
diff(sin(x), x)
```

```text
cos(x)
```

```text
diff(x^3, x, 2)
```

```text
6*x
```

---

## Integrals

```text
integrate(x^2, x)
```

```text
x^3/3
```

Definite integration:

```text
integrate(x^2, (x, 0, 1))
```

```text
1/3
```

---

## Limits

```text
limit(sin(x)/x, x, 0)
```

```text
1
```

One-sided limits:

```text
limit(1/x, x, 0, "+")
```

```text
∞
```

---

## Series

```text
series(exp(x), x, 0, 6)
```

Example output:

```text
1 + x + x²/2 + x³/6 + x⁴/24 + x⁵/120 + O(x⁶)
```

---

# Trigonometry

The calculator supports both degree and radian modes.

Toggle using:

```text
F2
```

or:

```text
:deg
:rad
```

### Degree mode

```text
sin(30)
```

```text
1/2
```

```text
asin(1)
```

```text
90
```

### Radian mode

```text
sin(pi/6)
```

```text
1/2
```

```text
asin(1)
```

```text
pi/2
```

Supported functions include:

```text
sin
cos
tan
sec
csc
cot

asin
acos
atan
atan2
acot

sinh
cosh
tanh
asinh
acosh
atanh
```

Explicit conversion is also supported:

```text
deg(x)
rad(x)
```

Symbolic expressions remain in radians so that calculus operations are mathematically consistent.

---

# Big Integers

CUI Calculator supports arbitrary-precision integer calculations.

For example:

```text
2^1000
```

produces a 302-digit exact integer.

The interface can display:

```text
10,715,086,071,862,673,209,484,250,490,600,...
```

instead of converting it into a floating-point approximation.

The calculator can also report:

```text
302 digits · 1001 bits · 12 ms
```

Large values can be truncated visually while remaining available internally.

Example:

```text
[first 500 digits]
...
[last 100 digits]
```

---

## Large Integer Limits

A practical size limit is used to protect the system from accidental resource exhaustion.

The engine uses an approximately:

```text
4,000,000-bit
```

large-integer boundary.

The live preview uses a significantly smaller limit.

This allows normal calculations to remain responsive while still supporting very large values.

---

# Number Theory

Examples:

```text
isprime(2^31 - 1)
```

```text
True
```

```text
isprime(100)
```

```text
False
```

```text
nextprime(100)
```

```text
101
```

```text
prevprime(100)
```

```text
97
```

```text
prime(1000)
```

```text
7919
```

```text
primepi(10^6)
```

```text
78498
```

```text
factorint(360)
```

```text
2^3 · 3^2 · 5
```

```text
primefactors(360)
```

```text
[2, 3, 5]
```

```text
divisors(28)
```

```text
[1, 2, 4, 7, 14, 28]
```

Additional operations:

```text
totient
divisor_count
gcd
lcm
modinv
powmod
isqrt
```

---

# Combinatorics

Supported functions include:

```text
factorial
factorial2
comb
perm
fibonacci
lucas
catalan
bell
harmonic
```

Examples:

```text
factorial(20)
```

```text
2432902008176640000
```

```text
comb(100, 50)
```

```text
100891344545564193334812497256
```

```text
perm(10, 3)
```

```text
720
```

```text
fibonacci(100)
```

```text
354224848179261915075
```

For concrete integer inputs, optimized integer algorithms can be used where appropriate.

---

# Matrices and Linear Algebra

Matrices can be constructed directly:

```text
matrix([[1, 2], [3, 4]])
```

### Determinant

```text
det(matrix([[1, 2], [3, 4]]))
```

```text
-2
```

### Inverse

```text
inv(matrix([[1, 2], [3, 4]]))
```

```text
[[-2, 1],
 [3/2, -1/2]]
```

### Other operations

```text
transpose
det
inv
rank
trace
eigenvals
identity
dot
cross
norm
```

Small matrices can be displayed using a readable two-dimensional representation.

A practical matrix-size limit prevents excessively large renderings.

---

# Statistics

CUI Calculator supports exact statistical operations.

```text
mean(1, 2, 3, 4, 5)
```

```text
3
```

```text
median(1, 2, 3, 4)
```

```text
5/2
```

```text
variance(1, 2, 3, 4, 5)
```

```text
5/2
```

```text
pvariance(1, 2, 3, 4, 5)
```

```text
2
```

```text
stdev(1, 2, 3, 4, 5)
```

```text
√(5/2)
```

Other supported operations include:

```text
min
max
hypot
sum
prod
```

---

# Bases and Bit Operations

Binary:

```text
0b1010
```

Result:

```text
10
```

Hexadecimal:

```text
0xFF
```

Result:

```text
255
```

Octal:

```text
0o17
```

Result:

```text
15
```

Conversions:

```text
bin(255)
hex(255)
oct(255)
```

Custom bases:

```text
base(255, 2)
```

```text
11111111
```

```text
base(255, 36)
```

```text
73
```

Reverse conversion:

```text
frombase("ff", 16)
```

```text
255
```

Bit operations:

```text
popcount(255)
bitlen(255)
xor(12, 10)
```

Supported operators include:

```text
<<
>>
&
|
~
```

---

# Variables

Variables can store mathematical values.

```text
a = 5
```

Then:

```text
a * 3
```

produces:

```text
15
```

Another example:

```text
x = pi
```

The value remains symbolic:

```text
π
```

Variables can contain:

```text
integers
rationals
symbols
expressions
lists
matrices
```

---

# Functions

User-defined functions are supported.

```text
f(x) = x^2 + 1
```

Then:

```text
f(4)
```

produces:

```text
17
```

Multiple arguments:

```text
g(x, y) = x^2 + y^2
```

Then:

```text
g(3, 4)
```

produces:

```text
25
```

Functions can also participate in symbolic operations:

```text
diff(f(x), x)
```

Result:

```text
2*x
```

---

# The `ans` Variable

Every successful calculation updates:

```text
ans
```

Example:

```text
2 + 2
```

```text
4
```

Then:

```text
ans * 3
```

```text
12
```

Leading operators can reference the previous answer:

```text
*2
```

which is interpreted conceptually as:

```text
ans * 2
```

---

# Memory

Classic calculator memory operations are available.

| Key | Operation                   |
| --- | --------------------------- |
| M+  | Add current value to memory |
| M−  | Subtract current value      |
| MR  | Recall memory               |
| MC  | Clear memory                |

The status bar displays the current memory value.

Example:

```text
M: 42
```

---

# History

The history panel keeps previous calculations accessible.

Example:

```text
2 + 2       → 4
sqrt(2)     → √2
f(3)        → 10
2^1000      → large integer
```

Selecting a history entry can reload the expression into the input field.

History is persisted between launches.

---

# Live Preview

CUI Calculator can preview an expression while the user is typing.

The general flow is:

```text
User types expression
        |
        v
Short debounce period
        |
        v
Preview calculation
        |
        v
Preview result
```

The preview uses tighter limits than the full engine.

This means that entering a potentially expensive expression does not need to block the main application.

---

# Cancellation

This is one of the most important architectural features of the project.

Some symbolic calculations can take a long time.

For example:

```text
integrate(sin(x)/x, (x, -oo, oo))
```

Instead of running the calculation directly inside the UI process, CUI Calculator uses a separate calculation process.

When a calculation is running:

```text
Calculating...

Press Esc to cancel
```

Pressing:

```text
Esc
```

causes the calculation engine to be terminated and restarted.

The interface remains available.

---

# Process Recovery

The engine lifecycle is approximately:

```text
                Start
                  |
                  v
          +---------------+
          | Calc Engine   |
          +-------+-------+
                  |
                  v
             Calculation
                  |
        +---------+---------+
        |                   |
        v                   v
     Success             Failure
        |                   |
        |             Restart engine
        |                   |
        +---------+---------+
                  |
                  v
            Restore state
                  |
                  v
               Ready
```

This architecture protects the UI from expensive or failed calculations.

---

# Persistence

Application state is stored locally.

Default location:

```text
~/.textual_calculator_v2.json
```

The saved state can contain:

```json
{
  "history": [
    {
      "expr": "2^1000",
      "result": "1071508607..."
    }
  ],
  "state": {
    "angle": "DEG",
    "prec": 30,
    "vars": {
      "a": "5"
    },
    "funcs": {
      "f(x)": "f(x) = x**2 + 1"
    },
    "ans": "10",
    "memory": "42"
  }
}
```

The application can restore:

- Variables
- Functions
- History
- Precision
- Angle mode
- `ans`
- Memory

Persistence is best-effort so that a disk-write problem does not unnecessarily terminate the application.

---

# Themes

CUI Calculator supports:

```text
Dark
Light
```

Use:

```text
F4
```

to toggle the theme.

---

# Commands

Commands start with `:`.

| Command      | Description                     |
| ------------ | ------------------------------- |
| `:deg`       | Switch to degree mode           |
| `:rad`       | Switch to radian mode           |
| `:prec N`    | Set decimal precision           |
| `:vars`      | Display variables and functions |
| `:del NAME`  | Delete a variable or function   |
| `:reset`     | Reset calculator state          |
| `:save FILE` | Save the last full result       |
| `:timeout N` | Set calculation timeout         |

Examples:

```text
:prec 100
```

```text
:timeout 60
```

```text
:vars
```

```text
:reset
```

---

# Keyboard Shortcuts

| Shortcut | Action                            |
| -------- | --------------------------------- |
| `Enter`  | Evaluate expression               |
| `Esc`    | Cancel calculation or clear input |
| `F1`     | Show help                         |
| `F2`     | Toggle DEG/RAD                    |
| `F3`     | Clear history                     |
| `F4`     | Toggle theme                      |
| `F5`     | Copy full result                  |
| `F6`     | Show/hide history                 |
| `F8`     | Copy decimal approximation        |
| `Ctrl+Q` | Quit                              |

---

# Architecture

The application consists of three primary layers.

```text
+------------------------------------------------------+
|                    Textual UI                        |
|                                                      |
|  Input | Result | History | Keypad | Status | Tabs  |
+---------------------------+--------------------------+
                            |
                            v
+------------------------------------------------------+
|                  CalcService                         |
|                                                      |
|  Process lifecycle | IPC | Timeout | Cancellation   |
|  State snapshot    | Restart | Recovery             |
+---------------------------+--------------------------+
                            |
                            v
+------------------------------------------------------+
|                   CalcEngine                         |
|                                                      |
|  Preprocessing | AST validation | SymPy | Formatting|
+------------------------------------------------------+
```

---

# Data Flow

For an expression such as:

```text
2^1000
```

the processing pipeline is approximately:

```text
User input
    |
    v
Textual Input
    |
    v
Preview / Evaluation Worker
    |
    v
CalcService
    |
    v
JSON request
    |
    v
CalcEngine subprocess
    |
    v
Expression preprocessing
    |
    v
AST parsing
    |
    v
Allowed-expression validation
    |
    v
SymPy evaluation
    |
    v
Result formatting
    |
    v
JSON response
    |
    v
Textual UI
```

---

# Project Structure

```text
CUI_Calculator/
│
├── main.py
├── README.md
├── LICENSE
├── requirements.txt
│
└── Modules/
    ├── __init__.py
    ├── Calc_engine.py
    └── Calc_service.py

```

### `main.py`

Contains the Textual application and UI logic.

Responsibilities include:

- Layout
- Input handling
- Result rendering
- History panel
- Key bindings
- Live preview
- UI workers
- Persistence integration
- Theme handling

### `Modules/Calc_engine.py`

Contains the mathematical engine.

Responsibilities include:

- Expression parsing
- AST validation
- Mathematical functions
- SymPy operations
- Result formatting
- Large-number handling

### `Modules/Calc_service.py`

Manages the calculation process.

Responsibilities include:

- Process creation
- JSON IPC
- Timeouts
- Cancellation
- Restarting the engine
- State restoration

---

# Installation

## Requirements

- Python 3.10 or newer
- Unicode-capable terminal
- 256-color terminal support
- Approximately 50 MB or more for dependencies

Recommended terminals include:

- macOS Terminal
- iTerm2
- Windows Terminal
- GNOME Terminal
- Kitty
- Alacritty

---

# Quick Start

## Clone the repository

```bash
git clone https://github.com/DevMuhammadHussnain/Itz-Python.git
cd Itz-Python/CUI_Calculator
```

## Create a virtual environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Windows Command Prompt

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

---

# Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the requirements file is unavailable:

```bash
pip install "textual>=0.80" rich sympy
```

---

# Run

```bash
python main.py
```

Run the command from the project root.

The application expects the `Modules` package to be available relative to the project root.

---

# Testing

## Basic arithmetic

```text
2 + 2
```

Expected:

```text
4
```

```text
10 / 4
```

Expected:

```text
5/2
```

```text
1 / 3
```

Expected:

```text
1/3
```

```text
0.1 + 0.2
```

Expected:

```text
3/10
```

---

## Big integers

```text
2^1000
```

Expected:

```text
302-digit integer
```

```text
100!
```

Expected:

```text
158-digit integer
```

```text
fibonacci(1000)
```

Expected:

```text
209-digit integer
```

```text
2^10000
```

Expected:

```text
Large integer with truncated display
```

---

## Symbolic mathematics

```text
solve(x^2 - 4, x)
```

Expected:

```text
[-2, 2]
```

```text
diff(sin(x), x)
```

Expected:

```text
cos(x)
```

```text
integrate(x^2, (x, 0, 1))
```

Expected:

```text
1/3
```

```text
limit(sin(x)/x, x, 0)
```

Expected:

```text
1
```

```text
factor(x^2 - 1)
```

Expected:

```text
(x - 1)*(x + 1)
```

---

## Number theory

```text
isprime(2^31 - 1)
```

Expected:

```text
True
```

```text
factorint(360)
```

Expected:

```text
2^3 · 3^2 · 5
```

```text
gcd(462, 1071)
```

Expected:

```text
21
```

```text
prime(1000)
```

Expected:

```text
7919
```

---

## Variables and functions

```text
a = 5
```

```text
a * 3
```

Expected:

```text
15
```

```text
f(x) = x^2 + 1
```

```text
f(4)
```

Expected:

```text
17
```

```text
:vars
```

Expected:

```text
a = 5
f(x) = x^2 + 1
```

---

# Limits and Resource Management

Mathematics can be computationally expensive.

Examples include:

```text
large symbolic integrations
large matrix operations
huge integer calculations
large symbolic expansions
high-order series
```

CUI Calculator therefore uses several protections:

| Protection          | Purpose                                       |
| ------------------- | --------------------------------------------- |
| Calculation timeout | Prevent indefinitely running calculations     |
| Process isolation   | Keep expensive calculations away from the UI  |
| Cancellation        | Allow the user to terminate calculations      |
| Integer limits      | Prevent uncontrolled huge integers            |
| Matrix limits       | Prevent excessive matrix operations/rendering |
| Preview limits      | Keep live preview lightweight                 |
| Persistence limits  | Prevent huge state files                      |

These limits are intended to protect responsiveness rather than mathematically restrict normal usage.

---

# Security

The expression evaluator is designed around an AST-based validation model.

The intended evaluation flow is:

```text
Input
  |
  v
Preprocessor
  |
  v
AST parser
  |
  v
Allowed syntax validation
  |
  v
Allowed function resolution
  |
  v
SymPy evaluation
  |
  v
Formatted result
```

The project does not rely on unrestricted Python `eval()` for expression evaluation.

The mathematical engine is also separated into its own process.

As with any expression-processing application, additional security review is recommended before accepting hostile or untrusted input.

---

# Configuration

## Precision

Set precision:

```text
:prec 50
```

or:

```text
:prec 100
```

The precision controls decimal approximations rather than changing exact symbolic values.

---

## Timeout

Set a 60-second calculation timeout:

```text
:timeout 60
```

The timeout can be adjusted according to the workload.

---

## Angle Mode

Degree:

```text
:deg
```

Radian:

```text
:rad
```

---

# Performance Philosophy

The application is designed to keep the interface responsive even when mathematical operations are expensive.

Instead of:

```text
UI
 |
 +--> calculation
       |
       +--> calculation takes 2 minutes
       |
       +--> UI freezes
```

the architecture aims for:

```text
UI
 |
 +--> Engine process
       |
       +--> calculation
       |
       +--> calculation takes 2 minutes
       |
       +--> UI remains responsive
       |
       +--> user presses Esc
       |
       +--> process terminated
```

This is particularly useful for symbolic mathematics where computational complexity can be difficult to predict.

---

# Roadmap

Potential future improvements include:

- Plotting
- Graph rendering
- LaTeX input
- LaTeX output
- PDF export
- Calculation export
- Searchable history
- More matrix operations
- Additional symbolic functions
- More configurable themes
- Extended automated testing
- Standalone executable releases
- Plugin architecture
- Mathematical documentation inside the application

---

# Reporting Bugs

When reporting a calculation or application issue, include:

```text
Operating System:
Python version:
Textual version:
SymPy version:

Expression:

Expected result:

Actual result:

Error message:
```

For mathematical problems, always include the exact expression that produced the problem.

---

# License

CUI Calculator is released under the MIT License.

See:

```text
LICENSE
```

for the complete license.

---

# Credits

CUI Calculator is built with:

<div align="center" style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">

<a href="https://www.python.org/">
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
</a>

<a href="https://textual.textualize.io/">
<img src="https://img.shields.io/badge/Textual-6C5CE7?style=for-the-badge">
</a>

<a href="https://www.sympy.org/">
<img src="https://img.shields.io/badge/SymPy-3B5526?style=for-the-badge">
</a>

<a href="https://github.com/Textualize/rich">
<img src="https://img.shields.io/badge/Rich-000000?style=for-the-badge">
</a>

</div>

---

# Project Philosophy

CUI Calculator is built around five principles.

### Exactness

Preserve mathematical meaning whenever possible.

```text
1/3
```

should remain:

```text
1/3
```

rather than being silently converted to a rounded decimal.

### Transparency

Clearly distinguish:

```text
Exact result
```

from:

```text
Approximation
```

### Responsiveness

Expensive mathematics should not freeze the interface.

### Recoverability

If the calculation process fails, it should be possible to restart it and restore the previous state.

### Practicality

Large mathematical capabilities should be balanced with sensible resource limits.

---

# Summary

CUI Calculator combines:

```text
Exact Arithmetic
        +
Symbolic Mathematics
        +
Calculus
        +
Number Theory
        +
Combinatorics
        +
Linear Algebra
        +
Statistics
        +
Big Integers
        +
Custom Functions
        +
Persistent State
        +
Process Isolation
        +
Cancellation
        +
Responsive TUI
```

The result is a terminal-based mathematical environment designed for users who want more than a conventional calculator.

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&height=3&section=footer" width="100%"/>

<br><br>

<strong>CUI Calculator</strong>

<br>

Exact mathematics in a terminal interface.

<br><br>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:764ba2,100:667eea&height=140&section=footer" width="100%"/>

</div>
