# create_meeting_app/utils/qa_helper.py
import math
import requests
import numpy as np
from django.conf import settings
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# lazy-loaded embedder
_EMBEDDER = None
def get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDER

def chunk_text(text, chunk_words=220, overlap_words=40):
    """
    Break long text into overlapping word-based chunks.
    Returns list[str].
    """
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+chunk_words]
        chunks.append(" ".join(chunk))
        i += (chunk_words - overlap_words)
    return chunks

def retrieve_top_chunks(full_text, question, top_k=5):
    """
    Return top_k chunks (strings) and similarity scores.
    """
    if not full_text or not question:
        return [], []

    embedder = get_embedder()
    chunks = chunk_text(full_text)
    if not chunks:
        return [], []

    # embed chunks and question
    chunk_embeddings = embedder.encode(chunks, show_progress_bar=False)
    q_emb = embedder.encode([question], show_progress_bar=False)[0]

    sims = cosine_similarity([q_emb], chunk_embeddings)[0]
    idxs = list(np.argsort(sims)[::-1][:top_k])
    top_chunks = [chunks[i] for i in idxs]
    top_scores = [float(sims[i]) for i in idxs]
    return top_chunks, top_scores

def call_groq_chat(prompt, model="llama3-8b-8192", temperature=0.0, max_tokens=512):
    """
    Call Groq chat completions (if GROQ_API_KEY exists in settings).
    Returns the generated string or None on failure / not-configured.
    """
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        # swallow and return None so caller can fallback
        print("GROQ call failed:", e)
        return None
