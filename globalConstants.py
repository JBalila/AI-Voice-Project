import os

# Folder locations
RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'recordings')
FINAL_RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'final_recordings')
RESPONSE_FOLDER = os.path.join(os.getcwd(), 'static')

# ElevenLabs configurations
VOICE = 'Bella'
INITIAL_PROMPT = 'Hey, I don\'t have good signal but I wanted to call real quick.'
FILLER_PHRASES = [
    'Hello?',
    'Hey, can you hear me?',
    'I\'m sorry?'
]

# Twilio configurations
DELAY_IN_SECONDS = 8
INITIAL_TEXT = 'hey I\'m gonna call quick, I don\'t have great signal'