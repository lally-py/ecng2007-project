#--------------------------------------------------------DONE---------------------------------------------------------------------------------#

# add an option to adjust the speech rate and tone of the text-to-speech engine , do this by adding in a settings page to the program preferably with a top menu bar that would have settings, help etc. -- done

#add a language model selection option for improved accuracy in different languages or accents. (change language to predominantly english allow user to select between the major languages (english and spanish and frecnch)  -- done

# Improve accessibility by adding keyboard shortcuts for navigation and common actions (e.g., starting/stopping recording). with keyboard keys, add help menu for instuctions on different operations  -- done

# Use configuration files (e.g., JSON or YAML) for managing questions, making it easier to add, remove, or modify questions without changing the code. -- done

# remove the hardcoded resume generation prompt from in the code and move it to its own file -- done

# Introduce a "pause recording" feature in addition to start/stop, for more flexibility during the voice walkthrough. -- done

# since file size limit is 25 mb, determine how long a recording would take to meet this file size,  1mb per 30 seconds , 25mb = 12.5 minutes, this should be stated in the help menu -- done
#-----------------------------------------------------------------------------------------------------------------------------------------#


#----------------------------------------------------UNDONE-------------------------------------------------------------------------------------#

# Implement more detailed error messages and logging for debugging purposes. Display user-friendly notifications when network or API issues occur and Introduce a retry mechanism for API calls that fail due to temporary issues, instead of immediately showing an error message. -- undone

# Provide an option to export the resume in various formats (e.g., PDF, Word). -- undone

# Implement a feature to autosave user responses at intervals, preventing data loss if the program crashes. -- undone

# Add a "Clear Data" button that allows users to restart the questionnaire from scratch without manually deleting previous responses, will ask for confimation before clearing whne pressed -- undone

# add a timer that shows how long you have been recording for 
#-----------------------------------------------------------------------------------------------------------------------------------------#


# TODO :
#  - After the first walkthrough is complleted save the file and use that for creating the resume itself, then modify that file and see how the template reacts
#  - Make it so that it firsts get placed into a word doc (formatted), and is then converted to a pdf for the final result
#  - allow the word doc to be downloaded as well so personal modification can be done as well 
#  - check if it is possible to get a nicer voice to talk to you in the voice assisted version


# make it so that you can email the finished resume to yourself if you want to by typing in your email address, create an email adress and get SMTP adress so i can create it (email name should be somthing along the lines of resume generator)


# TODO : based on documentation
# add user auth page
# add feedback loop - that will send data on completion back to somewhere
# data retention and deletion policy for when the data is sent 
# all data is saved locally on your system and is not sent to any server/system. 
# AUTO BACKUP INCASE OF CRASH WILL HAVE A SAVE AT LAST checkpoint

    
import customtkinter as ctk
from tkinter import messagebox
import os
import pyaudio
import wave
import tempfile
import threading
import requests  # interacts with OpenAI directly through HTTP
import pyttsx3  # For text-to-speech
import speech_recognition as sr  # For real-time speech recognition
import openai  # Added for OpenAI SDK if required
from PIL import Image  # For handling images/icons
import whisper
import numpy as np
import sounddevice as sd
import time
import io
import webrtcvad
import collections
from fuzzywuzzy import process
import json
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Set your OpenAI API key from the .env file
openai_api_key = os.getenv('OPENAI_API_KEY')

