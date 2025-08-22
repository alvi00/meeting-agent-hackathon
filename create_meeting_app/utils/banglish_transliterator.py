import os
from avro import parse
import fasttext  # Added missing import

# 1) Point to the fastText lid model
MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'lid.176.bin')
)
lang_model = fasttext.load_model(MODEL_PATH)

def is_bangla_word(token: str) -> bool:
    """
    Returns True if fastText predicts this token is Bangla.
    """
    label = lang_model.predict(token.lower(), k=1)[0][0]  # e.g. "__label__bn"
    return label == "__label__bn"

def banglish_to_bangla(text: str) -> str:
    """
    Tokenizes on whitespace, transliterates Bangla words from Roman to Bangla script,
    leaves English tokens unchanged.
    """
    tokens = text.split()
    out = []
    for tok in tokens:
        if is_bangla_word(tok):
            try:
                bn = parse(tok)  # Uses Avro phonetics from avro.py
                out.append(bn)
            except Exception:
                out.append(tok)  # Fallback if transliteration fails
        else:
            out.append(tok)
    return " ".join(out)