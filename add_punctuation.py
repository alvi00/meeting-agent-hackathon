from deepmultilingualpunctuation import PunctuationModel

model = PunctuationModel()
text = "মাই নেম ইজ আহমেদ ফাহিম হ্যালো এভরিওয়া টুডে ওয়েকাম অল অফ ইউ টু মাই ক্লাস আজকে আমি তোমাদের শিখাবো তোমাদের সবাইকে আমিএফ মুভিটি দেখতে বলবো কারন মুভিটা অনেক ভালো তোমাদের"
result = model.restore_punctuation(text)

# Replace '.' with '।'
result_with_bangla_fullstop = result.replace('.', '।')

print(result_with_bangla_fullstop)