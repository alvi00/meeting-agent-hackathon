import os
import requests
from django.core.files import File
from django.conf import settings

def generate_tts_and_save(text, lang, file_field, instance, filename):
    if not text:
        return

    try:
        # Call GPT-5 TTS API (assumed endpoint and configuration)
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-5-tts",
                "input": text,
                "voice": "alloy",  # Assuming a default voice, adjustable if needed
                "language": lang,
                "response_format": "mp3"
            },
            timeout=30,
        )
        response.raise_for_status()

        # Save the audio file
        file_path = f"media/tts/{filename}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(response.content)

        # Update Django model file field
        with open(file_path, "rb") as f:
            file_field.save(filename, File(f), save=False)

    except Exception as e:
        print(f"⚠️ Error in GPT-5 TTS generation: {e}")