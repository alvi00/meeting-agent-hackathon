#mixed_transliterator.py
import os
import fasttext
import re
from bnunicodenormalizer.normalizer import Normalizer
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from spellchecker import SpellChecker

# Load FastText model for language identification
MODEL = fasttext.load_model("lid.176.bin")
bn_normalizer = Normalizer()
spell = SpellChecker()

# Dictionary path (default or via environment variable)
DICTIONARY_PATH = os.getenv("DICTIONARY_PATH", "BengaliDictionary/")

# Initialize Bangla-to-English dictionary
BANGLA_ENGLISH_DB = {}
try:
    # Load BengaliDictionary_17.txt (|english|bangla format)
    with open(os.path.join(DICTIONARY_PATH, "BengaliDictionary_17.txt"), "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) == 3 and parts[0] == '':  # Format: |english|bangla
                english = parts[1]
                bangla = parts[2]
                BANGLA_ENGLISH_DB[bangla] = english
    print(f"Loaded BengaliDictionary_17.txt from {DICTIONARY_PATH} successfully.")
except FileNotFoundError:
    print(f"Warning: BengaliDictionary_17.txt not found in {DICTIONARY_PATH}. Falling back to minimal dictionary.")

# Load loanwords from meeting_workflow/
LOANWORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "loanwords.txt")
PHONETIC_ENGLISH = {}
try:
    with open(LOANWORDS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if '|' in line:
                bangla, english = line.strip().split('|', 1)
                PHONETIC_ENGLISH[bangla] = english
    print(f"Loaded loanwords from {LOANWORDS_PATH} successfully.")
except FileNotFoundError:
    print(f"Warning: {LOANWORDS_PATH} not found. Using minimal PHONETIC_ENGLISH.")

# Common Bangla suffixes
BANGLA_SUFFIXES = ["ে", "র", "তে", "য়", "কে", "রা"]

# Known Bangla words and proper nouns to preserve
KNOWN_BANGLA = {"যাব", "আমি", "আপনার", "কাছে", "এর", "করে", "থেকে", "আমার", "ফাহমির"}

def is_probably_english(word):
    """Check if a word is likely English with a lower threshold."""
    clean = re.sub(r'[^\w\s]', '', word)
    if not clean:
        return False
    prediction, confidence = MODEL.predict(clean)[0][0], MODEL.predict(clean)[1][0]
    return prediction == '__label__en' and confidence > 0.7  # Reduced threshold

def clean_transliteration(latin):
    """Clean up transliterated text with improved mappings."""
    mappings = {
        "māinemija": "my name is",
        "ebharioẏāna": "everyone",
        "ṭuḍa": "today",
        "oẏārlḍa": "world",
        "ala": "all",
        "apha": "of",
        "ṭu": "to",
        "māi": "my",
        "klāsa": "class",
        "ājaka": "today",
        "śikhāvo": "teach",
        "inṭigreśana": "integration",
        "savāika": "all of you",
        "epha": "f",
        "oẏāna": "one",
        "mubhi": "movie",
        "dekhata": "watch",
        "valava": "will say",
        "ṭā": "the",
        "bhālo": "good",
    }
    if latin in mappings:
        return mappings[latin]
    corrected = spell.correction(latin)
    return corrected if corrected and is_probably_english(corrected) else latin

def bangla_to_english_phonetic(word):
    """Convert Bangla word to English equivalent."""
    if word in KNOWN_BANGLA:
        return None
    
    # Strip suffixes to find root word
    root_word = word
    for s in BANGLA_SUFFIXES:
        if word.endswith(s):
            root_word = word[:-len(s)]
            break
    
    # Check dictionary first
    if root_word in BANGLA_ENGLISH_DB:
        return BANGLA_ENGLISH_DB[root_word]
    
    # Check phonetic English mappings
    if root_word in PHONETIC_ENGLISH:
        return PHONETIC_ENGLISH[root_word]
    
    # Transliterate to Latin as fallback
    latin = transliterate(root_word, sanscript.BENGALI, sanscript.IAST)
    latin = re.sub(r'[^\w\s]', '', latin.lower())
    print(f"Transliterated {word} to {latin}")
    latin = clean_transliteration(latin)
    
    if is_probably_english(latin):
        return latin
    return None

def banglish_to_mixed(text):
    """Convert Banglish text to mixed Bangla-English, preserving original language."""
    words = re.findall(r'\S+|\n', text)
    
    normalized_words = []
    for word in words:
        norm_res = bn_normalizer(word)
        normalized = norm_res.get("normalized", word)
        normalized_words.append(normalized if normalized else word)
    
    mixed_words = []
    for word in normalized_words:
        if word == '\n':
            mixed_words.append(word)
            continue
        
        clean = re.sub(r'[^\w\s]', '', word)
        is_english = is_probably_english(word)
        
        if is_english:
            mixed_words.append(clean)  # Keep English as English
        elif word in PHONETIC_ENGLISH:
            mixed_words.append(PHONETIC_ENGLISH[word])
        else:
            english_equivalent = bangla_to_english_phonetic(word)
            if english_equivalent:
                mixed_words.append(english_equivalent)
            else:
                mixed_words.append(word)  # Keep Bangla as Bangla
    
    return ' '.join(mixed_words)