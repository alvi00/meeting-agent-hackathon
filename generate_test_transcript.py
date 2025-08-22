import os

# Sample Bangla text with normal and hateful content
sample_transcript = """
স্পিকার ১: হ্যালো এভরিওয়ান, আজকের মিটিং শুরু করছি। আমরা প্রজেক্ট ডেডলাইন নিয়ে আলোচনা করব।
স্পিকার ২: ঠিক আছে, আমার কাছে কিছু আইডিয়া আছে। গুগল ড্রাইভে নোট শেয়ার করেছি।
স্পিকার ৩: তুমি কি বোকা? এই প্রজেক্টে মেয়েরা কিছুই করতে পারে না!  # Hateful: Gender-based insult
স্পিকার ১: শান্ত হও, আমরা সবাই মিলে কাজ করব। ক্লাসের জন্য অ্যাসাইনমেন্ট জমা দিতে হবে।
স্পিকার ৪: হিন্দুদের জন্য এই কাজটা উপযুক্ত নয়, তারা অলস।  # Hateful: Religious discrimination
স্পিকার ২: চলো, ফোকাস করি। মিডটার্ম পরীক্ষার জন্য প্রস্তুতি নিতে হবে।
"""

# Save to a file in media/recordings (mimics WAV transcription output)
output_dir = "media/recordings"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "test_meeting_1_transcript.txt")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(sample_transcript)

print(f"Sample transcript saved to {output_file}")