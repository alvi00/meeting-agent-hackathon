import os
import io
from pathlib import Path
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from create_meeting_app.utils.match_clip_embeddings import match_summary_to_screenshots
from create_meeting_app.models import Meeting
from django.conf import settings
from django.utils import timezone
from bs4 import BeautifulSoup
from PIL import Image

# optional: small thumbnails to reduce PDF size (set to False to keep original images)
GENERATE_THUMBNAILS = True
THUMB_MAX_WIDTH = 1000  # pixels
THUMB_DIR_NAME = "summary_thumbs"
MATCH_CONFIDENCE_THRESHOLD = 0.35  # tune this (0..1)

def _get_section_items(soup, heading_text):
    """
    Find <h3> that contains heading_text, then read the next <ul> or next <p>.
    Returns list[str].
    """
    h = soup.find(lambda tag: tag.name == "h3" and heading_text.lower() in tag.get_text(strip=True).lower())
    if not h:
        return []
    # prefer a following UL
    ul = h.find_next_sibling(lambda t: t.name in ("ul", "ol"))
    if ul:
        return [li.get_text(strip=True) for li in ul.find_all("li")]
    # fallback to next paragraph
    p = h.find_next_sibling(lambda t: t.name == "p")
    if p:
        return [p.get_text(strip=True)]
    return []

def _resolve_screenshot_path(s):
    """
    Accepts an instance 's' (screenshot model), robustly returns absolute filesystem path
    if available else None.
    """
    # Common case: s.image is a FileField
    if hasattr(s, "image") and getattr(s, "image"):
        try:
            return s.image.path
        except Exception:
            # maybe s.image.url available but not stored locally
            pass
    # older code used s.image_path string
    image_path = getattr(s, "image_path", "") or getattr(s, "path", "")
    if not image_path:
        return None
    # strip leading slashes then check both as relative to MEDIA_ROOT and absolute
    image_path = image_path.lstrip("/")
    full1 = os.path.join(settings.MEDIA_ROOT, image_path)
    if os.path.exists(full1):
        return full1
    if os.path.isabs(image_path) and os.path.exists(image_path):
        return image_path
    # last-ditch: try the raw string as path
    if os.path.exists(image_path):
        return image_path
    return None

def _make_thumbnail(src_path, dest_dir, max_width=THUMB_MAX_WIDTH):
    os.makedirs(dest_dir, exist_ok=True)
    name = Path(src_path).stem + Path(src_path).suffix
    dest = os.path.join(dest_dir, name)
    try:
        with Image.open(src_path) as im:
            if im.width <= max_width:
                # copy original if small enough
                im.save(dest, optimize=True)
            else:
                ratio = max_width / float(im.width)
                new_h = int(im.height * ratio)
                im = im.resize((max_width, new_h), Image.LANCZOS)
                im.save(dest, optimize=True)
        return dest
    except Exception as e:
        print(f"⚠️ Thumb error for {src_path}: {e}")
        return src_path  # fallback to original

