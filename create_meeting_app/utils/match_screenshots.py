from sentence_transformers import SentenceTransformer, util
from create_meeting_app.models import Screenshot

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def match_screenshots(transcript, summary_lines):
    if not summary_lines:
        raise ValueError("Summary is empty. Cannot match to screenshots.")

    segs = list(transcript.segments.all())
    if not segs:
        raise ValueError("Transcript has no segments. Cannot match screenshots.")

    seg_text = [s.text for s in segs]
    seg_embs = model.encode(seg_text, convert_to_tensor=True)
    sum_embs = model.encode(summary_lines, convert_to_tensor=True)

    matches = []
    for idx, emb in enumerate(sum_embs):
        sims = util.cos_sim(emb, seg_embs)[0]
        best = sims.argmax().item()
        t0 = segs[best].start_time
        shots = transcript.meeting.screenshots.all()
        if not shots:
            raise ValueError("No screenshots available to match.")
        shot = min(shots, key=lambda s: abs((s.created - transcript.created) - t0))
        matches.append((summary_lines[idx], shot.image_path))

    return matches
