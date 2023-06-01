import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse

# Import API keys from .env file
load_dotenv()

# API Keys
WHISPER_API_KEY = os.getenv('WHISPER_API_KEY')
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

# Create clients
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Create a Flask web server
app = Flask(__name__)

call_sid = None
context = "Hi there it's me."

def on_call_connected(call_sid):
    # This is where you'd define what happens when a call is connected.
    # The specifics would depend on your application's requirements.
    # For example, you could play a welcome message or start a conversation.
    pass

# Create a call and connect it to the web server.
# This call will be used to handle the conversation.
twilio_client.calls.create(
    to='+13059953569',
    from_='+17867417334',
    url='http://example.com/assistant',
    method='POST',
    status_callback=on_call_connected
)

# Define a function to handle incoming requests.
# This function is called when a request is received from the web server.
@app.route('/assistant', methods=['POST'])
def assistant():
    global context
    user_input = request.values.get('SpeechResult')

    # Replace this with a real call to the OpenAI API.
    # This call generates a response from OpenAI's ChatGPT.
    response = openai_api_call(prompt)
    chatgpt_response = response

    # Send the response to Eleven Labs.
    # This service synthesizes the response into audio.
    data = {"input": chatgpt_response}
    response = requests.post(
        "https://api.elevenlabs.ai/v1/synthesize",
        headers={"Authorization": f"Bearer {ELEVENLABS_API_KEY}"},
        data=data
    )
    audio_data = response.content

    # Create a TwiML response.
    # This response plays the synthesized audio.
    twiml = VoiceResponse()
    twiml.play(audio_data)

    # Update the context.
    # This variable is used to store the conversation history.
    context += f"\nHuman: {user_input}\nClaude: {chatgpt_response}"

    # Return the TwiML response.
    return Response(str(twiml), mimetype='text/xml')

# Define a function to call the OpenAI API.
# This function generates a response from OpenAI's ChatGPT.
def openai_api_call(prompt):
    # This is a placeholder function, replace with a real call to the OpenAI API
    response = requests.post(
        "https://api.openai.com/v1/engines/davinci/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "prompt": prompt,
            "temperature": 0.7,
            "max_tokens": 100,
            "n": 1,
            "no_repeat_ngram_size": 3,
            "early_stopping": True,
        },
    )
    return response.json()["choices"][0]["text"]

# Run the app.
if __name__ == "__main__":
    app.run(debug=True)