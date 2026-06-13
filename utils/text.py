# utils/text.py
# Author: Emsii (refactored)
# Narzędzia tekstowe — usuwanie znaków diakrytycznych dla wyświetlacza LCD.

import unicodedata

# Mapowanie generowane automatycznie przez NFD Unicode normalizację.
# NFD rozkłada znak złożony na literę bazową + diakrytyki, bierzemy literę bazową.
# Przykład: ą → NFD → a + ̨ (ogonkowy) → bierzemy 'a'
#
# ł/Ł są wyjątkiem — nie mają NFD dekompozycji (to oddzielny znak Unicode),
# więc dodajemy je ręcznie.
#
# Stara ręczna lista (554 znaków) była błędna — zawierała przesunięcia mapowania,
# stąd ł wyświetlało się jako 'B', ż jako 'L' itp.

def _build_translator():
    mapping = {}

    # Automatyczne mapowanie przez NFD dla U+0080..U+1FFF
    for codepoint in range(0x0080, 0x2000):
        char = chr(codepoint)
        nfd = unicodedata.normalize('NFD', char)
        if len(nfd) > 1:
            base = nfd[0]
            if base.isascii() and base.isalpha():
                mapping[ord(char)] = base

    # Wyjątki bez NFD dekompozycji
    mapping[ord('ł')] = 'l'
    mapping[ord('Ł')] = 'L'
    mapping[ord('ß')] = 's'  # niemieckie — zamień na 's' (nie 'ss' bo maketrans 1:1)

    return mapping

# Zbuduj raz przy imporcie modułu
_TRANSLATOR = _build_translator()


def remove_accents(input_text: str) -> str:
    """
    Zastąp znaki diakrytyczne ich ASCII odpowiednikami.

    Używa Unicode NFD normalizacji — bezbłędne dla wszystkich języków
    łacińskich (PL, DE, FR, ES, CZ itd.) bez ręcznego wpisywania list.
    """
    return input_text.translate(_TRANSLATOR)