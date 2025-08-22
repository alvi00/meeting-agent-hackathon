# create_meeting_app/utils/match_clip_embeddings.py
import numpy as np
import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from typing import List, Optional, Dict, Tuple

# optional OCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

device = "cuda" if torch.cuda.is_available() else "cpu"

# initialize model & processor once (keep name compatibility)
CLIP_MODEL = "openai/clip-vit-base-patch32"
_model = CLIPModel.from_pretrained(CLIP_MODEL).to(device)
_processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

def _batchify(lst, batch_size=16):
    for i in range(0, len(lst), batch_size):
        yield lst[i:i+batch_size]

def _compute_text_embeddings(sentences: List[str], batch_size=32) -> torch.Tensor:
    if not sentences:
        return torch.empty((0, _model.visual_projection.weight.shape[1]), device=device)
    embeds = []
    for batch in _batchify(sentences, batch_size):
        inputs = _processor(text=batch, return_tensors="pt", padding=True, truncation=True).to(device)
        with torch.no_grad():
            emb = _model.get_text_features(**inputs).float()
        embeds.append(emb)
    return torch.cat(embeds, dim=0)

def _compute_image_embeddings(image_paths: List[str], batch_size=8) -> torch.Tensor:
    if not image_paths:
        return torch.empty((0, _model.visual_projection.weight.shape[1]), device=device)
    embeds = []
    for batch in _batchify(image_paths, batch_size):
        imgs = [Image.open(p).convert("RGB") for p in batch]
        inputs = _processor(images=imgs, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            emb = _model.get_image_features(**inputs).float()
        embeds.append(emb)
    return torch.cat(embeds, dim=0)

def _extract_ocr_texts(paths: List[str]) -> List[str]:
    if not OCR_AVAILABLE:
        return [""] * len(paths)
    texts = []
    for p in paths:
        try:
            img = Image.open(p).convert("RGB")
            txt = pytesseract.image_to_string(img).strip()
            texts.append(txt)
        except Exception:
            texts.append("")
    return texts

def _temporal_score_matrix(sent_ts: Optional[List[float]], shot_ts: Optional[List[float]], sigma_seconds: float = 7.0):
    if sent_ts is None or shot_ts is None:
        return None
    s = np.array(sent_ts)[:, None]
    sh = np.array(shot_ts)[None, :]
    diff = np.abs(s - sh)
    return np.exp(-(diff**2) / (2 * sigma_seconds**2))  # shape (n_sent, n_shot)

def match_summary_to_screenshots(
    summary_sentences: List[str],
    screenshot_paths: List[str],
    summary_timestamps: Optional[List[float]] = None,        # seconds, optional
    screenshot_timestamps: Optional[List[float]] = None,     # seconds, optional
    top_k: int = 1,
    use_ocr: bool = True,
    weight_visual: float = 0.6,
    weight_ocr_text: float = 0.25,
    weight_time: float = 0.15,
    visual_batch_size: int = 8
) -> Dict[str, List[Tuple[str, float]]]:
    """
    Backwards-compatible matcher. Returns {sentence: [(path, score), ...]}.
    If timestamps aren't provided, time contribution is ignored.
    """

    matches: Dict[str, List[Tuple[str, float]]] = {}

    # quick guards
    if not summary_sentences or not screenshot_paths:
        return matches

    # normalize weights
    wsum = weight_visual + weight_ocr_text + weight_time
    if wsum <= 0:
        raise ValueError("At least one positive weight required")
    weight_visual /= wsum
    weight_ocr_text /= wsum
    weight_time /= wsum

    # compute embeddings
    text_emb = _compute_text_embeddings(summary_sentences, batch_size=32)  # (n_sent, d)
    image_emb = _compute_image_embeddings(screenshot_paths, batch_size=visual_batch_size)  # (n_img, d)

    if text_emb.shape[0] == 0 or image_emb.shape[0] == 0:
        return matches

    text_emb = F.normalize(text_emb, dim=-1)
    image_emb = F.normalize(image_emb, dim=-1)

    visual_sim = (text_emb @ image_emb.T).cpu().numpy()  # cosine in [-1,1]
    visual_sim = (visual_sim + 1.0) / 2.0  # scale to [0,1]

    # OCR sim (optional)
    if use_ocr:
        ocr_texts = _extract_ocr_texts(screenshot_paths)
        ocr_emb = _compute_text_embeddings(ocr_texts, batch_size=32)
        if ocr_emb.shape[0] == image_emb.shape[0]:
            ocr_emb = F.normalize(ocr_emb, dim=-1)
            ocr_sim = (text_emb @ ocr_emb.T).cpu().numpy()
            ocr_sim = (ocr_sim + 1.0) / 2.0
        else:
            ocr_sim = np.zeros_like(visual_sim)
    else:
        ocr_sim = np.zeros_like(visual_sim)

    # temporal sim
    time_sim = _temporal_score_matrix(summary_timestamps, screenshot_timestamps)
    if time_sim is None:
        time_sim = np.zeros_like(visual_sim)

    # combine
    combined = (weight_visual * visual_sim) + (weight_ocr_text * ocr_sim) + (weight_time * time_sim)

    n_sent, n_img = combined.shape
    for i, sent in enumerate(summary_sentences):
        scores = combined[i]
        idxs = np.argsort(scores)[::-1][:top_k]
        results = []
        for j in idxs:
            # store only if non-zero score (you can adjust threshold later where needed)
            results.append((screenshot_paths[j], float(scores[j])))
        matches[sent] = results

    return matches