def export_meeting_summary_pdf(meeting_id):
    try:
        meeting = Meeting.objects.get(pk=meeting_id)
        # get the most recent transcript (changed from first to last)
        transcript = meeting.transcripts.order_by('created').last()

        if not transcript or not getattr(transcript, "summary", None):
            raise ValueError("No summary available to export.")

        # Parse summary HTML using robust helper
        soup = BeautifulSoup(transcript.summary, 'html.parser')
        summary_data = {
            'topics': _get_section_items(soup, "Topics Discussed"),
            'decisions': _get_section_items(soup, "Decisions Made"),
            'actions': _get_section_items(soup, "Action Items"),
            'deadlines': _get_section_items(soup, "Deadlines") or _get_section_items(soup, "Next Steps"),
            'overall': (soup.find(lambda tag: tag.name == "h3" and "Overall Summary" in tag.get_text())
                        .find_next_sibling("p").get_text(strip=True)
                        if soup.find(lambda tag: tag.name == "h3" and "Overall Summary" in tag.get_text())
                        and soup.find(lambda tag: tag.name == "h3" and "Overall Summary" in tag.get_text()).find_next_sibling("p")
                        else '')
        }

        # Get screenshots and prepare (abs) paths and timestamps (seconds since meeting start)
        screenshots = meeting.screenshots.order_by('created')
        screenshot_paths = []
        screenshot_seconds = []
        for s in screenshots:
            full_path = _resolve_screenshot_path(s)
            if not full_path:
                print(f"Warning: Screenshot record {s} has no accessible file.")
                continue

            # optional: create thumbnails to reduce PDF size
            if GENERATE_THUMBNAILS:
                thumb_dir = os.path.join(settings.MEDIA_ROOT, THUMB_DIR_NAME)
                try:
                    full_path_for_pdf = _make_thumbnail(full_path, thumb_dir)
                except Exception:
                    full_path_for_pdf = full_path
            else:
                full_path_for_pdf = full_path

            screenshot_paths.append(full_path_for_pdf)

            # compute seconds relative to meeting.created_at when possible
            try:
                delta = (s.created - meeting.created_at).total_seconds()
            except Exception:
                # fallback: seconds since epoch of screenshot (not ideal)
                try:
                    delta = s.created.timestamp()
                except Exception:
                    delta = None
            screenshot_seconds.append(delta)

        # Build sentence list to match (topics + actions are probably the most visual)
        summary_sentences = summary_data['topics'] + summary_data['actions']
        # If none, try decisions or overall fallback
        if not summary_sentences:
            summary_sentences = summary_data['decisions'] or ([summary_data['overall']] if summary_data['overall'] else [])

        # Convert segment timestamps (if available) to seconds
        # If you have TranscriptSegments with start_time (timedelta), you can build summary_seconds mapping.
        # For now, we'll attempt to use transcript.segments if available and align by index.
        summary_seconds = None
        try:
            # naive: if transcript has named segments, map sentences to segment start times
            segs = list(transcript.segments.order_by('start_time'))
            if segs and len(segs) >= len(summary_sentences):
                summary_seconds = [s.start_time.total_seconds() for s in segs[:len(summary_sentences)]]
            else:
                # fallback: use None so matcher won't use time
                summary_seconds = None
        except Exception:
            summary_seconds = None

        # Match screenshots to summary points: matcher returns {sentence: [(path, score), ...]}
        matches = match_summary_to_screenshots(
            summary_sentences,
            screenshot_paths,
            summary_timestamps=summary_seconds,
            screenshot_timestamps=screenshot_seconds,
            top_k=3,
            use_ocr=True
        )

        # Prepare pdf_data with best match above threshold
        pdf_data = []
        for section, items in [
            ('Topics Discussed', summary_data['topics']),
            ('Action Items', summary_data['actions'])
        ]:
            for item in items:
                entry = {'section': section, 'point': item, 'screenshot': None, 'score': 0.0}
                candidates = matches.get(item) or []
                # candidates is list of tuples (path, score)
                if candidates:
                    # pick highest scoring candidate above threshold
                    best = max(candidates, key=lambda x: x[1])
                    if best[1] >= MATCH_CONFIDENCE_THRESHOLD and best[0] and os.path.exists(best[0]):
                        # weasyprint wants file:// URIs or accessible path; use Path().as_uri()
                        entry['screenshot'] = Path(best[0]).as_uri()
                        entry['score'] = float(best[1])
                pdf_data.append(entry)

        # Render HTML template
        html = render_to_string('pdf_templates/meeting_summary.html', {
            'meeting': meeting,
            'pdf_data': pdf_data,
            'summary_data': summary_data,
            'created_date': timezone.localtime(meeting.created_at).strftime('%B %d, %Y %I:%M %p')
        })

        # CSS (same as before, but ensure images scale)
        css = CSS(string='''
            @page { margin: 2cm; }
            body { font-family: 'Helvetica', 'Arial', sans-serif; color: #1E3A8A; }
            h1 { color: #1E40AF; font-size: 24pt; margin-bottom: 10pt; }
            h2 { color: #1E40AF; font-size: 18pt; border-bottom: 2px solid #BFDBFE; padding-bottom: 5pt; margin-top: 20pt; }
            p, li { font-size: 12pt; line-height: 1.5; color: #1F2937; }
            .point { margin-bottom: 15pt; page-break-inside: avoid; }
            .point img { max-width: 100%; height: auto; border: 1px solid #E5E7EB; border-radius: 4px; margin-top: 10pt; }
            .no-screenshot { color: #6B7280; font-style: italic; }
            .metadata { font-size: 10pt; color: #6B7280; }
            .score { font-size: 10pt; color: #374151; opacity: 0.8; }
        ''')

        # Write PDF with metadata
        out_dir = os.path.join(settings.MEDIA_ROOT, 'summaries')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"meeting_{meeting_id}.pdf")

        HTML(string=html).write_pdf(
            out_path,
            stylesheets=[css],
            document_title=f"Meeting Summary: {meeting.name}",
            author=meeting.user.get_full_name() or meeting.user.username,
            creator="Meeting App"
        )

        return out_path

    except Meeting.DoesNotExist:
        raise ValueError("Meeting not found.")
    except Exception as e:
        raise ValueError(f"Error generating PDF: {str(e)}")
