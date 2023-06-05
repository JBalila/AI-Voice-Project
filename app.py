import os
import requests
from dotenv import load_dotenv
from pydub import AudioSegment
from flask import Flask, request, Response
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse
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

# Global variables
RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'recordings')
FINAL_RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'final_recordings')
RESPONSE_FOLDER = os.path.join(os.getcwd(), 'responses')
context = 'Hey, how are you?'
orderNum = 1
recordingReady = False
recordingFilepath = None


# Create a Flask web server
app = Flask(__name__)

# Configure OpenAI parameters
openai.api_key = OPENAI_API_KEY

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

# Use <context> to say something with ElevenLabs, then listen for response
# After listening to response, send .wav to Whisper to transcribe it
# After transcribing, use ChatGPT to generate natural response
@app.route('/prompt', methods=['POST'])
def prompt():
    # Declare global vars
    global orderNum
    global context
    response = VoiceResponse()

    # Create .wav file of <context> with ElevenLabs, store in 'responses/' folder

    # Play the <responseWAV> to the recipient and record their response
    response.say(context)
    response.record(
        timeout=2,
        playBeep=False,
        action=f'{NGROK_ADDRESS}/wait',
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
    response.pause(length=3)
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
    global context
    global recordingFilepath
    response = VoiceResponse()

    # Transcribe mp3 file with OpenAI's Whisper
    transcription = openai.Audio.transcribe('whisper-1', open(recordingFilepath, 'rb')).text
    print('Transcription: ' + transcription)

    # Use <transcription> to update <context> and play it back to recipient
    gptResponse = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': 'You are calling your friend to say hello. Pretend you are not an AI.'},
            {'role': 'user', 'content': transcription}
        ]
    )
    context = gptResponse.choices[0].message.content
    print('Context: ' + context)

    # TODO: Remove after testing '/merge-wavs' endpoint
    context = 'Test'

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
        return

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

    return 'Done merging wavs'

# Run the app
if __name__ == "__main__":
    app.run(debug=True)