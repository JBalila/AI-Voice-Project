import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse

# Import API keys from .env file
load_dotenv()

# API Keys
NGROK_ADDRESS=os.getenv('NGROK_ADDRESS')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
WHISPER_API_KEY = os.getenv('WHISPER_API_KEY')
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

# Flask app constants
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'recordings')

# Create a Flask web server
app = Flask(__name__)

# Create a call and connect it to the web server
# This call will be used to handle the conversation
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
twilio_client.calls.create(
    to='+13059342479',
    from_=TWILIO_PHONE_NUMBER,
    url=NGROK_ADDRESS,
    method='POST',
    record=True,
    recording_status_callback=f'{NGROK_ADDRESS}/recording-finished',
    recording_status_callback_event='completed',
    recording_status_callback_method='GET'
)

# Call is connected, wait a little bit and then say 'Hello'
@app.route('/', methods=['POST'])
def talk():
    response = VoiceResponse()
    response.say('Hello!')
    response.pause(length=2)
    print(response)

    return Response(str(response), 200, mimetype='application/xml')

# Call has ended, print response data
@app.route('/recording-finished', methods=['GET'])
def on_call_ended():
    # Get info from request body (<RecordingUrl> and <RecordingSid>)
    args = request.args.to_dict()
    recordingURL = str(args['RecordingUrl'])
    filename = str(args['CallSid']) + '.mp3'
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Download URL and write to 'Recordings/' folder
    mp3_file = requests.get(recordingURL, allow_redirects=True)
    open(filepath, 'wb').write(mp3_file.content)

    return 'Recording finished'

# # Global variables
# call_sid = None
# context = "Hi there it's me."

# # Define a function to handle incoming requests.
# # This function is called when a request is received from the web server.
# @app.route('/assistant', methods=['POST'])
# def assistant():
#     global context
#     user_input = request.values.get('SpeechResult')

#     # Replace this with a real call to the OpenAI API
#     # This call generates a response from OpenAI's ChatGPT
#     response = openai_api_call(prompt)
#     chatgpt_response = response

#     # Send the response to Eleven Labs.
#     # This service synthesizes the response into audio.
#     data = {"input": chatgpt_response}
#     response = requests.post(
#         "https://api.elevenlabs.ai/v1/synthesize",
#         headers={"Authorization": f"Bearer {ELEVENLABS_API_KEY}"},
#         data=data
#     )
#     audio_data = response.content

#     # Create a TwiML response.
#     # This response plays the synthesized audio.
#     twiml = VoiceResponse()
#     twiml.play(audio_data)

#     # Update the context.
#     # This variable is used to store the conversation history.
#     context += f"\nHuman: {user_input}\nClaude: {chatgpt_response}"

#     # Return the TwiML response.
#     return Response(str(twiml), mimetype='text/xml')

# # Define a function to call the OpenAI API
# # This function generates a response from OpenAI's ChatGPT
# def openai_api_call(prompt):
#     # This is a placeholder function, replace with a real call to the OpenAI API
#     response = requests.post(
#         "https://api.openai.com/v1/engines/davinci/completions",
#         headers={
#             "Authorization": f"Bearer {OPENAI_API_KEY}",
#             "Content-Type": "application/x-www-form-urlencoded",
#         },
#         data={
#             "prompt": prompt,
#             "temperature": 0.7,
#             "max_tokens": 100,
#             "n": 1,
#             "no_repeat_ngram_size": 3,
#             "early_stopping": True,
#         },
#     )
#     return response.json()["choices"][0]["text"]

# Run the app
if __name__ == "__main__":
    app.run(debug=True)