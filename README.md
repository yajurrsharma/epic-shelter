# EpicShelter

EpicShelter is a lightweight, high performance CLI backup engine built on variable-size chunking, content-addressed storage, and SQLite metadata tracking with compression.

---

## Features

- **Content-Addressed Deduplication:** Breaks files down into content-defined chunks to eliminate duplicate storage across multiple snapshots.
- **Zstandard Compression:** Automatically compresses data chunks using `zstd` level 1 for optimal speed and space saving.
- **ACID Metadata & Auto-Replication:** Uses SQLite WAL mode to log snapshots, automatically replicating metadata back to system user configuration directories (`~/.config/shelter/backups/`).
- **Cross Platform Vault Concealment:** Automatically creates and hides `.shelter`, which is the main `.db` storage system, across Linux, macOS, and Windows.

---

## Installation

Install the latest version directly from PyPI:
```bash
pip install epic-shelter
```
Or install the development version from GitHub:
```bash
pip install git+https://github.com/yajurrsharma/epic-shelter.git
```
---

## Usage

Launch the interactive CLI shell from anywhere in your terminal:
```bash
shelter
```
OR

```bash
python3 -m shelter
```

### Commands

Inside the `shelter` interactive shell:

- `manual` / `m` — Run in manual mode.
- `auto` / `automatic` / `a` — Run in automatic mode.
- `status` / `info` — Display vault status and path details.
- `help` / `?` — Show the help menu.
- `exit` / `quit` / `q` — Exit the shell.
---

# Availability

This project is completely open-source and open to changes.

## License

This project is licensed under the MIT License.
