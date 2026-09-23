# PI Matrix Computation Engine

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Textual-TUI-000000?style=for-the-badge" alt="Textual">
  <img src="https://img.shields.io/badge/mpmath-High%20Precision-4B8BBE?style=for-the-badge" alt="mpmath">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<p align="center">
  <strong>A terminal-based high-precision π computation engine with a Matrix-inspired interface.</strong>
</p>

<p align="center">
  Calculate, preview, hash, measure, and save high-precision π values directly from the terminal.
</p>

---

## Overview

**PI Matrix Computation Engine** is a Python-based terminal user interface designed for high-precision computation of π.

The application combines:

- High-precision arithmetic using `mpmath`
- A reactive terminal interface powered by `Textual`
- Background computation using Python threads
- SHA-256 integrity verification
- Configurable output directories
- Live progress and computation metrics
- Matrix-inspired animated terminal visuals

The application is designed as a computational experiment and a demonstration of building interactive terminal applications with Python.

---

## Features

### High-Precision π

Uses `mpmath` arbitrary-precision arithmetic to generate π with a user-defined number of digits.

### Matrix-Style Interface

The terminal interface includes an animated mathematical background containing numerical and mathematical symbols.

### Background Computation

The computation runs outside the main Textual event loop using:

```python
asyncio.to_thread()
```

This prevents the UI from becoming completely unresponsive during computation.

### Progress Monitoring

The interface provides a visual computation pipeline and progress indicator while the calculation is running.

### SHA-256 Verification

After generating the result, the application creates a SHA-256 hash of the generated π string.

This can be used to verify that the saved output has not been modified.

### Performance Metrics

The application reports:

- Requested digits
- Computation time
- Approximate digits per second
- Output file size

### Automatic Output Directory

The output directory is created automatically if it does not exist.

Default:

```text
./DB/.TXT
```

---

## Requirements

### Software

- Python 3.10 or newer
- `pip`
- A terminal that supports Textual's terminal interface

### Python Dependencies

```text
python-dotenv
mpmath
textual
```

All dependencies are listed in:

```text
requirements.txt
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/DevMuhammadHussnain/Itz-Python.git
```

Enter the project directory:

```bash
cd Itz-Python
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

---

## Running the Application

Run the Python application:

```bash
python your_script.py
```

Replace `your_script.py` with the actual Python filename containing the application.

---

## Configuration

The application supports an optional `.env` file.

Create:

```text
.env
```

Then specify:

```env
PI_OUTPUT_DIR=./DB/.TXT
```

For example:

```env
PI_OUTPUT_DIR=./output
```

The application will automatically create the configured directory when necessary.

### Default Configuration

If `PI_OUTPUT_DIR` is not defined, the application uses:

```text
./DB/.TXT
```

---

## Output

After a successful calculation, the generated π value is saved as:

```text
pi_matrix_<digits>_digits.txt
```

For example:

```text
pi_matrix_25000_digits.txt
```

The output directory depends on the `PI_OUTPUT_DIR` configuration.

Example:

```text
DB/
└── .TXT/
    └── pi_matrix_25000_digits.txt
```

---

## Computation Pipeline

The application processes a request through several stages.

```text
INPUT
  │
  ▼
Validate digit count
  │
  ▼
Allocate precision context
  │
  ▼
Initialize high-precision engine
  │
  ▼
Calculate π
  │
  ▼
Serialize result
  │
  ▼
Save TXT file
  │
  ▼
Generate SHA-256
  │
  ▼
Calculate metrics
  │
  ▼
Display preview
  │
  ▼
COMPLETE
```

---

## Accuracy

The application uses `mpmath` arbitrary-precision arithmetic.

The requested precision is configured using:

```python
mp.dps = digits + 20
```

The additional precision provides guard digits during the computation.

The generated value is then converted to a string with:

```python
mp.nstr(mp.pi, digits + 1)
```

The exact numerical behavior and performance depend on the installed `mpmath` version and the hardware running the application.

---

# Warnings

## Large Digit Counts Can Be Expensive

High-precision calculations require increasing amounts of:

- CPU time
- RAM
- Storage
- Processing resources

The application currently limits the requested precision to:

```text
5,000,000 digits
```

This limit exists to reduce the possibility of accidentally requesting an extremely large computation.

Even below this limit, performance can vary significantly between systems.

# Possible Errors

## `ModuleNotFoundError`

Example:

```text
ModuleNotFoundError: No module named 'textual'
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

