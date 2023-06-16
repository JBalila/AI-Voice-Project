import os

# Global constants
RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'recordings')
FINAL_RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'final_recordings')
RESPONSE_FILE = os.path.join(os.getcwd(), 'static', 'response.wav')
DELAY_IN_SECONDS = 5
INITIAL_TEXT = 'hey I\'m gonna call quick, I don\'t have great signal'
INITIAL_PROMPT = 'Hey, I don\'t have good signal but I wanted to call real quick.'
FILLER_PHRASES = [
    'Hello?',
    'Hey, can you hear me?',
    'I\'m sorry?'
]