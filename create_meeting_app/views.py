from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from .models import Meeting
from .forms import CreateMeetingForm, JoinMeetingForm
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required
from google.cloud import translate_v2 as translate
from create_meeting_app.utils.tts import generate_tts_and_save
from bs4 import BeautifulSoup
from .models import Transcript


import json
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.html import escape


def dashboard(request):
    meetings = Meeting.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard.html', {'meetings': meetings})

def create_meeting(request):
    if request.method == 'POST':
        form = CreateMeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.user = request.user
            meeting.save()
            messages.success(request, 'Meeting created successfully!')
            return redirect('dashboard')
        messages.error(request, 'Error creating meeting. Please check the form.')
    return redirect('dashboard')

def join_meeting(request):
    if request.method == 'POST':
        form = JoinMeetingForm(request.POST)
        if form.is_valid():
            meeting = get_object_or_404(Meeting, pk=form.cleaned_data['meeting_id'], user=request.user)
            meeting.meeting_link = form.cleaned_data['meeting_link']
            meeting.join_time = form.cleaned_data['join_time']
            meeting.joined = False
            meeting.save()
            messages.success(request, 'Meeting details saved! Bot will join on time.')
            return redirect('meeting_page', meeting_id=meeting.pk)
        messages.error(request, 'Error saving meeting details.')
    return redirect('dashboard')

def meeting_page(request, meeting_id):
    meeting = get_object_or_404(Meeting, pk=meeting_id)

    segments = []
    for transcript in meeting.transcripts.order_by('created'):
        if transcript.text:
            blocks = transcript.text.split('। ')
            for block in blocks:
                if block.strip():
                    if ': ' in block:
                        speaker, text = block.split(': ', 1)
                    else:
                        speaker, text = None, block
                    segments.append({
                        'speaker': speaker,
                        'text': text,
                        'created': transcript.created,
                    })

    hateful_segments = []
    for transcript in meeting.transcripts.order_by('created'):
        if transcript.hateful_text:
            blocks = transcript.hateful_text.split('। ')  # Split by sentence
            for block in blocks:
                if block.strip():
                    if ': ' in block:
                        speaker, text = block.split(': ', 1)
                    else:
                        speaker, text = None, block
                    hateful_segments.append({
                        'speaker': speaker,
                        'text': text,
                        'created': transcript.created,
                    })

    screenshots = meeting.screenshots.order_by('created')

    return render(request, 'meeting_detail.html', {
        'meeting': meeting,
        'segments': segments,
        'hateful_segments': hateful_segments,
        'screenshots': screenshots,
    })

@require_POST
def delete_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, user=request.user)
    meeting.delete()
    return JsonResponse({'status': 'success'})

@csrf_exempt
def transcribe_meeting_view(request, meeting_id):
    if request.method == 'POST':
        call_command('transcribe_meeting', str(meeting_id))
        return redirect('meeting_page', meeting_id=meeting_id)
    return HttpResponse("Invalid request", status=400)

@csrf_exempt  # MODIFIED: Added for testing
@login_required
@require_POST
def summarize_transcript(request, transcript_id):
    print(f"Request for summarize_transcript, transcript_id: {transcript_id}")  # NEW: Debug
    try:
        t = get_object_or_404(Transcript, pk=transcript_id, meeting__user=request.user)
        print("Transcript fetched successfully")  # NEW

        # Translate to English if needed
        translated_text = t.translated_text
        if not translated_text:
            client = translate.Client()
            result = client.translate(
                t.text,  # Clean text only
                source_language="bn",
                target_language="en",
                format_="text"
            )
            translated_text = result["translatedText"]
            t.translated_text = translated_text
            t.save(update_fields=["translated_text"])
            print("Translation successful")  # NEW

        # Build summarization prompt
        prompt = f"""
You are a highly intelligent AI assistant designed to take unstructured meeting transcripts and produce clear, detailed, and professional summaries.

Your summary must be helpful to someone who didn’t attend the meeting.

Please generate a structured summary **in valid HTML format** using the following structure and tags:

<h3>📝 Topics Discussed</h3>
<ul>
  <li>...</li>
</ul>

<h3>✅ Decisions Made</h3>
<ul>
  <li>...</li>
</ul>

<h3>📌 Action Items</h3>
<ul>
  <li>...</li>
</ul>

<h3>⏳ Deadlines / Next Steps</h3>
<ul>
  <li>...</li>
</ul>

<h3>🧠 Overall Summary</h3>
<p>...</p>

Make sure:
- The HTML is clean and well-formed.
- Don’t use Markdown.
- Use <ul> and <li> tags for lists.
- No <style> tags or inline CSS.

Transcript:
{translated_text}
""".strip()

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 256,
            },
            timeout=30,
        )
        resp.raise_for_status()
        summary = resp.json()["choices"][0]["message"]["content"].strip()
        print("Summary generated successfully")  # NEW

        t.summary = summary
        t.save(update_fields=["summary"])

        plain_summary = BeautifulSoup(t.summary, "html.parser").get_text(separator="\n")
        generate_tts_and_save(
            plain_summary,
            lang='bn',  # Changed to Bangla for consistency
            file_field=t.summary_audio,
            instance=t,
            filename=f"summary_{t.id}.mp3"
        )
        t.save(update_fields=["summary_audio"])

        return JsonResponse({
            "success": True,
            "summary": summary,
            "summary_audio_url": t.summary_audio.url
        })

    except requests.exceptions.HTTPError as e:
        error_text = str(e)
        print(f"API error: {error_text}")  # NEW
        return JsonResponse({"success": False, "error": error_text}, status=500)
    except Exception as e:
        error_text = str(e)
        print(f"Unexpected error: {error_text}")  # NEW
        return JsonResponse({"success": False, "error": error_text}, status=500)

