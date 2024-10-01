import pyaudio
import wave
import requests
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Set your OpenAI API key from the .env file
openai_api_key = os.getenv('OPENAI_API_KEY')


# PyAudio parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Initialize PyAudio
p = pyaudio.PyAudio()

# Open the stream
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("Recording...")

frames = []

# Record for a fixed duration (e.g., 5 seconds)
RECORD_SECONDS = 5
for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("Finished recording.")

# Stop and close the stream
stream.stop_stream()
stream.close()
p.terminate()

# Save the recorded data as a WAV file
audio_filename = 'temp_audio.wav'
wf = wave.open(audio_filename, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

# Use requests to call the OpenAI API
api_url = 'https://api.openai.com/v1/audio/transcriptions'

headers = {
    'Authorization': f'Bearer {openai_api_key}',
}

with open(audio_filename, 'rb') as audio_file:
    files = {
        'file': (audio_filename, audio_file, 'audio/wav'),
        'model': (None, 'whisper-1'),
    }

    response = requests.post(api_url, headers=headers, files=files)

    if response.status_code == 200:
        transcript = response.json()['text']
        print("Transcription:")
        print(transcript)
    else:
        print(f"Error {response.status_code}: {response.text}")

# Clean up the temporary audio file
os.remove(audio_filename)