# Loads questions and their field mappings from a JSON file.
def load_questions(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            questions = [q['question'] for q in data['questions']]
            field_mapping = {q['question']: q['field'] for q in data['questions']}
        return questions, field_mapping
    except FileNotFoundError:
        messagebox.showerror("Error", f"Configuration file '{file_path}' not found.")
        return [], {}
    except json.JSONDecodeError as e:
        messagebox.showerror("Error", f"Error parsing '{file_path}': {e}")
        return [], {}
    except KeyError as e:
        messagebox.showerror("Error", f"Missing key in '{file_path}': {e}")
        return [], {}
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load questions: {e}")
        return [], {}

# Load questions and field mapping
questions, field_mapping = load_questions('questions.json')


# Initialize global variables
current_question = 0
transcribed_responses = {}
add_more_flag = False  # Flag to indicate if we are adding more to the response

# Threading events
stop_recording_event = threading.Event()
pause_recording_event = threading.Event()  # --- New Feature: Pause Recording ---

def load_trinidad_locations(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read all lines and strip any whitespace
            locations = [line.strip() for line in f if line.strip()]
        return locations
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load locations: {e}")
        return []

# Load the catalogue of Trinidad locations
places_in_trinidad = load_trinidad_locations('trinidad_locations.txt')


def find_location_matches(transcribed_address, catalogue, threshold=80):
    words = transcribed_address.split()
    matches = []
    max_phrase_length = min(5, len(words))  # Adjust based on the maximum expected length of place names

    # Generate all possible n-grams
    for size in range(1, max_phrase_length + 1):
        for i in range(len(words) - size + 1):
            phrase = ' '.join(words[i:i+size])
            match, score = process.extractOne(phrase, catalogue)
            # Debug statement to see what's being matched
            print(f"Trying phrase: '{phrase}' | Best match: '{match}' with score {score}")
            if score >= threshold:
                matches.append((match, score))

    # Remove duplicates and keep the highest score for each match
    unique_matches = {}
    for match, score in matches:
        if match not in unique_matches or score > unique_matches[match]:
            unique_matches[match] = score

    # Return matches sorted by score
    sorted_matches = sorted(unique_matches.items(), key=lambda x: x[1], reverse=True)
    return [match for match, score in sorted_matches]

def handle_address_transcription(transcribed_text):
    print(f"Transcribed Address: '{transcribed_text}'")  # Debug statement
    matched_locations = find_location_matches(transcribed_text, places_in_trinidad)

    if matched_locations:
        # Remove matched locations from the transcribed text
        other_parts = transcribed_text
        for location in matched_locations:
            other_parts = other_parts.replace(location, '')
        # Construct the final address result
        address_result = f"{other_parts.strip()}, {' '.join(matched_locations)}"
    else:
        address_result = transcribed_text

    print(f"Matched Locations: {matched_locations}")  # Debug statement
    print(f"Final Address Result: '{address_result}'")  # Debug statement

    # Save the address to the responses
    question = "Please provide your address(provide spelling if necessary)."
    transcribed_responses[question] = address_result

    # Update the transcription label
    root.after(0, update_transcription_label, f"Transcription: {address_result}")

# Function to update the status label
def update_status(message):
    if 'status_label' in globals():
        status_label.configure(text=f"Status: {message}")

# Function to handle recording and transcribing for voice mode
def record_and_transcribe_response(record_seconds):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000  # Whisper models are trained on 16kHz audio

    p = pyaudio.PyAudio()
    frames = []

    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        # Inform the user to start speaking
        root.after(0, update_status, "Recording... Please speak now.")

        for _ in range(0, int(RATE / CHUNK * record_seconds)):
            data = stream.read(CHUNK)
            frames.append(data)

        # Finish recording
        stream.stop_stream()
        stream.close()
        p.terminate()

        root.after(0, update_status, "Transcribing response...")
        # Save the recorded data as a WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            wf = wave.open(tmp_file.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            temp_filename = tmp_file.name

        # Use requests to call the OpenAI API for transcription
        try:
            api_url = 'https://api.openai.com/v1/audio/transcriptions'

            headers = {
                'Authorization': f'Bearer {openai_api_key}',
            }

            with open(temp_filename, 'rb') as audio_file:
                files = {
                    'file': (temp_filename, audio_file, 'audio/wav'),
                    'model': (None, 'whisper-1'),
                }
                data = {
                    'language': selected_language_code  # Add language parameter
                }

                response = requests.post(api_url, headers=headers, files=files, data=data)
                response.raise_for_status()

                result = response.json()
                transcription_text = result['text'].strip()
        except Exception as e:
            messagebox.showerror("Error", f"Transcription failed: {e}")
            transcription_text = ""
        finally:
            os.unlink(temp_filename)  # Remove the temp file

        return transcription_text

    except Exception as e:
        messagebox.showerror("Error", f"Error during recording: {e}")
        return ""

def listen_and_transcribe(recognizer, microphone):
    try:
        stop_phrase = "stop recording"
        transcription = []

        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            root.after(0, update_status, "Listening...")

            while True:
                audio = recognizer.listen(source, phrase_time_limit=5)

                try:
                    # Recognize speech using Google's speech recognition
                    text = recognizer.recognize_google(audio, language=selected_language_code)
                    print(f"You said: {text}")

                    if stop_phrase.lower() in text.lower():
                        print("Stop phrase detected. Ending recording.")
                        break
                    else:
                        transcription.append(text)

                except sr.UnknownValueError:
                    print("Could not understand audio. Please try again.")
                except sr.RequestError as e:
                    messagebox.showerror("Error", f"Could not request results from Google Speech Recognition service; {e}")
                    return None

        full_transcription = ' '.join(transcription)
        return full_transcription.strip()

    except Exception as e:
        messagebox.showerror("Error", f"Error during listening: {e}")
        return None

# Function to update the question label in voice mode
def update_question_voice_mode(idx):
    question = questions[idx]
    question_label.configure(text=f"Question {idx + 1}/{len(questions)}:\n{question}")
    # Update progress bar
    progress = (idx + 1) / len(questions)
    progress_bar.set(progress)
    # Update transcription label if responses exist
    if question in transcribed_responses and transcribed_responses[question]:
        transcribed_label.configure(text=f"Transcription: {transcribed_responses[question]}")
    else:
        transcribed_label.configure(text="Transcription: ")
    # Update resume preview
    update_resume_preview()

# Function to update the transcription label
def update_transcription_label(transcription_text):
    transcribed_label.configure(text=f"Transcription: {transcription_text}")
    update_resume_preview()

def listen_for_command(recognizer, microphone):
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening for command...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        # Recognize speech using Google's speech recognition
        command = recognizer.recognize_google(audio, language=selected_language_code)
        print(f"Command recognized: {command}")
        return command.lower()
    except sr.UnknownValueError:
        engine.say("Sorry, I didn't catch that.")
        engine.runAndWait()
        return None
    except sr.WaitTimeoutError:
        engine.say("No speech detected.")
        engine.runAndWait()
        return None
    except sr.RequestError as e:
        messagebox.showerror("Error", f"Could not request results from Google Speech Recognition service; {e}")
        return None

def listen_and_transcribe_with_stop_phrase(recognizer, microphone):
    audio_data = io.BytesIO()
    stop_phrase_detected = False
    concatenated_audio = []

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        root.after(0, update_status, "Listening...")

        while not stop_phrase_detected:
            try:
                # Record a short phrase
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                # Save the audio data
                concatenated_audio.append(audio.get_wav_data())
                
                # Use a temporary recognizer to check for stop phrase
                temp_recognizer = sr.Recognizer()
                temp_audio = sr.AudioData(audio.get_raw_data(), audio.sample_rate, audio.sample_width)
                try:
                    temp_text = temp_recognizer.recognize_google(temp_audio, language=selected_language_code)
                    print(f"You said: {temp_text}")
                    if "stop recording" in temp_text.lower():
                        stop_phrase_detected = True
                        # Remove "stop recording" from concatenated audio
                        concatenated_audio.pop()
                        break
                except sr.UnknownValueError:
                    pass  # Ignore unintelligible speech
            except sr.WaitTimeoutError:
                # No speech detected within timeout, continue listening
                continue

    # Concatenate all audio chunks
    full_audio_data = b"".join(concatenated_audio)

    # Create an AudioData instance for the full audio
    full_audio = sr.AudioData(full_audio_data, audio.sample_rate, audio.sample_width)

    # Transcribe the full audio
    root.after(0, update_status, "Transcribing response...")
    try:
        transcription_text = recognizer.recognize_google(full_audio, language=selected_language_code)
        root.after(0, update_transcription_label, transcription_text)
        return transcription_text.strip()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        messagebox.showerror("Error", f"Could not request results from Google Speech Recognition service; {e}")
        return None

# Function to perform the voice-assisted walkthrough
def voice_walkthrough():
    global transcribed_responses, engine
    engine = pyttsx3.init()
    engine.setProperty('rate', tts_settings['rate'])  # Use rate from settings
    engine.setProperty('voice', tts_settings['voice'].id)  # Use selected voice from settings

    # Provide initial instructions once
    initial_instructions = (
        "Welcome to the voice-assisted resume generator. "
        "You will be asked a series of questions to build your resume. "
        "After each question, please provide your response. "
        "When you are finished speaking, simply stop talking, and I will process your response. "
        "After your response, I will read it back to you. "
        "If it is correct, please say 'yes'. "
        "If it is incorrect, please say 'no' to redo your response. "
        "Let's begin."
    )
    engine.say(initial_instructions)
    engine.runAndWait()

    for idx, question in enumerate(questions):
        response_recorded = False
        while not response_recorded:
            # Update GUI with current question
            root.after(0, update_question_voice_mode, idx)
            # Update status
            root.after(0, update_status, f"Asking Question {idx+1}/{len(questions)}")

            # Speak the question
            engine.say(question)
            engine.runAndWait()

            # Record and transcribe the user's response
            transcription_text = listen_and_transcribe_with_stop_phrase(sr.Recognizer(), sr.Microphone())

            if transcription_text is None or transcription_text.strip() == "":
                engine.say("I didn't catch that. Let's try again.")
                engine.runAndWait()
                continue  # Restart the question

            # Special handling for the address question
            if question == "Please provide your address(provide spelling if necessary).":
                handle_address_transcription(transcription_text)
                address_result = transcribed_responses[question]
                # Read back the address result
                engine.say("You said:")
                engine.say(address_result)
                engine.runAndWait()
            else:
                # Standard processing for other questions
                transcribed_responses[question] = transcription_text
                # Update the transcription label
                root.after(0, update_transcription_label, transcription_text)
                # Read back the response
                engine.say("You said:")
                engine.say(transcription_text)
                engine.runAndWait()

            # Confirmation loop
            confirmation_received = False
            while not confirmation_received:
                # Ask if the response is correct
                engine.say("Is this correct? Please say 'yes' to confirm or 'no' to try again.")
                engine.runAndWait()

                # Listen for confirmation
                recognizer = sr.Recognizer()
                microphone = sr.Microphone()
                confirmation = listen_for_command(recognizer, microphone)
                if confirmation is not None and 'yes' in confirmation.lower():
                    # Save the response (already saved for the address question)
                    if question != "Please provide your address(provide spelling if necessary).":
                        transcribed_responses[question] = transcription_text
                    response_recorded = True  # Move to the next question
                    confirmation_received = True  # Exit confirmation loop
                    # Update the resume preview
                    root.after(0, update_resume_preview)
                elif confirmation is not None and 'no' in confirmation.lower():
                    engine.say("Let's try again.")
                    engine.runAndWait()
                    confirmation_received = True  # Exit confirmation loop to redo the question
                    # Do not set response_recorded to True, so the question will be re-asked
                else:
                    engine.say("I didn't understand your response. Please say 'yes' or 'no'.")
                    engine.runAndWait()
                    # Continue the confirmation loop without changing confirmation_received

    # After all questions are done
    root.after(0, update_status, "Voice Walkthrough Completed")
    # Generate and save the formatted resume
    generate_and_save_formatted_resume()
    # Inform the user
    engine.say("Voice walkthrough completed. Your formatted resume has been generated and saved.")
    engine.runAndWait()

# Function to record and transcribe using OpenAI Whisper API
def listen_and_transcribe_with_whisper():
    CHUNK_DURATION_MS = 30  # Duration of a chunk in milliseconds
    SAMPLE_RATE = 16000  # Sample rate in Hz
    CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # Chunk size in samples
    FORMAT = pyaudio.paInt16  # 16-bit int sampling
    CHANNELS = 1  # Mono audio

    # Initialize VAD
    vad = webrtcvad.Vad(1)  # Aggressiveness from 0 to 3
    frames = []
    silence_threshold = 5  # Seconds of silence before stopping
    silence_counter = 0  # Counter for silence duration

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=CHUNK_SIZE)

    root.after(0, update_status, "Listening... Please speak now.")
    print("Listening... Please speak now.")

    try:
        while True:
            frame = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            is_speech = vad.is_speech(frame, SAMPLE_RATE)

            if is_speech:
                frames.append(frame)
                silence_counter = 0  # Reset silence counter when speech is detected
            else:
                silence_counter += CHUNK_DURATION_MS / 1000.0  # Increment silence counter
                if silence_counter >= silence_threshold:
                    print("Silence detected. Stopping recording.")
                    break
                frames.append(frame)  # Optionally include silence frames
    except Exception as e:
        messagebox.showerror("Error", f"Error during recording: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    root.after(0, update_status, "Transcribing response...")
    # Save the recorded data as a WAV file
    temp_filename = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            wf = wave.open(tmp_file.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            temp_filename = tmp_file.name

        # Use requests to call the OpenAI API for transcription
        try:
            api_url = 'https://api.openai.com/v1/audio/transcriptions'

            headers = {
                'Authorization': f'Bearer {openai_api_key}',
            }

            with open(temp_filename, 'rb') as audio_file:
                files = {
                    'file': (temp_filename, audio_file, 'audio/wav'),
                    'model': (None, 'whisper-1'),
                }
                data = {
                    'language': selected_language_code  # Add language parameter
                }

                response = requests.post(api_url, headers=headers, files=files, data=data)
                response.raise_for_status()

                result = response.json()
                transcription_text = result['text'].strip()
        except Exception as e:
            error_message = response.json().get('error', {}).get('message', str(e))
            messagebox.showerror("Error", f"Transcription failed: {error_message}")
            transcription_text = ""
    finally:
        if temp_filename:
            os.unlink(temp_filename)  # Remove the temp file

    return transcription_text

# Function to handle recording and transcribing
def recording_thread_function():
    global transcribed_responses, add_more_flag

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000  # Whisper models are trained on 16kHz audio

    p = pyaudio.PyAudio()

    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        messagebox.showerror("Error", f"Could not open microphone: {e}")
        root.after(0, update_status, "Ready")
        return False

    frames = []

    print("Recording...")
    root.after(0, update_status, "Recording...")

    while not stop_recording_event.is_set():
        if pause_recording_event.is_set():
            # If paused, wait until the pause is lifted
            time.sleep(0.1)
            continue
        try:
            data = stream.read(CHUNK)
            frames.append(data)
        except Exception as e:
            messagebox.showerror("Error", f"Error while recording: {e}")
            break

    print("Finished recording.")
    root.after(0, update_status, "Processing transcription...")

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save the recorded data as a WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        wf = wave.open(tmp_file.name, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        temp_filename = tmp_file.name

    # Use requests to call the OpenAI API for transcription
    try:
        api_url = 'https://api.openai.com/v1/audio/transcriptions'

        headers = {
            'Authorization': f'Bearer {openai_api_key}',
        }

        with open(temp_filename, 'rb') as audio_file:
            files = {
                'file': (temp_filename, audio_file, 'audio/wav'),
                'model': (None, 'whisper-1'),
            }
            data = {
                'language': selected_language_code  # Add language parameter
            }

            response = requests.post(api_url, headers=headers, files=files, data=data)
            response.raise_for_status()

            result = response.json()
            transcription_text = result['text'].strip()
    except Exception as e:
        messagebox.showerror("Error", f"Transcription failed: {e}")
        transcription_text = ""
    finally:
        os.unlink(temp_filename)  # Remove the temp file

    # Update the transcription label
    root.after(0, update_transcription_label, transcription_text)
    # Update 'Add More' button state
    root.after(0, update_add_more_button_state)

    # Save responses
    current_q = questions[current_question]
    if add_more_flag:
        # Append to existing responses
        transcribed_responses[current_q] += " " + transcription_text if current_q in transcribed_responses else transcription_text
    else:
        # Replace existing responses
        transcribed_responses[current_q] = transcription_text

    # Reset add_more_flag
    add_more_flag = False

    # Schedule GUI updates
    root.after(0, update_resume_preview)
    root.after(0, enable_buttons_after_recording)
    root.after(0, update_status, "Ready")
    root.after(0, show_decision_frame)

# Function to start recording in a new thread
def start_recording_thread(add_more=False):
    global add_more_flag
    stop_recording_event.clear()
    pause_recording_event.clear()  # Clear pause at start
    add_more_flag = add_more
    # Hide decision frame first
    hide_decision_frame()
    # Disable buttons during recording
    disable_buttons_for_recording()
    # Enable the Pause button with initial text and color
    pause_button.configure(state="normal", text="Pause Recording", fg_color="green")  # Set to green indicating active recording
    # Update labels to indicate recording
    transcribed_label.configure(text="Transcription: Recording...")
    update_status("Recording...")
    # Start recording thread
    recording_thread = threading.Thread(target=recording_thread_function)
    recording_thread.start()


# Function to stop recording
def stop_recording():
    stop_recording_event.set()
    # Reset the pause event in case recording was paused
    pause_recording_event.clear()
    # Update label to indicate processing
    transcribed_label.configure(text="Transcription: Processing...")
    update_status("Processing transcription...")
    # Disable the stop and pause buttons to prevent multiple presses
    stop_button.configure(state="disabled")
    pause_button.configure(state="disabled", text="Pause Recording", fg_color="green")  # Reset to initial state


# Function to toggle pause/resume recording
def toggle_pause_recording():
    if not pause_recording_event.is_set():
        # Pause the recording
        pause_recording_event.set()
        pause_button.configure(text="Resume Recording", fg_color="red")  # Change text and color to red
        update_status("Recording Paused.")
    else:
        # Resume the recording
        pause_recording_event.clear()
        pause_button.configure(text="Pause Recording", fg_color="green")  # Revert text and color to green
        update_status("Recording Resumed.")


# Function to disable buttons during recording
def disable_buttons_for_recording():
    start_button.configure(state="disabled")
    stop_button.configure(state="normal")
    pause_button.configure(state="normal")  # Enable Pause Button
    next_button.configure(state="disabled")
    prev_button.configure(state="disabled")
    save_button.configure(state="disabled")
    skip_button.configure(state="disabled")
    add_more_main_button.configure(state="disabled")  # Disable 'Add More' button

# Function to re-enable buttons after recording
def enable_buttons_after_recording():
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")
    pause_button.configure(state="disabled", text="Pause Recording", fg_color="green")  # Reset to initial state
    next_button.configure(state="normal")
    prev_button.configure(state="normal")
    save_button.configure(state="normal")
    skip_button.configure(state="normal")
    update_add_more_button_state()  # Update 'Add More' button state


# Function to navigate to the next question
def next_question_func():
    global current_question
    if current_question < len(questions) - 1:
        current_question += 1
        update_question()
    else:
        messagebox.showinfo("End", "You have reached the last question.")

# Function to navigate to the previous question
def prev_question_func():
    global current_question
    if current_question > 0:
        current_question -= 1
        update_question()
    else:
        messagebox.showinfo("Start", "You are at the first question.")

# Function to update the question label and display existing responses if any
def update_question():
    question = questions[current_question]
    question_label.configure(text=f"Question {current_question + 1}/{len(questions)}:\n{question}")

    # Update transcription label if responses exist
    if question in transcribed_responses and transcribed_responses[question]:
        transcribed_label.configure(text=f"Transcription: {transcribed_responses[question]}")
    else:
        transcribed_label.configure(text="Transcription: ")

    # Update 'Add More' button state
    update_add_more_button_state()

    # Update progress bar
    progress = (current_question + 1) / len(questions)
    progress_bar.set(progress)


# Function to generate resume text from responses
def generate_resume_text():
    # If there are no responses, return an empty string
    if not any(transcribed_responses.values()):
        return ""

    # Define the resume sections based on the provided prompt
    resume_sections = {
        "Name": transcribed_responses.get(questions[0], "").strip(),
        "Contact Number": transcribed_responses.get(questions[1], "").strip(),
        "Email Address": transcribed_responses.get(questions[2], "").strip(),
        "Address": transcribed_responses.get(questions[3], "").strip(),
        "Professional Summary": transcribed_responses.get(questions[4], "").strip(),
        "Skills": transcribed_responses.get(questions[5], "").strip(),
        "Certifications and Training": transcribed_responses.get(questions[6], "").strip(),
        "Professional Achievements": transcribed_responses.get(questions[7], "").strip(),
        "Interests": transcribed_responses.get(questions[13], "").strip(),
        "Extracurricular Activities": transcribed_responses.get(questions[14], "").strip(),
        "Volunteer Experience": transcribed_responses.get(questions[15], "").strip(),
        "Professional Associations": transcribed_responses.get(questions[16], "").strip(),
        "References": "Available upon request."
    }

    # Start building the resume text
    resume_text = ""
    significant_sections_added = 0  # Counter for significant sections added

    # Function to add section if response exists
    def add_section(title, content, is_significant=False):
        nonlocal resume_text, significant_sections_added
        if content.strip():
            resume_text += f"{title}:\n{content}\n\n"
            if is_significant:
                significant_sections_added += 1

    # Add Name section separately
    if resume_sections["Name"]:
        resume_text += f"Name:\n{resume_sections['Name']}\n\n"

    # Add Contact Information
    if resume_sections["Contact Number"]:
        resume_text += f"Contact Number:\n{resume_sections['Contact Number']}\n\n"
    if resume_sections["Email Address"]:
        resume_text += f"Email Address:\n{resume_sections['Email Address']}\n\n"
    if resume_sections["Address"]:
        resume_text += f"Address:\n{resume_sections['Address']}\n\n"

    # Add significant sections
    add_section("Professional Summary", resume_sections["Professional Summary"], is_significant=True)

    # Handle Skills
    if resume_sections["Skills"]:
        skills_list = [skill.strip() for skill in resume_sections["Skills"].split(',') if skill.strip()]
        if skills_list:
            resume_text += "Skills:\n"
            for skill in skills_list:
                resume_text += f"- {skill}\n"
            resume_text += "\n"
            significant_sections_added += 1

    # Handle Certifications and Training
    if resume_sections["Certifications and Training"]:
        certs_list = [cert.strip() for cert in resume_sections["Certifications and Training"].split(',') if cert.strip()]
        if certs_list:
            resume_text += "Certifications and Training:\n"
            for cert in certs_list:
                resume_text += f"- {cert}\n"
            resume_text += "\n"
            significant_sections_added += 1

    # Handle Professional Achievements
    if resume_sections["Professional Achievements"]:
        achievements_list = [ach.strip() for ach in resume_sections["Professional Achievements"].split(',') if ach.strip()]
        if achievements_list:
            resume_text += "Professional Achievements:\n"
            for ach in achievements_list:
                resume_text += f"- {ach}\n"
            resume_text += "\n"
            significant_sections_added += 1

    # Handle Work Experience
    work_place = transcribed_responses.get(questions[8], '').strip()
    position_description = transcribed_responses.get(questions[9], '').strip()
    key_projects = transcribed_responses.get(questions[10], '').strip()

    work_experience_content = ""
    if work_place:
        work_experience_content += f"{work_place}\n"
    if position_description:
        work_experience_content += f"{position_description}\n"
    if key_projects:
        work_experience_content += f"Key Projects:\n{key_projects}\n"
    if work_experience_content.strip():
        resume_text += f"Work Experience:\n{work_experience_content.strip()}\n\n"
        significant_sections_added += 1

    # Handle Education
    prior_education = transcribed_responses.get(questions[11], '').strip()
    current_education = transcribed_responses.get(questions[12], '').strip()
    education_content = ""
    if prior_education:
        education_content += f"{prior_education}\n"
    if current_education:
        education_content += f"{current_education}\n"
    if education_content.strip():
        resume_text += f"Education:\n{education_content.strip()}\n\n"
        significant_sections_added += 1

    # Handle Interests
    if resume_sections["Interests"]:
        interests_list = [interest.strip() for interest in resume_sections["Interests"].split(',') if interest.strip()]
        if interests_list:
            resume_text += "Interests:\n"
            for interest in interests_list:
                resume_text += f"- {interest}\n"
            resume_text += "\n"
            significant_sections_added += 1

    # Handle Extracurricular Activities
    add_section("Extracurricular Activities", resume_sections["Extracurricular Activities"], is_significant=True)

    # Handle Volunteer Experience
    add_section("Volunteer Experience", resume_sections["Volunteer Experience"], is_significant=True)

    # Handle Professional Associations
    if resume_sections["Professional Associations"]:
        associations_list = [assoc.strip() for assoc in resume_sections["Professional Associations"].split(',') if assoc.strip()]
        if associations_list:
            resume_text += "Professional Associations:\n"
            for assoc in associations_list:
                resume_text += f"- {assoc}\n"
            resume_text += "\n"
            significant_sections_added += 1

    # Only add References if significant sections were added
    if significant_sections_added > 0:
        resume_text += f"References:\n{resume_sections['References']}\n"

    return resume_text.strip()

# Function to update the resume preview textbox
def update_resume_preview():
    resume_text = generate_resume_text()
    resume_preview_textbox.configure(state="normal")
    resume_preview_textbox.delete("1.0", "end")
    resume_preview_textbox.insert("end", resume_text)
    resume_preview_textbox.configure(state="disabled")  # Make it read-only
    # Save responses to file
    save_responses_to_file()


# Function to save the responses to a text file without replacing field names
def save_responses_to_file():
    try:
        with open('responses.txt', 'w', encoding='utf-8') as f:
            for question in questions:
                # Get the corresponding field name (e.g., [NAME], [CONTACT NUMBER])
                field_name = field_mapping.get(question, question)
                response = transcribed_responses.get(question, "")
                
                # Write the field name as it is, and append the response after the dash
                f.write(f"{field_name} - {response}\n")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save responses: {e}")

# Function to save the resume to a text file and generate formatted resume via ChatGPT
def save_resume():
    resume_text = generate_resume_text()
    try:
        # Save the basic resume preview
        with open('generated_resume.txt', 'w', encoding='utf-8') as f:
            f.write(resume_text)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save basic resume: {e}")
        return

    # Now generate formatted resume via ChatGPT
    formatted_resume = generate_formatted_resume()
    if formatted_resume:
        try:
            with open('formatted_resume.txt', 'w', encoding='utf-8') as f:
                f.write(formatted_resume)
            messagebox.showinfo("Success", "Your formatted resume has been saved as 'formatted_resume.txt'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save formatted resume: {e}")
    else:
        messagebox.showerror("Error", "Failed to generate formatted resume via ChatGPT.")

# Function to generate formatted resume via ChatGPT
def generate_formatted_resume():
    """
    Generates a formatted resume by loading the resume prompt template,
    inserting the user responses into the Input section, and sending it to ChatGPT.
    """
    try:
        # Load the resume prompt template
        with open('resume_prompt.txt', 'r', encoding='utf-8') as f:
            resume_template = f.read()

        # Construct the input_section with [FIELD] - value pairs
        input_section = ""
        for question in questions:
            field = field_mapping.get(question, question)  # Get the field name
            response = transcribed_responses.get(question, "").strip()
            if response:  # Only include fields that have responses
                input_section += f"{field} - {response}\n"

        # Replace the {input_section} placeholder in the template
        filled_resume_template = resume_template.replace("{input_section}", input_section.strip())

        # Debug: Print the filled resume template
        print("=== Filled Resume Template ===")
        print(filled_resume_template)
        print("=== End of Template ===")

        # Prepare the full prompt for OpenAI
        full_prompt = filled_resume_template

        # Send the prompt to the OpenAI API
        api_url = 'https://api.openai.com/v1/chat/completions'

        headers = {
            'Authorization': f'Bearer {openai_api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            "model": "gpt-3.5-turbo",  # You can use a different model if preferred
            "messages": [
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 2000,  # Adjust as needed
            "n": 1,
            "temperature": 0.7
        }

        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        formatted_resume = result['choices'][0]['message']['content'].strip()
        
        # Debug: Print the formatted resume received from OpenAI
        print("=== Formatted Resume ===")
        print(formatted_resume)
        print("=== End of Formatted Resume ===")
        
        return formatted_resume

    except FileNotFoundError:
        messagebox.showerror("Error", "The resume prompt file 'resume_prompt.txt' was not found.")
        return None
    except requests.exceptions.HTTPError as e:
        error_message = response.json().get('error', {}).get('message', str(e))
        messagebox.showerror("Error", f"OpenAI API request failed: {error_message}")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate formatted resume: {e}")
        return None



# Function to generate and save the formatted resume via ChatGPT
def generate_and_save_formatted_resume():
    # Update status
    update_status("Generating formatted resume...")
    try:
        # Now generate formatted resume via ChatGPT
        formatted_resume = generate_formatted_resume()
        if formatted_resume:
            try:
                with open('formatted_resume.txt', 'w', encoding='utf-8') as f:
                    f.write(formatted_resume)
                messagebox.showinfo("Success", "Your formatted resume has been saved as 'formatted_resume.txt'.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save formatted resume: {e}")
        else:
            messagebox.showerror("Error", "Failed to generate formatted resume via ChatGPT.")
    finally:
        update_status("Ready")

# Function to skip the current question
def skip_question_func():
    current_q = questions[current_question]
    transcribed_responses[current_q] = ""
    update_resume_preview()
    update_add_more_button_state()
    next_question_func()


# Function to show decision frame
def show_decision_frame():
    decision_frame.pack(pady=10, padx=20, fill="x")
    # Disable main buttons
    start_button.configure(state="disabled")
    stop_button.configure(state="disabled")
    pause_button.configure(state="disabled")  # --- New Feature: Disable Pause Button ---
    next_button.configure(state="disabled")
    prev_button.configure(state="disabled")
    save_button.configure(state="disabled")
    skip_button.configure(state="disabled")
    add_more_main_button.configure(state="disabled")  # Disable 'Add More' button

# Function to hide decision frame
def hide_decision_frame():
    decision_frame.pack_forget()
    # Enable main buttons
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")
    pause_button.configure(state="disabled", text="Pause Recording")  # --- New Feature: Disable Pause Button ---
    next_button.configure(state="normal")
    prev_button.configure(state="normal")
    save_button.configure(state="normal")
    skip_button.configure(state="normal")
    update_add_more_button_state()  # Update 'Add More' button state

# Function when user accepts the response
def accept_response():
    hide_decision_frame()
    next_question_func()

# Function when user wants to redo the response
def redo_response():
    hide_decision_frame()
    # Clear the response for the current question
    current_q = questions[current_question]
    transcribed_responses[current_q] = ""
    update_resume_preview()
    update_add_more_button_state()
    start_recording_thread(add_more=False)

# Function when user wants to add more to the response
def add_more_response():
    hide_decision_frame()
    start_recording_thread(add_more=True)

# ========================== Settings Implementation ==========================

# Global dictionary to store TTS settings and language selection
tts_settings = {
    'rate': 200,  # Default speech rate
    'voice': None,  # To be set after initializing engine
    'language': 'English'  # Default language
}

# Mapping of languages to their codes
language_mapping = {
    'English': 'en',
    'Spanish': 'es',
    'French': 'fr'
}

selected_language = tts_settings['language']
selected_language_code = language_mapping[selected_language]

# Initialize the pyttsx3 engine globally
engine = pyttsx3.init()
# Set default properties
engine.setProperty('rate', tts_settings['rate'])

# Get available voices and set default
voices = engine.getProperty('voices')
if voices:
    # Default to first voice that matches the selected language, else first voice
    selected_voice = next((voice for voice in voices if selected_language_code in voice.languages or selected_language_code in voice.id.lower()), voices[0])
    tts_settings['voice'] = selected_voice
    engine.setProperty('voice', selected_voice.id)
else:
    messagebox.showerror("Error", "No voices available for the text-to-speech engine.")

# Function to open the Settings window
def open_settings():
    settings_window = ctk.CTkToplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("400x400")
    settings_window.resizable(False, False)

    # Label for Speech Rate
    rate_label = ctk.CTkLabel(settings_window, text="Speech Rate:", font=("Helvetica", 14))
    rate_label.pack(pady=(20, 5))

    # Slider for Speech Rate
    rate_slider = ctk.CTkSlider(settings_window, from_=100, to=300, number_of_steps=200, command=lambda val: update_rate(val))
    rate_slider.set(tts_settings['rate'])
    rate_slider.pack(pady=5, padx=20, fill="x")

    # Display current rate value
    rate_value_label = ctk.CTkLabel(settings_window, text=f"{tts_settings['rate']} words per minute", font=("Helvetica", 12))
    rate_value_label.pack(pady=5)

    # Update label when slider moves
    def on_rate_change(val):
        rate = int(float(val))
        rate_value_label.configure(text=f"{rate} words per minute")

    rate_slider.configure(command=lambda val: [update_rate(val), on_rate_change(val)])

    # Label for Voice Selection
    voice_label = ctk.CTkLabel(settings_window, text="Select Voice:", font=("Helvetica", 14))
    voice_label.pack(pady=(20, 5))

    # Dropdown for Voice Selection
    voice_options = [voice.name for voice in voices]
    selected_voice_name = ctk.StringVar(value=tts_settings['voice'].name if tts_settings['voice'] else "")

    voice_dropdown = ctk.CTkOptionMenu(settings_window, values=voice_options, variable=selected_voice_name, command=lambda val: update_voice(val))
    voice_dropdown.pack(pady=5, padx=20, fill="x")

    # Label for Language Selection
    language_label = ctk.CTkLabel(settings_window, text="Select Language:", font=("Helvetica", 14))
    language_label.pack(pady=(20, 5))

    # Dropdown for Language Selection
    language_options = list(language_mapping.keys())
    selected_language_var = ctk.StringVar(value=tts_settings['language'])

    language_dropdown = ctk.CTkOptionMenu(settings_window, values=language_options, variable=selected_language_var, command=lambda val: update_language(val))
    language_dropdown.pack(pady=5, padx=20, fill="x")

    # Close Button
    close_button = ctk.CTkButton(settings_window, text="Close", command=settings_window.destroy)
    close_button.pack(pady=20)

# Function to update speech rate
def update_rate(val):
    rate = int(float(val))
    tts_settings['rate'] = rate
    engine.setProperty('rate', rate)

# Function to update voice
def update_voice(voice_name):
    selected = next((voice for voice in voices if voice.name == voice_name), None)
    if selected:
        tts_settings['voice'] = selected
        engine.setProperty('voice', selected.id)
    else:
        messagebox.showerror("Error", "Selected voice not found.")

# Function to update language
def update_language(language):
    global selected_language, selected_language_code
    if language in language_mapping:
        selected_language = language
        selected_language_code = language_mapping[language]
        tts_settings['language'] = language
        # Optionally, you can also set the voice to match the language
        # This requires that voices are tagged with their languages
        # For simplicity, we're not changing the voice based on language
    else:
        messagebox.showerror("Error", "Selected language not supported.")

# ========================== End of Settings Implementation ==========================

# GUI Setup using customtkinter
ctk.set_appearance_mode("System")  # Options: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("dark-blue")  # Options: "blue" (default), "green", "dark-blue"

root = ctk.CTk()
root.title("Resume Generator")
root.geometry("1400x800")
root.resizable(True, True)  # Make the window resizable

# ========================== Menu Bar Implementation ==========================

# Help Button
def create_menu_bar():
    menu_bar = ctk.CTkFrame(root, corner_radius=0)
    menu_bar.pack(side="top", fill="x")

    # Settings Button
    settings_button = ctk.CTkButton(
        menu_bar,
        text="Settings",
        command=open_settings,
        width=100,
        height=30,
        fg_color="transparent",
        hover_color="gray70",
        text_color="white",
        font=("Helvetica", 12)
    )
    settings_button.pack(side="left", padx=10, pady=5)

    # Help Button
    def show_help():
        # Create a new top-level window for the Help Menu
        help_window = ctk.CTkToplevel(root)
        help_window.title("Help")
        help_window.geometry("800x600")
        help_window.resizable(False, False)  # Fixed size for consistency

        # Create a frame to hold all help content with padding
        help_frame = ctk.CTkFrame(help_window, corner_radius=10)
        help_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Add a title label
        title_label = ctk.CTkLabel(
            help_frame,
            text="Resume Generator Help",
            font=("Helvetica", 20, "bold"),
            anchor="w"
        )
        title_label.pack(pady=(0, 10), anchor="w")

        # Create a scrollable frame in case content overflows
        scroll_frame = ctk.CTkScrollableFrame(help_frame, width=760, height=500)
        scroll_frame.pack(pady=10, padx=5, fill="both", expand=True)

        # Helper function to add section titles
        def add_section_title(text):
            section_label = ctk.CTkLabel(
                scroll_frame,
                text=text,
                font=("Helvetica", 16, "bold"),
                anchor="w"
            )
            section_label.pack(pady=(10, 5), anchor="w")

        # Helper function to add bullet points
        def add_bullet_point(text):
            bullet_label = ctk.CTkLabel(
                scroll_frame,
                text=f"• {text}",
                font=("Helvetica", 12),
                anchor="w"
            )
            bullet_label.pack(pady=2, anchor="w")

        # Helper function to add numbered lists
        def add_numbered_list(text, number):
            numbered_label = ctk.CTkLabel(
                scroll_frame,
                text=f"{number}. {text}",
                font=("Helvetica", 12),
                anchor="w"
            )
            numbered_label.pack(pady=2, anchor="w")

        # -------------------- Help Content Sections --------------------

        # How to Use Section
        add_section_title("How to Use")
        add_numbered_list("Manual Walkthrough: Enter your details manually.", 1)
        add_numbered_list("Voice Walkthrough: Answer questions verbally using your microphone.", 2)

        # Keyboard Shortcuts Section
        add_section_title("Keyboard Shortcuts")
        add_bullet_point("Ctrl+R: Start/Stop voice recording")
        add_bullet_point("Ctrl+N: Next question")
        add_bullet_point("Ctrl+P: Previous question")
        add_bullet_point("Ctrl+S: Save your resume")
        add_bullet_point("Ctrl+A: Add more details")
        add_bullet_point("Ctrl+Q: Quit the app")

        # Settings Section
        add_section_title("Settings")
        add_bullet_point("Adjust speech speed and choose a Text-to-Speech (TTS) voice.")
        add_bullet_point("Select a transcription language for better accuracy.")

        # Microphone Setup Section
        add_section_title("Microphone Setup")
        add_bullet_point("Ensure your microphone is properly connected for the voice mode to function correctly.")

        # Recording Guidelines Section
        add_section_title("Recording Guidelines")
        add_bullet_point("Maximum File Size: 25 MB per recording.")
        add_bullet_point("Estimated Duration: Approximately 30 seconds per 1 MB, allowing up to 12.5 minutes per recording.")
        add_bullet_point("Monitoring Size: The application displays the recording size in MB before sending it for transcription.")

        # Recording Tips Section
        add_section_title("Recording Tips")
        add_bullet_point("Speak Clearly: Enunciate your words for better transcription accuracy.")
        add_bullet_point("Minimize Background Noise: Reduce ambient sounds to avoid interference.")
        add_bullet_point("Stay Within Limits: Keep recordings under the 12-minute threshold to prevent errors.")

        # Contact Information Section
        add_section_title("Need Help?")
        contact_label = ctk.CTkLabel(
            scroll_frame,
            text="For assistance or questions, please contact our support team at support@example.com.",
            font=("Helvetica", 12),
            anchor="w",
            wraplength=700
        )
        contact_label.pack(pady=(2, 10), anchor="w")

        # Optional: Add a close button at the bottom
        close_button = ctk.CTkButton(
            help_frame,
            text="Close",
            command=help_window.destroy,
            width=100,
            height=40,
            fg_color="blue",
            text_color="white",
            font=("Helvetica", 12)
        )
        close_button.pack(pady=10)

    help_button = ctk.CTkButton(
        menu_bar,
        text="Help",
        command=show_help,
        width=100,
        height=30,
        fg_color="transparent",
        hover_color="gray70",
        text_color="white",
        font=("Helvetica", 12)
    )
    help_button.pack(side="left", padx=10, pady=5)

    # ========================== Keyboard Shortcuts Implementation ==========================

    def on_shortcut(event):
        # Mapping keyboard shortcuts to functions
        # Ctrl+R: Start/Stop Recording
        # Ctrl+N: Next Question
        # Ctrl+P: Previous Question
        # Ctrl+S: Save Resume
        # Ctrl+A: Add More
        # Ctrl+Q: Quit Application
        if event.state & 0x0004:  # Ctrl key
            if event.keysym.lower() == 'r':
                # Toggle Recording
                if stop_button.cget('state') == 'normal':
                    stop_recording()
                else:
                    start_recording_thread(add_more=False)
            elif event.keysym.lower() == 'n':
                next_question_func()
            elif event.keysym.lower() == 'p':
                prev_question_func()
            elif event.keysym.lower() == 's':
                save_resume()
            elif event.keysym.lower() == 'a':
                add_more_response()
            elif event.keysym.lower() == 'q':
                root.quit()

    root.bind_all("<Control-r>", on_shortcut)  # Ctrl+R
    root.bind_all("<Control-n>", on_shortcut)  # Ctrl+N
    root.bind_all("<Control-p>", on_shortcut)  # Ctrl+P
    root.bind_all("<Control-s>", on_shortcut)  # Ctrl+S
    root.bind_all("<Control-a>", on_shortcut)  # Ctrl+A
    root.bind_all("<Control-q>", on_shortcut)  # Ctrl+Q

    # ========================== End of Keyboard Shortcuts Implementation ==========================

create_menu_bar()

# Load icons (Ensure the icons are in the same directory or provide the correct path)
try:
    manual_icon = ctk.CTkImage(Image.open("icons/manual_icon.png"), size=(20, 20))
    voice_icon = ctk.CTkImage(Image.open("icons/voice_icon.png"), size=(20, 20))
    start_icon = ctk.CTkImage(Image.open("icons/start_icon.png"), size=(20, 20))
    stop_icon = ctk.CTkImage(Image.open("icons/stop_icon.png"), size=(20, 20))
    next_icon = ctk.CTkImage(Image.open("icons/next_icon.png"), size=(20, 20))
    prev_icon = ctk.CTkImage(Image.open("icons/prev_icon.png"), size=(20, 20))
    save_icon = ctk.CTkImage(Image.open("icons/save_icon.png"), size=(20, 20))
    skip_icon = ctk.CTkImage(Image.open("icons/skip_icon.png"), size=(20, 20))
    accept_icon = ctk.CTkImage(Image.open("icons/accept_icon.png"), size=(20, 20))
    redo_icon = ctk.CTkImage(Image.open("icons/redo_icon.png"), size=(20, 20))
    add_more_icon = ctk.CTkImage(Image.open("icons/add_more_icon.png"), size=(20, 20))
    pause_icon = ctk.CTkImage(Image.open("icons/pause_icon.png"), size=(20, 20))
except Exception as e:
    print(f"Icon loading failed: {e}")
    manual_icon = None
    voice_icon = None
    start_icon = None
    stop_icon = None
    next_icon = None
    prev_icon = None
    save_icon = None
    skip_icon = None
    accept_icon = None
    redo_icon = None
    add_more_icon = None
    pause_icon = None

# Progress Bar
progress_bar = ctk.CTkProgressBar(root, width=400, height=20)
progress_bar.set(0)  # Initial progress
progress_bar.pack(pady=(20, 10), padx=20)

# Function to show the start page
def show_start_page():
    start_frame = ctk.CTkFrame(root, corner_radius=10)
    start_frame.pack(pady=10, padx=20, fill="both", expand=True)

    # Welcome Image or Logo (Ensure the image exists)
    try:
        logo_image = ctk.CTkImage(Image.open("icons/logo.png"), size=(100, 100))
        logo_label = ctk.CTkLabel(start_frame, image=logo_image, text="")
        logo_label.image = logo_image  # Keep a reference
        logo_label.pack(pady=(20, 10))
    except Exception as e:
        print(f"Logo loading failed: {e}")

    welcome_label = ctk.CTkLabel(start_frame, text="Welcome to the Resume Generator", font=("Helvetica", 26, "bold"))
    welcome_label.pack(pady=10)

    instruction_label = ctk.CTkLabel(start_frame, text="Please select an option to proceed", font=("Helvetica", 16))
    instruction_label.pack(pady=10)

    # Manual Walkthrough Button
    manual_button = ctk.CTkButton(
        start_frame,
        text="Manual Walkthrough",
        image=manual_icon,
        compound="left",
        command=lambda: start_manual_mode(start_frame),
        width=200,
        height=50,
        font=("Helvetica", 14)
    )
    manual_button.pack(pady=10)

    # Voice Assisted Walkthrough Button
    voice_button = ctk.CTkButton(
        start_frame,
        text="Voice Assisted Walkthrough",
        image=voice_icon,
        compound="left",
        command=lambda: start_voice_mode(start_frame),
        width=200,
        height=50,
        font=("Helvetica", 14)
    )
    voice_button.pack(pady=10)

# Function to start manual mode with voice recording
def start_manual_mode(start_frame):
    start_frame.destroy()
    initialize_manual_gui()

# Function to start voice mode
def start_voice_mode(start_frame):
    start_frame.destroy()
    initialize_voice_gui()
    threading.Thread(target=voice_walkthrough, daemon=True).start()

# Function to initialize the voice GUI
def initialize_voice_gui():
    global status_label, question_label, transcribed_label, resume_preview_textbox
    # Create a frame for the voice mode
    voice_frame = ctk.CTkFrame(root, corner_radius=10)
    voice_frame.pack(pady=10, padx=20, fill="both", expand=True)

    # Status Label
    status_label = ctk.CTkLabel(
        voice_frame,
        text="Status: Starting Voice Walkthrough...",
        wraplength=760,
        font=("Helvetica", 14, "italic")
    )
    status_label.pack(pady=5, padx=20, anchor="w")

    # Label to display the current question
    question_label = ctk.CTkLabel(
        voice_frame,
        text="",
        wraplength=760,
        font=("Helvetica", 16, "bold")
    )
    question_label.pack(pady=5, padx=20, anchor="w")

    # Label to display transcription
    transcribed_label = ctk.CTkLabel(
        voice_frame,
        text="Transcription: ",
        wraplength=760,
        font=("Helvetica", 12)
    )
    transcribed_label.pack(pady=5, padx=20, anchor="w")

    # Resume Preview Textbox
    resume_preview_label = ctk.CTkLabel(
        voice_frame,
        text="Resume Preview:",
        font=("Helvetica", 16, "bold")
    )
    resume_preview_label.pack(pady=(10, 5), padx=20, anchor="w")

    resume_preview_textbox = ctk.CTkTextbox(
        voice_frame,
        width=760,
        height=300,
        wrap="word",
        font=("Helvetica", 12)
    )
    resume_preview_textbox.pack(pady=5, padx=20)
    resume_preview_textbox.configure(state="disabled")  # Make it read-only

def update_add_more_button_state():
    question = questions[current_question]
    if question in transcribed_responses and transcribed_responses[question].strip():
        # There is an existing response, enable 'Add More' button
        add_more_main_button.configure(state="normal")
    else:
        # No response yet, disable 'Add More' button
        add_more_main_button.configure(state="disabled")

# Function to initialize the manual input GUI with voice recording
def initialize_manual_gui():
    global question_label, transcribed_label
    global start_button, stop_button, pause_button, next_button, prev_button, save_button, skip_button, generate_button
    global status_label, resume_preview_textbox, decision_frame
    global add_more_main_button  # Add this line

    # Frame for question and recording
    question_frame = ctk.CTkFrame(root, corner_radius=10)
    question_frame.pack(pady=10, padx=20, fill="x")

    # Label to display the current question
    question_label = ctk.CTkLabel(
        question_frame,
        text="",
        wraplength=760,
        font=("Helvetica", 16, "bold")
    )
    question_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)

    # Frame for buttons
    button_frame = ctk.CTkFrame(root, corner_radius=10)
    button_frame.pack(pady=10, padx=20, fill="x")

    # Start Recording Button
    start_button = ctk.CTkButton(
        button_frame,
        text="Start Recording",
        image=start_icon,
        compound="left",
        command=lambda: start_recording_thread(add_more=False),
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    start_button.grid(row=0, column=0, padx=10, pady=10)

    # Pause Recording Button --- New Feature: Pause Recording ---
    pause_button = ctk.CTkButton(
        button_frame,
        text="Pause Recording",
        image=None,  # Optionally, add an icon for pause
        compound="left",
        command=lambda: toggle_pause_recording(),
        width=150,
        height=40,
        font=("Helvetica", 12),
        state="disabled"  # Initially disabled
    )
    pause_button.grid(row=0, column=1, padx=10, pady=10)

    # Stop Recording Button
    stop_button = ctk.CTkButton(
        button_frame,
        text="Stop Recording",
        image=stop_icon,
        compound="left",
        command=stop_recording,
        width=150,
        height=40,
        font=("Helvetica", 12),
        state="disabled"  # Initially disabled
    )
    stop_button.grid(row=0, column=2, padx=10, pady=10)

    # Add More Button
    add_more_main_button = ctk.CTkButton(
        button_frame,
        text="Add More",
        image=add_more_icon,
        compound="left",
        command=add_more_response,
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    add_more_main_button.grid(row=0, column=3, padx=10, pady=10)

    # Skip Button
    skip_button = ctk.CTkButton(
        button_frame,
        text="Skip",
        image=skip_icon,
        compound="left",
        command=skip_question_func,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    skip_button.grid(row=0, column=4, padx=10, pady=10)

    # Previous Button
    prev_button = ctk.CTkButton(
        button_frame,
        text="Previous",
        image=prev_icon,
        compound="left",
        command=prev_question_func,
        width=120,
        height=40,
        font=("Helvetica", 12)
    )
    prev_button.grid(row=0, column=5, padx=10, pady=10)

    # Next Button
    next_button = ctk.CTkButton(
        button_frame,
        text="Next",
        image=next_icon,
        compound="left",
        command=next_question_func,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    next_button.grid(row=0, column=6, padx=10, pady=10)

    # Save Resume Button
    save_button = ctk.CTkButton(
        button_frame,
        text="Save Resume",
        image=save_icon,
        compound="left",
        command=save_resume,
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    save_button.grid(row=0, column=7, padx=10, pady=10)

    # Generate Formatted Resume Button
    generate_button = ctk.CTkButton(
        button_frame,
        text="Generate Formatted Resume",
        image=save_icon,  # Reusing save icon, consider adding a different icon
        compound="left",
        command=generate_and_save_formatted_resume,
        width=220,
        height=40,
        font=("Helvetica", 12)
    )
    generate_button.grid(row=0, column=8, padx=10, pady=10)

    # Status Label
    status_label = ctk.CTkLabel(
        root,
        text="Status: Ready",
        wraplength=760,
        font=("Helvetica", 14, "italic")
    )
    status_label.pack(pady=10, padx=20, anchor="w")

    # Label to display transcription
    transcribed_label = ctk.CTkLabel(
        root,
        text="Transcription: ",
        wraplength=760,
        font=("Helvetica", 12)
    )
    transcribed_label.pack(pady=5, padx=20, anchor="w")

    # Decision Frame
    decision_frame = ctk.CTkFrame(root, corner_radius=10)
    # Decision Frame Buttons
    accept_button = ctk.CTkButton(
        decision_frame,
        text="Accept",
        image=accept_icon,
        compound="left",
        command=accept_response,
        width=120,
        height=40,
        font=("Helvetica", 12)
    )
    accept_button.pack(side="left", padx=10, pady=10)

    redo_button = ctk.CTkButton(
        decision_frame,
        text="Redo",
        image=redo_icon,
        compound="left",
        command=redo_response,
        width=120,
        height=40,
        font=("Helvetica", 12)
    )
    redo_button.pack(side="left", padx=10, pady=10)

    add_more_button = ctk.CTkButton(
        decision_frame,
        text="Add More",
        image=add_more_icon,
        compound="left",
        command=add_more_response,
        width=120,
        height=40,
        font=("Helvetica", 12)
    )
    add_more_button.pack(side="left", padx=10, pady=10)
    
    # Pause Recording Button --- Updated to use single icon and color changes ---
    pause_button = ctk.CTkButton(
        button_frame,
        text="Pause Recording",
        image=pause_icon,  # Assign the single pause icon
        compound="left",
        command=lambda: toggle_pause_recording(),
        width=150,
        height=40,
        font=("Helvetica", 12),
        state="disabled",  # Initially disabled
        fg_color="green"  # Green indicates active recording
    )
    pause_button.grid(row=0, column=1, padx=10, pady=10)

    # Resume Preview Textbox
    resume_preview_label = ctk.CTkLabel(
        root,
        text="Resume Preview:",
        font=("Helvetica", 16, "bold")
    )
    resume_preview_label.pack(pady=(20, 5), padx=20, anchor="w")

    resume_preview_textbox = ctk.CTkTextbox(
        root,
        width=760,
        height=300,
        wrap="word",
        font=("Helvetica", 12)
    )
    resume_preview_textbox.pack(pady=5, padx=20)
    resume_preview_textbox.configure(state="disabled")  # Make it read-only

    # Initialize the first question
    update_question()

# Start the application
show_start_page()

# Start the GUI event loop
root.mainloop()
