#!/usr/bin/env python3
# transcribe_local_v1.py

import os
import json
from dotenv import load_dotenv
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from deepmultilingualpunctuation import PunctuationModel

# 1) Load env
load_dotenv()
KEY_PATH    = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
AUDIO_PATH  = "meet_66_20250707_013117.wav"  # your file here

# 2) Init clients
speech_client  = speech.SpeechClient.from_service_account_file(KEY_PATH)
storage_client = storage.Client.from_service_account_json(KEY_PATH)

# 3) Upload audio to GCS
print("☁ Uploading audio…")
bucket = storage_client.bucket(BUCKET_NAME)
blob = bucket.blob(os.path.basename(AUDIO_PATH))
blob.upload_from_filename(AUDIO_PATH)
gcs_uri = f"gs://{BUCKET_NAME}/{os.path.basename(AUDIO_PATH)}"
print(f"📤 Uploaded to {gcs_uri}")

# 4) Configure V1 long‑running transcription
config = speech.RecognitionConfig(
    encoding      = speech.RecognitionConfig.AudioEncoding.LINEAR16,
    language_code = "bn-BD",
    audio_channel_count = 1,
    enable_automatic_punctuation = True,
    model         = "latest_long"   # V1 supports this model too
)
audio = speech.RecognitionAudio(uri=gcs_uri)

# 5) Kick off async job
print("🗣 Starting long‑running transcription…")
operation = speech_client.long_running_recognize(config=config, audio=audio)

# 6) Wait for completion (you can tweak timeout)
response = operation.result(timeout=3600)  # 1 hour timeout

# 7) Collect all transcript chunks
raw_text = " ".join(
    result.alternatives[0].transcript
    for result in response.results
)

# 8) Punctuate & convert dot to Bangla danda
print("✨ Applying punctuation…")
punctuator = PunctuationModel()
punctuated = punctuator.restore_punctuation(raw_text)
punctuated_bangla = punctuated.replace(".", "।")

# 9) Show final
print("\n📝 Final Transcript (Bangla):\n")
print(punctuated_bangla)

# 10) Cleanup GCS & local file (optional)
blob.delete()
os.remove(AUDIO_PATH)
print("\n🧹 Cleaned up. Done!")
