"""
Enhanced BIOS loader for GTU‑C312 simulator.
Parses a “.gtu” program file and returns two ordered lists:
    * data_segment        – list[(address:int, value:int)] (ascending by address)
    * instruction_segment – list[(address:int, instr:str)] (ascending by address)

Key features vs. previous implementation
---------------------------------------
1. **Strict section handling** – DATA and INSTRUCTION sections can appear in any order but may not be nested.
2. **Flexible value syntax**   – supports “addr=value”, “addr = value”, or “addr   value”.
3. **Case‑insensitive markers** – BEGIN DATA SECTION / END DATA SECTION etc.
4. **Early duplicate detection** – warns and keeps first occurrence.
5. **Code/Data overlap check** – raises ValueError before returning if an address is defined in both segments.
6. **Sorted output**           – output lists are ascending by address for deterministic loading.
7. **Verbose diagnostics**     – precise file & line info in all warnings/errors.

© 2025 – Helper rewrite for ChatGPT user.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple

DataSeg  = List[Tuple[int, int]]
InstrSeg = List[Tuple[int, str]]

_BEGIN_DATA        = "BEGIN DATA SECTION"
_END_DATA          = "END DATA SECTION"
_BEGIN_INSTR       = "BEGIN INSTRUCTION SECTION"
_END_INSTR         = "END INSTRUCTION SECTION"


def _strip_comment(line: str) -> str:
    """Remove trailing # … comment (but not inside literals)."""
    hash_pos = line.find("#")
    return line[:hash_pos] if hash_pos != -1 else line


def _warn(msg: str) -> None:
    print(f"BIOS Warning: {msg}")


def load_and_parse_gtu_program(filepath: str | Path,
                               *,
                               allow_overlap: bool = False) -> Tuple[DataSeg, InstrSeg]:
    """Parse the given .gtu file, returning (data_segment, instruction_segment).

    Raises FileNotFoundError or ValueError on severe problems unless handled
    by caller. When *allow_overlap* is False (default), encountering the same
    address in both data and code sections aborts with ValueError.
    """
    fp = Path(filepath)
    if not fp.is_file():
        raise FileNotFoundError(fp)

    data_map: dict[int, int] = {}
    code_map: dict[int, str] = {}

    in_data = in_code = False

    for line_no, raw in enumerate(fp.read_text().splitlines(), start=1):
        stripped = _strip_comment(raw).strip()
        if not stripped:
            continue  # blank or full‑line comment

        upper = stripped.upper()
        if upper == _BEGIN_DATA:
            in_data, in_code = True, False
            continue
        if upper == _END_DATA:
            in_data = False
            continue
        if upper == _BEGIN_INSTR:
            in_code, in_data = True, False
            continue
        if upper == _END_INSTR:
            in_code = False
            continue

        # --- DATA line ---
        if in_data:
            # Accept "ADDR = VALUE" or "ADDR VALUE"
            if "=" in stripped:
                addr_part, val_part = stripped.split("=", 1)
            else:
                parts = stripped.split()
                if len(parts) != 2:
                    _warn(f"Invalid data format at {fp}:{line_no}: '{raw.strip()}'")
                    continue
                addr_part, val_part = parts
            try:
                addr = int(addr_part.strip())
                val = int(val_part.strip())
            except ValueError:
                _warn(f"Non‑integer data at {fp}:{line_no}: '{raw.strip()}'")
                continue
            if addr in data_map:
                _warn(f"Duplicate data addr {addr} – keeping first value ({data_map[addr]}), ignoring {val}")
                continue
            data_map[addr] = val
            continue

        # --- CODE line ---
        if in_code:
            if ":" not in stripped:
                _warn(f"Missing ':' in instruction at {fp}:{line_no}: '{raw.strip()}'")
                continue
            addr_part, instr_part = stripped.split(":", 1)
            try:
                addr = int(addr_part.strip())
            except ValueError:
                _warn(f"Non‑integer instruction address at {fp}:{line_no}: '{raw.strip()}'")
                continue
            instr = instr_part.strip().upper()
            if not instr:
                _warn(f"Empty instruction at {fp}:{line_no}")
                continue
            if addr in code_map:
                _warn(f"Duplicate instruction addr {addr} – keeping first instruction '{code_map[addr]}', ignoring '{instr}'")
                continue
            code_map[addr] = instr
            continue

        # If we reach here, line is outside any recognised section
        _warn(f"Line outside section at {fp}:{line_no}: '{raw.strip()}'")

    # ---------- Post‑processing ----------
    overlap = set(data_map).intersection(code_map)
    if overlap and not allow_overlap:
        raise ValueError(f"Overlapping DATA/CODE addresses detected: {sorted(overlap)}")

    data_segment: DataSeg = sorted(data_map.items())
    instr_segment: InstrSeg = sorted(code_map.items())
    return data_segment, instr_segment


# Optional self‑test when run directly ---------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="Parse .gtu and print segments.")
    parser.add_argument("file", help="Path to .gtu program")
    parser.add_argument("--allow-overlap", action="store_true", help="Permit overlapping addresses (data overwrites code)")
    ns = parser.parse_args()

    try:
        data, code = load_and_parse_gtu_program(ns.file, allow_overlap=ns.allow_overlap)
    except Exception as exc:
        print(f"Fatal: {exc}")
        sys.exit(1)

    print("\n--- DATA SEGMENT ---")
    for a, v in data:
        print(f"{a:>6} = {v}")

    print("\n--- INSTRUCTION SEGMENT ---")
    for a, instr in code:
        print(f"{a:>6}: {instr}")