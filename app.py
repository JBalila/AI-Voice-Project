import os
import time
import requests
from dotenv import load_dotenv
from pydub import AudioSegment
from flask import Flask, request, Response, send_file
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse
from elevenlabs import set_api_key, generate, save
import openai

# Import API keys from .env file
load_dotenv()

# API Keys
NGROK_ADDRESS=os.getenv('NGROK_ADDRESS')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

# Global constants
RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'recordings')
FINAL_RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'final_recordings')
RESPONSE_FILE = os.path.join(os.getcwd(), 'static', 'response.wav')
INITIAL_PROMPT = 'Hey, I don\'t have good signal but I wanted to call real quick.'
VOICES = ['Rachel', 'Domi', 'Bella', 'Antoni']

# Global program variables
context = INITIAL_PROMPT
orderNum = 1
recordingReady = False
recordingFilepath = None
messageHistory = [
    {'role': 'system', 'content': 'You are calling your friend. Do not say you are an AI.'},
    {'role': 'assistant', 'content': INITIAL_PROMPT}
]

# Create a Flask web server
app = Flask(__name__)

# Set API Keys
set_api_key(ELEVENLABS_API_KEY)     # For ElevenLabs
openai.api_key = OPENAI_API_KEY     # For OpenAI

# Create a call and connect it to the web server
# This call will be used to handle the conversation
twilioClient = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
twilioClient.calls.create(
    to='+13059342479',
    from_=TWILIO_PHONE_NUMBER,
    url=f'{NGROK_ADDRESS}/prompt',
    method='POST',
    status_callback=f'{NGROK_ADDRESS}/merge-wavs',
    status_callback_event='completed',
    status_callback_method='POST'
)

@app.route('/get-response-wav', methods=['GET'])
def get_response_wav():
    if os.path.exists(RESPONSE_FILE):
        return send_file(RESPONSE_FILE, mimetype='audio/mpeg')
    else:
        return 'Nothing to send'

# Use <context> to say something with ElevenLabs, then listen for response
# After listening to response, send .wav to Whisper to transcribe it
# After transcribing, use ChatGPT to generate natural response
@app.route('/prompt', methods=['POST'])
def prompt():
    # Declare global vars
    global orderNum
    global context
    response = VoiceResponse()

    # Generate raw audio byte-data with ElevenLabs and save to 'responses/response.wav'
    audioBytes = generate(
        text=context,
        voice='Bella',
        model='eleven_monolingual_v1'
    )
    save(audioBytes, RESPONSE_FILE)

    # Play the <responseWAV> to the recipient and record their response
    response.play(f'{NGROK_ADDRESS}/get-response-wav')
    response.record(
        timeout=2,
        playBeep=False,
        action=f'{NGROK_ADDRESS}/generate-response',
        method='POST',
        recording_status_callback=f'{NGROK_ADDRESS}/upload-recording',
        recording_status_callback_event='completed',
        recording_status_callback_method='GET'
    )

    return Response(str(response), 200, mimetype='application/xml')

# Wait until recording is ready to play
@app.route('/wait', methods=['POST'])
def wait_and_respond():
    # Declare global vars
    global recordingReady
    response = VoiceResponse()

    # Wait until we have an audiofile to play
    response.pause(length=2)
    response.redirect(f'{NGROK_ADDRESS}/generate-response', method=['POST'])

    # Reset <recordingReady> and return
    recordingReady = False
    return Response(str(response), 200, mimetype='application/xml')


# Recording has ended, add to 'recordings/' folder
@app.route('/upload-recording', methods=['GET'])
def upload_recording():
    global recordingFilepath
    global recordingReady
    global orderNum

    # Get info from request body (<RecordingUrl> and <CallSid>)
    args = request.args.to_dict()
    recordingURL = str(args['RecordingUrl'])
    callSID = str(args['CallSid'])
    filename = f'{orderNum}_{callSID}.wav'
    recordingFilepath = os.path.join(RECORDINGS_FOLDER, filename)

    # Download URL and write to 'recordings/' folder
    wavFile = requests.get(recordingURL, allow_redirects=True)
    open(recordingFilepath, 'wb').write(wavFile.content)

    orderNum += 1
    recordingReady = True
    return 'Recording finished'

# Use Whisper to transcribe the recording and ChatGPT-3.5 to generate a response
@app.route('/generate-response', methods=['POST'])
def generate_response():
    # Declare global vars
    global recordingFilepath
    global messageHistory
    global context
    response = VoiceResponse()

    # Transcribe mp3 file with OpenAI's Whisper
    try:
        transcription = openai.Audio.transcribe('whisper-1', open(recordingFilepath, 'rb')).text
        print('Transcription: ' + transcription)
    except:
        response.pause(length=1)
        response.redirect(f'{NGROK_ADDRESS}/generate-response')
    else:
        # Update the <messageHistory> with the user's response
        messageHistory.append(
            {'role': 'user', 'content': transcription}
        )

        # Use <transcription> to update <context>
        gptResponse = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=messageHistory
        )
        context = gptResponse.choices[0].message.content
        print('Context: ' + context)

        # Update the <messageHistory> with ChatGPT's response
        messageHistory.append(
            {'role': 'assistant', 'content': context}
        )

        # Use the updated <context> to respond to the recipient
        response.redirect('/prompt', methods=['POST'])
    
    return Response(str(response), 200, mimetype='application/xml')

# Call has ended, merge .wav files into one .wav file
@app.route('/merge-wavs', methods=['POST'])
def merge_wavs():
    # Get list of all wavs
    wavList = os.listdir(RECORDINGS_FOLDER)
    wavList.sort(key = lambda wavFile: int(wavFile.split('_')[0]))

    # Nothing in 'recordings/' folder
    if (len(wavList) == 0):
        return 'Nothing to merge'

    # Concatenate wav snippets into a single wav
    fullWAV = AudioSegment.empty()
    for wav in wavList:
        wavPath = os.path.join(RECORDINGS_FOLDER, wav)
        fullWAV += AudioSegment.from_file(wavPath, format='wav')

    # Save <fullWav> into 'final_recordings/' folder
    fullWAVName = wavList[0].split('_')[1]
    fullWAV.export(os.path.join(FINAL_RECORDINGS_FOLDER, fullWAVName), format='wav')

    # Remove wav files from 'recordings/ folder
    for wav in wavList:
        os.remove(os.path.join(RECORDINGS_FOLDER, wav))
    
    # Remove response.wav from 'static/' folder
    os.remove(RESPONSE_FILE)

    return 'Done merging wavs'

# Run the app
if __name__ == "__main__":
    app.run(debug=True)