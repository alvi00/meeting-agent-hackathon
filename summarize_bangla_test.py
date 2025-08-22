import os
import requests
from google.cloud import translate_v2 as translate
from dotenv import load_dotenv

load_dotenv()

# Sample Bangla input
bangla_text = """
হ্যালো এভরি ওয়ান। তোমাদের সবাইকে আমি বলতে চাই, যে তোমরা তোমাদের কুইজে অনেক ভালো রেজাল্ট করছো, 
তোমরা সবাই বিশ্বের বেশি পাইছো, সেটা অনেক ভালো। আমি আজকের মিটিংয়ে বলতে চাই, তোমাদের সবাইকে 
আমি অনেক ভালো রেজাল্ট করার জন্য শুভেচ্ছা জানাবো। আর তোমরা অ্যাটেনডেন্সের পরে চলে যেও, ঠিক আছে, 
ধন্যবাদ সবাইকে।
"""

# Step 1: Translate Bangla → English
def translate_bangla_to_english(text):
    client = translate.Client()
    result = client.translate(
        text,
        source_language="bn",
        target_language="en",
        format_="text"
    )
    return result["translatedText"]

# Step 2: Summarize in English using Groq
def summarize_english_text(text):
    prompt = f"""
You are an AI meeting assistant. Please read the following meeting transcript and produce a concise, action-oriented summary. Your summary should include:

1. Main topics discussed  
2. Key decisions made  
3. Action items (who is responsible for what)  
4. Deadlines or next steps  

Transcript:
{text}
""".strip()

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
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
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

# Step 3: Translate English summary → Bangla
def translate_english_to_bangla(text):
    client = translate.Client()
    result = client.translate(
        text,
        source_language="en",
        target_language="bn",
        format_="text"
    )
    return result["translatedText"]

# 🔁 Run full flow
if __name__ == "__main__":
    print("🔄 Translating Bangla to English...")
    english_text = translate_bangla_to_english(bangla_text)
    print("\n📜 Translated Text:\n", english_text)

    print("\n🧠 Summarizing...")
    summary_en = summarize_english_text(english_text)
    print("\n✅ Summary in English:\n", summary_en)

    print("\n🌐 Translating Summary Back to Bangla...")
    summary_bn = translate_english_to_bangla(summary_en)
    print("\n🎯 Final Summary in Bangla:\n", summary_bn)
