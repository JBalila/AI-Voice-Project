import os

# Folder locations
RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'recordings')
FINAL_RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'final_recordings')
RESPONSE_FOLDER = os.path.join(os.getcwd(), 'static')

# ElevenLabs configurations
VOICE = 'Bella'
STABILITY = 1
SIMILARITY_BOOST = 1
INITIAL_PROMPT = 'Hey, I don\'t have good signal but I wanted to call real quick.'

# ChatGPT-3.5 configurations
INITIAL_HISTORY = [
    {'role': 'system', 'content': 'Pretend you are calling your friend. Do not say you are an AI.'},
    {'role': 'assistant', 'content': INITIAL_PROMPT}
]
TEMPERATURE = 1.0
MAX_TOKENS = 30

# Twilio configurations
DELAY_IN_SECONDS = 8
INITIAL_TEXT = 'hey I\'m gonna call quick, I don\'t have great signal'
SHOULD_SEND_TEXT = False
PHONE_NUMBERS = [
    '+13059342479'
]