from create_meeting_app.utils.export_pdf import export_meeting_summary_pdf
from django.http import FileResponse, Http404

@login_required
def download_summary_pdf(request, meeting_id):
    try:
        path = export_meeting_summary_pdf(meeting_id)
        return FileResponse(open(path, 'rb'),
                           as_attachment=True,
                           filename=f"meeting_{meeting_id}.pdf")
    except ValueError as e:
        return HttpResponseBadRequest(f"Cannot generate PDF: {e}")
    except Meeting.DoesNotExist:
        raise Http404("Meeting not found.")
    except FileNotFoundError:
        raise Http404("PDF file not found.")
    except Exception as e:
        return HttpResponseBadRequest(f"Unexpected error: {e}")
    

# inside views.py: paste this view
@login_required
@require_POST
def ask_meeting_question(request, meeting_id):
    """
    POST JSON: { "question": "..." }
    Returns JSON: { "success": True, "answer": "...", "mode": "llm"|"extractive" }
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        question = (payload.get("question") or "").strip()
        if not question:
            return JsonResponse({"success": False, "error": "Missing question"}, status=400)

        meeting = get_object_or_404(Meeting, pk=meeting_id, user=request.user)

        # Gather transcript texts (prefer translated_text if available)
        texts = []
        for t in meeting.transcripts.order_by('created'):
            if getattr(t, "translated_text", None):
                texts.append(t.translated_text)
            elif getattr(t, "text", None):
                texts.append(t.text)
        full_text = "\n\n".join([x for x in texts if x])

        if not full_text:
            return JsonResponse({"success": False, "error": "No transcript available for this meeting."}, status=400)

        # Use helper to retrieve top chunks
        from .utils.qa_helper import retrieve_top_chunks, call_groq_chat

        top_chunks, scores = retrieve_top_chunks(full_text, question, top_k=4)
        context = "\n\n".join(top_chunks) if top_chunks else full_text[:4000]

        # If Groq key is configured, form a prompt and call LLM; else fallback to extractive.
        answer = None
        if getattr(settings, "GROQ_API_KEY", None):
            prompt = f"""
SYSTEM:
You are a precise assistant. Your ONLY knowledge is the transcript chunks provided below.
- Never make up facts outside the transcript.
- If the answer is not in the transcript, reply exactly: "No direct answer found in the transcript."
- Be concise (2–4 sentences max).
- Prefer quoting phrases directly from the transcript when possible.

CONTEXT:
{context}

USER QUESTION:
{question}

ASSISTANT ANSWER:
"""

            llm_resp = call_groq_chat(prompt)
            if llm_resp:
                answer = llm_resp

        if not answer:
            # extractive fallback: return the top chunks as quoted context + small synthesized header
            header = "Extractive answer (no LLM or LLM failed). Relevant transcript excerpts follow:\n\n"
            quoted = "\n\n---\n\n".join([f"{escape(c)}" for c in top_chunks]) if top_chunks else escape(full_text[:4000])
            answer = header + quoted
            mode = "extractive"
        else:
            mode = "llm"

        return JsonResponse({"success": True, "answer": answer, "mode": mode})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)