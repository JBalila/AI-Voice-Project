from libraryImports import *
from api_keys import *
from globalConstants import *

# Global program variables
aiResponse = INITIAL_PROMPT
messageHistory = [
    {'role': 'system', 'content': 'Pretend you are calling your friend. Do not say you are an AI.'},
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
    method='POST'
)

# Returns the ElevenLabs generated response .wav file
@app.route('/get-response-wav', methods=['GET'])
def get_response_wav():
    if os.path.exists(RESPONSE_FILE):
        return send_file(RESPONSE_FILE, mimetype='audio/mpeg')
    else:
        return 'Nothing to send'

# Use <aiResponse> to say something with ElevenLabs, then listen for response
# After listening to response, send .wav to Whisper to transcribe it
# After transcribing, use ChatGPT to generate natural response
@app.route('/prompt', methods=['POST'])
def prompt():
    # Declare global vars
    global aiResponse

    # Declare local vars
    response = VoiceResponse()

    # Generate audio for <aiResponse> and play back to the recipient
    audioBytes = generate(
        text=aiResponse,
        voice='Bella',
        model='eleven_monolingual_v1'
    )
    save(audioBytes, RESPONSE_FILE)
    response.play(f'{NGROK_ADDRESS}/get-response-wav')

    # Open up a stream to listen for the response
    # Transcribe the call as it goes, stopping when there's a pausee
    gather = Gather(
        action=f'{NGROK_ADDRESS}/generate-response',
        input='speech',
        language='en-US',
        method='POST',
        profanityFilter=False,
        speechTimeout=0,
        speechModel='experimental_conversations',
        actionOnEmptyResult=True
    )
    response.append(gather)

    return Response(str(response), 200, mimetype='application/xml')

# Use ChatGPT-3.5 to generate a response
@app.route('/generate-response', methods=['POST'])
def generate_response():
    # Declare global vars
    global messageHistory
    global aiResponse

    # Declare local vars
    response = VoiceResponse()

    # Get transcription generated from <Gather>
    transcription = request.form.get('SpeechResult')
    if transcription is None:
        transcription = ''

    # Update <messageHistory> with <transcription> and create reply with ChatGPT
    messageHistory.append({'role': 'user', 'content': transcription})
    gptResponse = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=messageHistory
    )
    aiResponse = gptResponse.choices[0].message.content

    # Update the <messageHistory> with ChatGPT's response
    messageHistory.append({'role': 'assistant', 'content': aiResponse})
    transcription = ''

    response.redirect('/prompt', method='POST')
    return Response(str(response), 200, mimetype='application/xml')

# Run the app
if __name__ == "__main__":
    app.run(debug=True)