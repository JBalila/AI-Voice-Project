from libraryImports import *
from api_keys import *
from globalConstants import *

# Create a Flask web server
app = Flask(__name__)

# Set API Keys
set_api_key(ELEVENLABS_API_KEY)     # For ElevenLabs
openai.api_key = OPENAI_API_KEY     # For OpenAI
twilioClient = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Global program variables
aiResponses = dict()
messageHistories = dict()

# Texts <number> with a message, waits a couple of seconds, and then calls <number>
def messageThenCall(number):
    # Give this thread its own entry in <aiResponses> and <messageHistories>
    aiResponses[number] = INITIAL_PROMPT
    messageHistories[number] = INITIAL_HISTORY

    # Make the text
    if SHOULD_SEND_TEXT:
        twilioClient.messages.create(
            to=number,
            from_=TWILIO_PHONE_NUMBER,
            body=INITIAL_TEXT
        )
    
        # Wait a little bit for the text message to register
        time.sleep(DELAY_IN_SECONDS)

    # Make the call
    twilioClient.calls.create(
        to=number,
        from_=TWILIO_PHONE_NUMBER,
        url=f'{NGROK_ADDRESS}/prompt',
        method='POST',
        status_callback=f'{NGROK_ADDRESS}/cleanup-memory',
        status_callback_method='POST',
        status_callback_event='completed'
    )

###################### MAIN FUNCTION #######################
# Set stability settings for voice
requests.post(
    f'https://api.elevenlabs.io/v1/voices/{VOICE}/settings/edit',
    params={
        'xi-api-key': ELEVENLABS_API_KEY
    },
    data={
        'stability': STABILITY,
        'similarity_boost': SIMILARITY_BOOST
    }
)

# Use multiple threads to message then call numbers
# Uses dictionaries with the callee's number as a key to access that thread's info
with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(messageThenCall, PHONE_NUMBERS)

############################################################

########################## ROUTES ##########################
# Returns the ElevenLabs generated audio of the ChatGPT response
@app.route('/get-response-wav', methods=['GET'])
def get_response_wav():
    # GET method needs params to be URL encoded, and '+' can't be in the URL so we add it here
    number = '+' + request.args.get('num')

    responseFile = os.path.join(RESPONSE_FOLDER, f'response_{number}.wav')
    if os.path.exists(responseFile):
        return send_file(responseFile, mimetype='audio/mpeg')
    else:
        return 'Nothing to send'

# Use <aiResponse> to say something with ElevenLabs, then listen for response
# After listening to response, send .wav to Whisper to transcribe it
# After transcribing, use ChatGPT to generate natural response
@app.route('/prompt', methods=['POST'])
def prompt():
    # Declare global vars
    global aiResponses

    # Declare local vars
    response = VoiceResponse()
    number = request.form.get('To')

    # Generate audio for <aiResponse> and play back to the recipient
    audioBytes = generate(
        text=aiResponses[number],
        voice=VOICE,
        model='eleven_monolingual_v1'
    )
    responseFile = os.path.join(RESPONSE_FOLDER, f'response_{number}.wav')
    save(audioBytes, responseFile)
    response.play(f'{NGROK_ADDRESS}/get-response-wav?num={number.replace("+","")}')

    # Open up a stream to listen for the response
    # Transcribe the call as it goes, stopping when there's a pause
    gather = Gather(
        action=f'{NGROK_ADDRESS}/generate-response',
        input='speech',
        language='en-US',
        method='POST',
        profanityFilter=False,
        timeout=1,
        speechTimeout='auto',
        speechModel='experimental_conversations',
        actionOnEmptyResult=True
    )
    response.append(gather)

    return Response(str(response), 200, mimetype='application/xml')

# Use ChatGPT-3.5 to generate a response
@app.route('/generate-response', methods=['POST'])
def generate_response():
    # Declare global vars
    global messageHistories
    global aiResponses

    # Declare local vars
    response = VoiceResponse()
    number = request.form.get('To')

    # Get transcription generated from <Gather>
    transcription = request.form.get('SpeechResult')
    if transcription is None:
        transcription = ''

    # Update <messageHistory> with <transcription> and create reply with ChatGPT
    messageHistories[number].append({'role': 'user', 'content': transcription})
    gptResponse = openai.ChatCompletion.create(
        model='gpt-3.5-turbo-16k',
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=messageHistories[number]
    )
    aiResponses[number] = gptResponse.choices[0].message.content

    # Update the <messageHistory> with ChatGPT's response
    messageHistories[number].append({'role': 'assistant', 'content': aiResponses[number]})
    transcription = ''

    response.redirect('/prompt', method='POST')
    return Response(str(response), 200, mimetype='application/xml')

# Clean up any memory used during this call
@app.route('/cleanup-memory', methods=['POST'])
def cleanup_memory():
    # Declare global variables
    global messageHistories
    global aiResponses

    # Declare local variables
    number = request.form.get('To')

    # Cleanup key in <messageHistories> and <aiResponses>
    messageHistories.pop(number)
    aiResponses.pop(number)

    # Remove 'response.wav' file from 'static/' folder
    responseFile = os.path.join(RESPONSE_FOLDER, f'response_{number}.wav')
    if (os.path.exists(responseFile)):
        os.remove(responseFile)
    
    return 'Done cleaning memory...'

############################################################

# Run the app
if __name__ == "__main__":
    app.run(debug=True)