#!/usr/bin/env python3
import os
import re
from pathlib import Path

CSV_DIR = Path('.')
LOG_FILE = CSV_DIR / 'translated_files_log.txt'

# Conservative word-level dictionary (deterministic). Extend as needed.
DICT = {
    'Aceptar': 'Aceitar', 'Aceptar.': 'Aceitar.', 'Aceptar!': 'Aceitar!','Aceptar?':'Aceitar?',
    'Aceptar;': 'Aceitar;', 'Aceptar,': 'Aceitar,',
    'Cancelar': 'Cancelar', 'Sí': 'Sim', 'Si': 'Se', 'No': 'Não',
    'Bienvenido': 'Bem-vindo', 'Bienvenida': 'Bem-vinda', 'Bienvenidos': 'Bem-vindos',
    'Cerrar': 'Fechar', 'Abrir': 'Abrir', 'Aceptar': 'Aceitar', 'Aceptar': 'Aceitar',
    'Aceptar': 'Aceitar', 'Reino': 'Reino', 'Reyes': 'Reis', 'Rey': 'Rei', 'Reina': 'Rainha',
    'Hijos': 'Filhos', 'Hijas': 'Filhas', 'Hijo': 'Filho', 'Hija': 'Filha',
    'Guardar': 'Salvar', 'Cargar': 'Carregar', 'Siguiente': 'Próximo', 'Anterior': 'Anterior',
    'Aceptar': 'Aceitar', 'Aceptar': 'Aceitar'
}

PLACEHOLDER_PATTERN = re.compile(r"\$[^\$]+\$|__PROTECTED_\d+__")
BRACKET_PATTERN = re.compile(r"\[.*?\]")


def detect_spanish_header(cols):
    # find index of column named SPANISH (case-insensitive)
    for i, c in enumerate(cols):
        if c.strip().upper() == 'SPANISH':
            return i
    # fallback: use 5th index if header weird
    if len(cols) > 5:
        return 5
    return None


def should_skip(text):
    if not text:
        return True
    if '\\n' in text:
        return True
    if BRACKET_PATTERN.search(text):
        return True
    if PLACEHOLDER_PATTERN.search(text):
        return True
    return False


def remove_leading_inverted_exclamation(text):
    if text.startswith('¡'):
        return text[1:]
    return text


def translate_text(text):
    if should_skip(text):
        return text, 'BLOQUEADO'
    orig = text
    text = remove_leading_inverted_exclamation(text)
    # simple token replace preserving case
    def repl(match):
        w = match.group(0)
        # exact match first
        if w in DICT:
            return DICT[w]
        # lowercase match
        lw = w.lower()
        for k, v in DICT.items():
            if k.lower() == lw:
                # preserve capitalization
                if w[0].isupper():
                    return v[0].upper() + v[1:]
                return v
        return w

    # replace word boundaries (letters, accents, apostrophes)
    translated = re.sub(r"[\wÁÉÍÓÚáéíóúÑñÜüçÇ]+", repl, text)
    # very conservative: if translation identical to input, mark as IGNORED
    status = 'TRADUZIDO' if translated != orig else 'IGNORADO'
    return translated, status


def process_file(path: Path):
    with path.open('r', encoding='utf-8', errors='replace') as f:
        lines = f.read().splitlines()

    if not lines:
        return 'IGNORADO', 0

    header = lines[0]
    cols = header.split(';')
    spanish_idx = detect_spanish_header(cols)
    if spanish_idx is None:
        return 'IGNORADO', 0

    out_lines = [header]
    translated_count = 0
    for ln in lines[1:]:
        if ln.startswith('#'):
            out_lines.append(ln)
            continue
        # Preserve exact semicolon layout: split left of Spanish column, extract Spanish, keep right as-is
        # split to get first spanish_idx fields (maxsplit=spanish_idx)
        left_parts = ln.split(';', spanish_idx)
        if len(left_parts) < spanish_idx + 1:
            # malformed line, keep as-is
            out_lines.append(ln)
            continue
        left = ';'.join(left_parts[:spanish_idx])
        rest = left_parts[spanish_idx]
        # rest contains the spanish column + remaining semicolons
        # separate spanish from the rest by splitting once
        if ';' in rest:
            span, right = rest.split(';', 1)
            right = ';' + right  # keep the separator
        else:
            span = rest
            right = ''

        orig_span = span
        new_span, status = translate_text(orig_span)
        if status == 'TRADUZIDO':
            translated_count += 1

        if left:
            new_line = left + ';' + new_span + right
        else:
            new_line = new_span + right

        out_lines.append(new_line)

    # overwrite file
    with path.open('w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(out_lines) + '\n')

    return 'TRADUZIDO', translated_count


def main():
    large_threshold = 10 * 1024
    results = []
    for file in sorted(CSV_DIR.glob('*.csv')):
        if file.name == LOG_FILE.name:
            continue
        size = file.stat().st_size
        if size <= large_threshold:
            continue
        status, count = process_file(file)
        results.append((file.name, 'SCRIPT', status))

    # write log
    with LOG_FILE.open('w', encoding='utf-8') as lf:
        for name, method, status in results:
            lf.write(f"{name};{method};{status}\n")

    print(f"Processed {len(results)} files. Log: {LOG_FILE}")


if __name__ == '__main__':
    main()
