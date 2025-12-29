#!/usr/bin/env python
"""
Compile Django translation files (.po to .mo) using pure Python.
This script doesn't require gettext tools to be installed.

Usage:
    python compile_translations.py
"""

import os
import struct
import array
from pathlib import Path


def generate_mo_file(po_file_path, mo_file_path):
    """
    Convert a .po file to .mo file format.
    Based on msgfmt functionality but pure Python.
    """
    messages = {}
    current_msgid = None
    current_msgstr = None
    header_msgstr = None

    print(f"Compiling {po_file_path}...")

    with open(po_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            if line.startswith('msgid '):
                if current_msgid is not None and current_msgstr is not None:
                    if current_msgid == '':
                        header_msgstr = current_msgstr
                    else:
                        messages[current_msgid] = current_msgstr
                current_msgid = line[7:-1]
                current_msgstr = None

            elif line.startswith('msgstr '):
                msg_line = line[8:-1].replace('\\n', '\n')
                current_msgstr = msg_line

            elif line.startswith('"') and current_msgstr is not None:
                msg_line = line[1:-1].replace('\\n', '\n')
                current_msgstr += msg_line

            elif line.startswith('"') and current_msgid is not None:
                current_msgid += line[1:-1]

    if current_msgid is not None and current_msgstr is not None:
        if current_msgid == '':
            header_msgstr = current_msgstr
        else:
            messages[current_msgid] = current_msgstr

    if not header_msgstr:
        header_msgstr = 'Content-Type: text/plain; charset=UTF-8\n'

    messages[''] = header_msgstr

    keys = sorted(messages.keys())
    offsets = []
    ids = []
    strs = []

    for key in keys:
        ids.append(key.encode('utf-8'))
        strs.append(messages[key].encode('utf-8'))

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + sum(len(k) + 1 for k in ids)

    koffsets = []
    voffsets = []

    for i, (msgid, msgstr) in enumerate(zip(ids, strs)):
        koffsets.append((len(msgid), keystart))
        keystart += len(msgid) + 1
        voffsets.append((len(msgstr), valuestart))
        valuestart += len(msgstr) + 1

    with open(mo_file_path, 'wb') as f:
        f.write(struct.pack('Iiiiiii',
            0x950412de,
            0,
            len(keys),
            7 * 4,
            7 * 4 + len(keys) * 8,
            0,
            0))

        for length, offset in koffsets:
            f.write(struct.pack('ii', length, offset))

        for length, offset in voffsets:
            f.write(struct.pack('ii', length, offset))

        for msgid in ids:
            f.write(msgid)
            f.write(b'\x00')

        for msgstr in strs:
            f.write(msgstr)
            f.write(b'\x00')

    print(f"  Created {mo_file_path}")
    print(f"  Compiled {len(messages)} messages")


def compile_all_translations():
    """
    Find and compile all .po files in the locale directory.
    """
    base_dir = Path(__file__).parent
    locale_dir = base_dir / 'locale'

    if not locale_dir.exists():
        print(f"Error: locale directory not found at {locale_dir}")
        return

    compiled_count = 0

    for po_file in locale_dir.rglob('*.po'):
        mo_file = po_file.with_suffix('.mo')

        try:
            generate_mo_file(str(po_file), str(mo_file))
            compiled_count += 1
        except Exception as e:
            print(f"Error compiling {po_file}: {e}")

    print(f"\nCompilation complete! Compiled {compiled_count} file(s).")
    print("\nTo see translations:")
    print("1. Restart your Django server")
    print("2. Refresh your browser")
    print("3. Use the language switcher in the header")


if __name__ == '__main__':
    print("=" * 60)
    print("Django Translation Compiler (Pure Python)")
    print("=" * 60)
    print()
    compile_all_translations()
