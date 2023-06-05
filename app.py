import os
import requests
from dotenv import load_dotenv
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

# Global variables
RECORDINGS_FOLDER = os.path.join(os.getcwd(), 'recordings')
RESPONSE_FOLDER = os.path.join(os.getcwd(), 'responses')
context = 'Hey, how are you?'
orderNum = 1
recordingReady = False
recordingFilepath = None
responseReady = False
responseFilepath = None


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
    status_callback=f'{NGROK_ADDRESS}/merge-mp3s',
    status_callback_event='completed',
    status_callback_method='POST'
)

# Call is connected, begin conversation
@app.route('/prompt', methods=['POST'])
def prompt():
    # Declare global vars
    global orderNum
    global context
    response = VoiceResponse()
    
    # Use <context> to say something with ElevenLabs, then listen for response
    # After listening to response, send .mp3 to Whisper to transcribe it
    # After transcribing, use ChatGPT to generate natural response
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
    global responseFilepath
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
    filename = f'{orderNum}_{callSID}.mp3'
    recordingFilepath = os.path.join(RECORDINGS_FOLDER, filename)

    # Download URL and write to 'recordings/' folder
    mp3File = requests.get(recordingURL, allow_redirects=True)
    open(recordingFilepath, 'wb').write(mp3File.content)

    orderNum += 1
    recordingReady = True
    return 'Recording finished'

@app.route('/generate-response', methods=['POST'])
def generate_response():
    # Declare global vars
    global context
    global recordingFilepath
    global responseReady
    global responseFilepath
    response = VoiceResponse()

    # Transcribe mp3 file with OpenAI's Whisper
    transcription = openai.Audio.transcribe('whisper-1', open(recordingFilepath, 'rb')).text
    print('Transcription: ' + transcription)

    # Use <transcription> to update <context> and play it back to recipient
    gptResponse = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': 'You are calling your friend to say hello.'},
            {'role': 'user', 'content': transcription}
        ]
    )
    context = gptResponse.choices[0].message.content
    print('Context: ' + context)

    # Use the updated <context> to respond to the recipient
    response.redirect('/prompt', methods=['POST'])
    return Response(str(response), 200, mimetype='application/xml')

# Call has ended, merge .mp3 files into one .mp3 file
@app.route('/merge-mp3s', methods=['POST'])
def merge_mp3s():
    return 'Done merging mp3s'

# Run the app
if __name__ == "__main__":
    app.run(debug=True)