from django.core.management.base import BaseCommand
from create_meeting_app.models import Meeting, Transcript, TranscriptSegment
import os
import datetime
from deepmultilingualpunctuation import PunctuationModel
from create_meeting_app.utils.tts import generate_tts_and_save
import requests
from django.conf import settings

# NEW: Import for Bangla sentence splitting
try:
    from bnlp import NLTKTokenizer
    bnlp_available = True
except ImportError:
    bnlp_available = False

ENGLISH_WORDS = {
    
}

def restore_english_words(text):
    for bn, en in ENGLISH_WORDS.items():
        text = text.replace(bn, en)
    return text

def get_seconds(d):
    if hasattr(d, 'seconds') and hasattr(d, 'microseconds'):
        return d.seconds + d.microseconds / 1e6
    return float(d)

def detect_hate_speech(text):
    prompt = f"""
You are an expert at detecting hate speech in Bangla text.

Hate speech is language that expresses discrimination, hostility, or violence against individuals or groups based on attributes like race, religion, ethnicity, nationality, gender, sexual orientation, political affiliation, origin, body shaming, or disability. Key indicators include dehumanizing language, calls for violence, discriminatory slurs, stereotyping, promoting supremacy, or personal offenses. Consider cultural context, dialects, and code-mixing in Bangla.

Classify the following Bangla text as hate speech.
Respond only with 'hate' or 'safe'.

Text: {text}
""".strip()

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 10,
            },
            timeout=30,
        )
        resp.raise_for_status()
        classification = resp.json()["choices"][0]["message"]["content"].strip().lower()
        return 'hate' in classification
    except Exception as e:
        print(f"⚠️ Error in hate detection: {e}")
        return False  # Assume safe if error

def transcribe_audio_with_gpt5(audio_path):
    """Transcribe audio using GPT-5 API (assumed endpoint and configuration)."""
    try:
        with open(audio_path, 'rb') as audio_file:
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "multipart/form-data",
                },
                files={
                    "file": audio_file,
                },
                data={
                    "model": "gpt-5",
                    "language": "bn",
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                },
                timeout=600,
            )
            resp.raise_for_status()
            result = resp.json()
            return result
    except Exception as e:
        raise Exception(f"⚠️ Error in GPT-5 transcription: {e}")

class Command(BaseCommand):
    help = "Transcribe WAV files in Bangla with smart punctuation & pause-based segments using GPT-5"

    def add_arguments(self, parser):
        parser.add_argument('meeting_id', type=int)

    def handle(self, *args, **options):
        mid = options['meeting_id']
        meeting = Meeting.objects.filter(id=mid).first()
        if not meeting:
            return self.stderr.write("❌ Meeting not found.")

        recordings = sorted(f for f in os.listdir("media/recordings")
                           if f.endswith('.wav') and f"_{mid}_" in f)
        if not recordings:
            return self.stdout.write("📭 No recordings found.")

        punctuator = PunctuationModel()

        for wav in recordings:
            path = os.path.join("media/recordings", wav)
            self.stdout.write(f"🗣 Transcribing {wav}…")

            try:
                # Transcribe with GPT-5
                transcription = transcribe_audio_with_gpt5(path)

                # Build transcript
                raw = transcription.get('text', '')
                punct = punctuator.restore_punctuation(raw).replace('.', '।')
                final_text = restore_english_words(punct)

                # Filter for hate speech (sentence-level)
                if bnlp_available:
                    bnltk = NLTKTokenizer()
                    sentences = bnltk.sentence_tokenization(final_text)
                else:
                    # Fallback: Split on Bangla full stop
                    sentences = [s.strip() for s in final_text.split('।') if s.strip()]

                clean_sentences = []
                hateful_sentences = []
                for sentence in sentences:
                    if ': ' in sentence:
                        speaker, text = sentence.split(': ', 1)
                        if detect_hate_speech(text):
                            hateful_sentences.append(sentence)
                        else:
                            clean_sentences.append(sentence)
                    else:
                        if detect_hate_speech(sentence):
                            hateful_sentences.append(sentence)
                        else:
                            clean_sentences.append(sentence)

                transcript = Transcript.objects.create(
                    meeting=meeting,
                    raw_text=raw,
                    text='। '.join(clean_sentences),  # Join with Bangla full stop
                    hateful_text='। '.join(hateful_sentences) if hateful_sentences else ''
                )

                # Generate TTS for cleaned text only
                if transcript.text:
                    generate_tts_and_save(transcript.text, 'bn', transcript.transcript_audio, transcript, f"transcript_{mid}.mp3")

                # If summary already exists, generate summary audio
                if transcript.summary:
                    generate_tts_and_save(transcript.summary, 'bn', transcript.summary_audio, transcript, f"summary_{mid}.mp3")

                transcript.save()

                # Segment by pauses
                words = transcription.get('words', [])
                buffer = ""
                start_time = None
                prev_end_sec = None

                for idx, word_info in enumerate(words):
                    sec_start = word_info.get('start_time', 0.0)
                    sec_end = word_info.get('end_time', 0.0)
                    word = word_info.get('word', '')

                    if start_time is None:
                        start_time = sec_start
                    buffer += word + " "

                    pause = sec_start - prev_end_sec if prev_end_sec is not None else 0
                    end_of_audio = (idx == len(words) - 1)

                    if pause > 0.8 or end_of_audio:
                        tot_start = start_time
                        tot_end = sec_end

                        start_td = datetime.timedelta(seconds=tot_start)
                        end_td = datetime.timedelta(seconds=tot_end)

                        TranscriptSegment.objects.create(
                            transcript=transcript,
                            text=buffer.strip(),
                            start_time=start_td,
                            end_time=end_td
                        )
                        buffer = ""
                        start_time = None

                    prev_end_sec = sec_end

                # Cleanup
                os.remove(path)
                self.stdout.write("✅ Transcription & segmentation complete.")

            except Exception as e:
                self.stderr.write(f"⚠️ Error: {e}")