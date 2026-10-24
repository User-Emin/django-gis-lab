#!/usr/bin/env python3
"""Haakjesbalans voor AutoLISP zonder AutoCAD: negeert ;-commentaar en "strings" (met \\-escapes).

Gebruik: python3 -I haakjes_check.py bestand.lsp   -> exit 0 als alles klopt.
Dit is GEEN syntaxcontrole van AutoLISP: alleen ( ) en ongesloten strings.
"""

import sys


def check(tekst):
    diepte, regel, in_str, esc, open_regels, defuns = 0, 1, False, False, [], 0
    i = 0
    while i < len(tekst):
        c = tekst[i]
        if c == "\n":
            regel += 1
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == ";":
            while i < len(tekst) and tekst[i] != "\n":
                i += 1
            continue
        elif c == '"':
            in_str = True
        elif c == "(":
            diepte += 1
            open_regels.append(regel)
            if diepte == 1 and tekst[i : i + 7] == "(defun ":
                defuns += 1
        elif c == ")":
            diepte -= 1
            if diepte < 0:
                return f"FOUT: ')' te veel op regel {regel}"
            open_regels.pop()
        i += 1
    if in_str:
        return "FOUT: string niet gesloten"
    if diepte:
        return f"FOUT: {diepte} '(' niet gesloten (geopend op regel {open_regels[-1]})"
    return f"OK: haakjes in balans, {regel} regels, {defuns} defun(s) op het hoogste niveau"


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        uit = check(f.read())
    print(f"{sys.argv[1].split('/')[-1]}: {uit}")
    sys.exit(0 if uit.startswith("OK") else 1)