If you are using a virtual environment, make sure it is activated first.

---

## `FileNotFoundError`

If the configured output path points to an invalid location, check:

```env
PI_OUTPUT_DIR=./DB/.TXT
```

The application automatically attempts to create the directory.

---

## `PermissionError`

Example:

```text
PermissionError: [Errno 13] Permission denied
```

This can happen when Python does not have permission to write to the configured output directory.

Try using a directory where your user account has write access.

For example:

```env
PI_OUTPUT_DIR=./output
```

---

## Invalid Digit Count

If the input contains something other than a positive integer, the application rejects it.

Invalid examples:

```text
abc
10.5
-100
1,000
```

Valid examples:

```text
100
1000
25000
100000
```

---

## Maximum Digit Limit

Requests above:

```text
5,000,000
```

are rejected by the application.

The limit can be changed in the source code if required, but increasing it may substantially increase resource consumption.

---

## Terminal Compatibility

Textual applications depend on terminal capabilities.

If the interface looks incorrect, try running the application in a modern terminal emulator.

Examples include:

- macOS Terminal
- iTerm2
- Windows Terminal
- modern Linux terminals

---

# Cancellation Warning

The application contains a cancellation interface, but cancellation of an already-running CPU-bound `mpmath` calculation is cooperative.

A cancellation request does **not** forcibly terminate an executing Python calculation.

For extremely large calculations, the worker may therefore continue consuming resources until the current operation completes.

---

# Performance

Performance depends on several factors:

- CPU architecture
- CPU frequency
- Number of CPU cores
- Available RAM
- Python version
- `mpmath` version
- Operating system
- Requested precision

The application calculates an approximate throughput using:

```text
digits / elapsed_time
```

The displayed value should be treated as an application-level measurement rather than a standardized benchmark.

---

# Keyboard Controls

| Key | Action               |
| --- | -------------------- |
| `Q` | Exit application     |
| `C` | Request cancellation |
| `R` | Reset interface      |

---

# Technical Stack

| Technology    | Purpose                         |
| ------------- | ------------------------------- |
| Python        | Application runtime             |
| Textual       | Terminal UI                     |
| mpmath        | Arbitrary-precision mathematics |
| python-dotenv | Environment configuration       |
| asyncio       | Asynchronous UI operations      |
| threading     | Background computation          |
| hashlib       | SHA-256 generation              |
| pathlib       | File and directory management   |

---

# Security and Data

The application does not require a database or external API for π computation.

Generated output is stored locally according to:

```env
PI_OUTPUT_DIR
```

The application does not need to transmit the calculated π value to an external server.

If the project is modified to process sensitive data or communicate with external services, those changes should be reviewed separately.

---

# Development

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python your_script.py
```

---

# Limitations

Current limitations include:

- π generation uses `mpmath` rather than a custom implementation of the Chudnovsky algorithm.
- Progress displayed during computation is an activity indicator rather than a mathematically measured percentage of completed digits.
- CPU-bound calculations cannot be forcibly interrupted safely through the current cooperative cancellation mechanism.
- Extremely large precision requests can require substantial system resources.
- Performance measurements are hardware-dependent.
- Generated TXT files can become very large.

---

# Future Improvements

Potential improvements include:

- True computation progress reporting
- Reliable worker cancellation
- Custom Chudnovsky implementation
- Multiple precision algorithms
- Binary output support
- Resume interrupted calculations
- Calculation history
- Configurable themes
- Export to additional formats
- Benchmark mode
- Multi-process computation
- Verification against known π digit sequences

---

# License

This project is licensed under the MIT License.

See the `LICENSE` file for details.

---

# Author

**Muhammad Hussnain**

GitHub:

https://github.com/DevMuhammadHussnain

Repository:

https://github.com/DevMuhammadHussnain/Itz-Python

---

<p align="center">
  Built with Python and Textual.
</p>
