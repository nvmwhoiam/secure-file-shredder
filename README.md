# 🔥 Secure File Shredder Pro

_A military-grade secure deletion tool that ensures sensitive files are permanently destroyed beyond any possible recovery_

---

## 📌 Features

✔️ Military-Grade File Destruction

- Multiple overwrite standards including DoD 5220.22-M (3-pass) and Gutmann (35-pass)
- Configurable security levels (1-35 passes) with intelligent pattern selection
- Advanced pattern algorithms (zero fill, random data, alternating bits)

✔️ Complete Data Sanitization

- Recursive folder shredding with directory structure destruction
- Free space wiping to eliminate previously deleted file remnants
- Comprehensive metadata destruction (timestamps, filenames, filesystem artifacts)

✔️ Enterprise-Grade Security

- Smart protected directory detection with customizable exclusion lists
- File handle verification prevents shredding of locked files
- Verification layer confirms complete unrecoverability

✔️ Professional Workflow

- Parallel processing engine (configurable worker threads)
- Adaptive chunk sizing for optimal performance
- Detailed audit logging with forensic-grade timestamps
- Progress tracking with ETA calculation

✔️ Dual Interface

- Intuitive GUI with drag & drop functionality
- Powerful CLI for automated/scripted operations
- Cross-platform support (Windows 10/11, macOS 10.15+, Linux)

## 🛡️ Security Implementation Details

- 🔐 Overwrite Patterns:

  - Standard Patterns (Zero Fill, One Fill, Random)
  - DoD 5220.22-M (3-pass: 0x55, 0xAA, Random)
  - Gutmann Method (35 specialized passes)
  - Custom pattern configuration

- 🔐 Complete Data Removal:

  - Multi-phase metadata destruction
  - Filesystem artifact elimination
  - Secure directory tree removal
  - Free space sanitization

- 🔐 Protection Systems:
  - Protected directory whitelist/blacklist
  - Process-level file lock detection
  - Multi-stage confirmation dialogs
  - Operation verification layer

## ⚙️ Technical Specifications

- System Requirements:

  - **Python 3.9 or later** installed.
  - 50MB disk space
  - No admin rights required

- Performance Benchmarks (1GB file on NVMe SSD):

  - Basic 3-pass: ~22 seconds
  - DoD Standard: ~45 seconds
  - Gutmann 35-pass: ~210 seconds
  - Free Space Wipe: Varies by capacity

- Resource Usage:
  - CPU: 15-30% (scales with worker threads)
  - RAM: <100MB typical
  - Disk I/O: Optimized sequential operations

## ⚙️ Installation

1.  Clone the repository:

```bash
git clone https://github.com/nvmwhoiam/secure-file-shredder.git
```

2.  Navigate to the project directory:

```bash
cd secure-file-shredder
```

3.  Install dependencies:

```bash
pip install tkinterdnd2
```

## 🚀 Usage

### GUI Mode (Default)

Launch the graphical interface

```bash
python secure-file-shredder.py
```

### CLI Mode (Command Line)

**Basic file shredding**

```bash
python secure-file-shredder.py --path file1.txt file2.jpg --passes 3
```

**Recursive folder shredding**

```bash
python secure-file-shredder.py --path ~/temp/ --recursive
```

**Wipe free space on C: drive**

```bash
python secure-file-shredder.py  --wipe-free-space --target C:
```

## ⚙️ Advanced CLI Mode (Command Line) Options

**Basic file shredding**

```bash
python secure-file-shredder.py --path "file.txt"
```

**Recursive shredding**

```bash
python secure-file-shredder.py --path ~/docs/ --recursive
```

**Pass selection**

```bash
python secure-file-shredder.py --path x --passes 7
```

**Pattern selection**

```bash
python secure-file-shredder.py --path x --pattern gutmann
```

**Free space wipe**

```bash
python secure-file-shredder.py --wipe-free-space C:
```

## ⚠️ Important Security Notice

### THIS IS A DATA DESTRUCTION TOOL!

**All processed files are:**

- Permanently destroyed at physical storage level
- Unrecoverable by any software or hardware means
- Verified as completely obliterated

**⚠ WARNING:**

- System files are protected by default
- No undo functionality exists
- Free space wiping requires significant temporary storage
- For maximum security, combine with physical destruction
  for highly sensitive media

## 💻 Technology Stack

🟢 Python 3.x
🟡 Tkinter (GUI)
🔵 tkinterdnd2 (Drag & Drop)

## Contact

If you have any questions or need assistance, please do not hesitate to reach out. I apologize if any part of this setup is not clear; this is my first major project, and I am putting in continuous effort to improve it. Feel free to contact me at [info@sadevworks.com](mailto:info@sadevworks.com) or open an issue on the [GitHub Repository](https://github.com/nvmwhoiam/secure-file-shredder).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Author

- Email: [info@sadevworks.com](mailto:info@sadevworks.com)
- Website: [sadevworks.com](https://sadevworks.com)
- GitHub: [@nvmwhoiam](https://github.com/nvmwhoiam/)
