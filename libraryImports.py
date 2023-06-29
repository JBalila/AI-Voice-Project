import os
import time
import requests
import random
import concurrent.futures
from threading import current_thread
from pydub import AudioSegment
from flask import Flask, request, Response, send_file
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Gather
from elevenlabs import set_api_key, generate, save
import openai