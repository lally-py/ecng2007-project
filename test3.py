# Enhance the Voice Walkthrough Experience:

# Implement continuous listening with Voice Activity Detection (VAD) to stop recording only after 5 seconds of silence, rather than using fixed recording intervals.
# Allow users to skip introductory instructions after hearing them once, with the option to prompt the instructions again if needed.
# Add an option to adjust the speech rate and tone of the text-to-speech engine for a more personalized experience.
# Improve Audio Quality and Transcription Accuracy:

# Apply noise reduction and audio filtering techniques to enhance the clarity of the recorded audio before transcription.
# Experiment with different Whisper model parameters or add a language model selection option for improved accuracy in different languages or accents.
# Simplify the Workflow:

# Perform all text rewording and formatting at the final resume generation stage, allowing users to review raw inputs before processing.
# Add an "Undo" feature for users to revert to previous answers if they accidentally confirm an incorrect response.
# Optimize UI and User Experience:

# Make the UI more responsive by displaying visual cues (e.g., loading indicators) during lengthy operations like transcription or generating the resume.
# Improve accessibility by adding keyboard shortcuts for navigation and common actions (e.g., starting/stopping recording).
# Provide feedback when a user attempts to perform an invalid action, such as trying to add more content to an unanswered question.
# Error Handling and User Feedback:

# Implement more detailed error messages and logging for debugging purposes. Display user-friendly notifications when network or API issues occur.
# Introduce a retry mechanism for API calls that fail due to temporary issues, instead of immediately showing an error message.
# Code Optimization and Maintainability:

# Refactor duplicated functions (e.g., listen_for_command appearing multiple times) to use a single, shared function.
# Use configuration files (e.g., JSON or YAML) for managing questions, making it easier to add, remove, or modify questions without changing the code.
# Modularize the code by separating voice processing, UI components, and API interactions into different files or classes.
# Testing and Debugging Improvements:

# Add unit tests for key functions, particularly the transcription and resume generation processes, to catch potential bugs.
# Implement logging for tracking the flow of the program, especially during voice commands and responses.
# Add New Features:

# Allow users to upload an existing resume and use the tool to improve or expand upon it.
# Provide an option to export the resume in various formats (e.g., PDF, Word).
# Introduce a "pause recording" feature in addition to start/stop, for more flexibility during the voice walkthrough.
# User Data Management:

# Implement a feature to autosave user responses at intervals, preventing data loss if the program crashes.
# Add a "Clear Data" button that allows users to restart the questionnaire from scratch without manually deleting previous responses.
# These improvements can make the program more robust, user-friendly, and efficient while providing a better experience for users.

import customtkinter as ctk
from tkinter import messagebox
import os
import pyaudio
import wave
import tempfile
import threading
import requests
import pyttsx3
import speech_recognition as sr
import openai
from PIL import Image
import whisper
import numpy as np
import sounddevice as sd
import time
import io
import webrtcvad
import collections
from dotenv import load_dotenv
import json
import logging
import noisereduce as nr

# Load environment variables from the .env file
load_dotenv()

# Set your OpenAI API key from the .env file
openai_api_key = os.getenv('OPENAI_API_KEY')

# Initialize logging
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load questions and field mapping from JSON file
with open('questions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    questions = data['questions']
    field_mapping = data['field_mapping']

# Initialize global variables
current_question = 0
transcribed_responses = {}
responses_history = []
add_more_flag = False  # Flag to indicate if we are adding more to the response
stop_recording_event = threading.Event()

# Initialize speech engine and settings
engine = pyttsx3.init()
speech_rate = 200  # Default speech rate
engine.setProperty('rate', speech_rate)
voices = engine.getProperty('voices')
current_voice = voices[0]
engine.setProperty('voice', current_voice.id)
current_voice_name = current_voice.name

# Initialize transcription language
transcription_language = 'English'
language_code_mapping = {
    'English': 'en',
    'Spanish': 'es',
    'French': 'fr',
    'German': 'de',
    'Chinese': 'zh'
}

# Function to update the status label
def update_status(message):
    if 'status_label' in globals():
        status_label.configure(text=f"Status: {message}")
    logging.info(message)

# Function to handle recording and transcribing with VAD
def listen_and_transcribe_with_whisper():
    CHUNK_DURATION_MS = 30  # Duration of a chunk in milliseconds
    SAMPLE_RATE = 16000  # Sample rate in Hz
    CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # Chunk size in samples
    FORMAT = pyaudio.paInt16  # 16-bit int sampling
    CHANNELS = 1  # Mono audio

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
    logging.info("Listening... Please speak now.")

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
                    logging.info("Silence detected. Stopping recording.")
                    break
                frames.append(frame)  # Optionally include silence frames
    except Exception as e:
        messagebox.showerror("Error", f"Error during recording: {e}")
        logging.error(f"Error during recording: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    root.after(0, update_status, "Transcribing response...")
    logging.info("Transcribing response...")

    # Process and reduce noise
    audio_data = b''.join(frames)
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    reduced_noise = nr.reduce_noise(y=audio_array, sr=SAMPLE_RATE)
    processed_audio_data = reduced_noise.tobytes()

    temp_filename = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            wf = wave.open(tmp_file.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(processed_audio_data)
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
                    'file': audio_file
                }
                data = {
                    'model': 'whisper-1',
                    'language': language_code_mapping.get(transcription_language, 'en')
                }
                response = make_api_call_with_retry(api_url, headers, data, files=files)
                result = response.json()
                transcription_text = result['text'].strip()
        except Exception as e:
            error_message = str(e)
            messagebox.showerror("Error", f"Transcription failed: {error_message}")
            logging.error(f"Transcription failed: {error_message}")
            transcription_text = ""
    finally:
        if temp_filename:
            os.unlink(temp_filename)  # Remove the temp file

    return transcription_text

# Function to listen for voice commands
def listen_for_command(recognizer, microphone):
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            logging.info("Listening for command...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        command = recognizer.recognize_google(audio)
        logging.info(f"Command recognized: {command}")
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
        messagebox.showerror("Error", f"Could not request results from Speech Recognition service; {e}")
        logging.error(f"Speech Recognition service error: {e}")
        return None

# Function to perform the voice-assisted walkthrough
def voice_walkthrough():
    global transcribed_responses, engine
    engine.setProperty('rate', speech_rate)
    engine.setProperty('voice', current_voice.id)

    initial_instructions = (
        "You will be asked a series of questions to build your resume. "
        "After each question, please provide your response. "
        "When you are finished speaking, simply stop talking, and I will process your response. "
        "After your response, I will read it back to you. "
        "If it is correct, please say 'yes'. "
        "If it is incorrect, please say 'no' to redo your response. "
        "Let's begin."
    )

    # Provide initial instructions with option to skip
    engine.say("Welcome to the voice-assisted resume generator.")
    engine.say("Would you like to hear the introductory instructions?")
    engine.runAndWait()

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    response = listen_for_command(recognizer, microphone)
    if response is not None and 'no' in response.lower():
        engine.say("Okay, skipping the introductory instructions.")
        engine.runAndWait()
    else:
        engine.say(initial_instructions)
        engine.runAndWait()

    for idx, question in enumerate(questions):
        response_recorded = False
        while not response_recorded:
            # Update GUI with current question
            root.after(0, update_question_voice_mode, idx)
            root.after(0, update_status, f"Asking Question {idx+1}/{len(questions)}")
            logging.info(f"Asking Question {idx+1}/{len(questions)}")

            # Speak the question
            engine.say(question)
            engine.runAndWait()

            # Record and transcribe the user's response
            transcription_text = listen_and_transcribe_with_whisper()

            if transcription_text is None or transcription_text.strip() == "":
                engine.say("I didn't catch that. Let's try again.")
                engine.runAndWait()
                continue  # Restart the question

            # Read back the response
            engine.say("You said:")
            engine.say(transcription_text)
            engine.runAndWait()

            # Update the transcription label
            root.after(0, update_transcription_label, transcription_text)

            # Confirmation loop
            confirmation_received = False
            while not confirmation_received:
                # Ask if the response is correct
                engine.say("Is this correct? Please say 'yes' to confirm or 'no' to try again.")
                engine.runAndWait()

                # Listen for confirmation
                confirmation = listen_for_command(recognizer, microphone)
                if confirmation is not None and 'yes' in confirmation.lower():
                    # Save the response
                    responses_history.append(transcribed_responses.copy())
                    transcribed_responses[questions[idx]] = transcription_text
                    response_recorded = True
                    confirmation_received = True
                    root.after(0, update_resume_preview)
                elif confirmation is not None and 'no' in confirmation.lower():
                    engine.say("Let's try again.")
                    engine.runAndWait()
                    confirmation_received = True
                else:
                    engine.say("I didn't understand your response. Please say 'yes' or 'no'.")
                    engine.runAndWait()

    # After all questions are done
    root.after(0, update_status, "Voice Walkthrough Completed")
    logging.info("Voice Walkthrough Completed")
    generate_and_save_formatted_resume()
    engine.say("Voice walkthrough completed. Your formatted resume has been generated and saved.")
    engine.runAndWait()

# Function to update the question label in voice mode
def update_question_voice_mode(idx):
    question = questions[idx]
    question_label.configure(text=f"Question {idx + 1}/{len(questions)}:\n{question}")
    progress = (idx + 1) / len(questions)
    progress_bar.set(progress)
    if question in transcribed_responses and transcribed_responses[question]:
        transcribed_label.configure(text=f"Transcription: {transcribed_responses[question]}")
    else:
        transcribed_label.configure(text="Transcription: ")
    update_resume_preview()

# Function to update the transcription label
def update_transcription_label(transcription_text):
    transcribed_label.configure(text=f"Transcription: {transcription_text}")
    update_resume_preview()

# Function to make API call with retry
def make_api_call_with_retry(url, headers, data, files=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            if files:
                response = requests.post(url, headers=headers, data=data, files=files)
            else:
                response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt < max_retries -1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise e

# Function to start recording in a new thread
def start_recording_thread(add_more=False):
    global add_more_flag
    stop_recording_event.clear()
    add_more_flag = add_more
    hide_decision_frame()
    disable_buttons_for_recording()
    transcribed_label.configure(text="Transcription: Recording...")
    recording_thread = threading.Thread(target=recording_thread_function)
    recording_thread.start()

# Function to handle recording and transcribing
def recording_thread_function():
    global transcribed_responses, add_more_flag

    transcription_text = listen_and_transcribe_with_whisper()

    root.after(0, update_transcription_label, transcription_text)
    root.after(0, update_add_more_button_state)

    current_q = questions[current_question]
    responses_history.append(transcribed_responses.copy())
    if add_more_flag:
        transcribed_responses[current_q] += " " + transcription_text if current_q in transcribed_responses else transcription_text
    else:
        transcribed_responses[current_q] = transcription_text

    add_more_flag = False

    root.after(0, update_resume_preview)
    root.after(0, enable_buttons_after_recording)
    root.after(0, update_status, "Ready")
    root.after(0, show_decision_frame)

# Function to stop recording
def stop_recording():
    stop_recording_event.set()
    transcribed_label.configure(text="Transcription: Processing...")
    update_status("Processing transcription...")
    stop_button.configure(state="disabled")

# Function to disable buttons during recording
def disable_buttons_for_recording():
    start_button.configure(state="disabled")
    stop_button.configure(state="normal")
    next_button.configure(state="disabled")
    prev_button.configure(state="disabled")
    save_button.configure(state="disabled")
    skip_button.configure(state="disabled")
    add_more_main_button.configure(state="disabled")

# Function to re-enable buttons after recording
def enable_buttons_after_recording():
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")
    next_button.configure(state="normal")
    prev_button.configure(state="normal")
    save_button.configure(state="normal")
    skip_button.configure(state="normal")
    update_add_more_button_state()

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
    if question in transcribed_responses and transcribed_responses[question]:
        transcribed_label.configure(text=f"Transcription: {transcribed_responses[question]}")
    else:
        transcribed_label.configure(text="Transcription: ")
    update_add_more_button_state()
    progress = (current_question + 1) / len(questions)
    progress_bar.set(progress)

# Function to generate resume text from responses
def generate_resume_text():
    if not any(transcribed_responses.values()):
        return ""
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

    resume_text = ""
    significant_sections_added = 0

    def add_section(title, content, is_significant=False):
        nonlocal resume_text, significant_sections_added
        if content.strip():
            resume_text += f"{title}:\n{content}\n\n"
            if is_significant:
                significant_sections_added += 1

    if resume_sections["Name"]:
        resume_text += f"Name:\n{resume_sections['Name']}\n\n"

    if resume_sections["Contact Number"]:
        resume_text += f"Contact Number:\n{resume_sections['Contact Number']}\n\n"
    if resume_sections["Email Address"]:
        resume_text += f"Email Address:\n{resume_sections['Email Address']}\n\n"
    if resume_sections["Address"]:
        resume_text += f"Address:\n{resume_sections['Address']}\n\n"

    add_section("Professional Summary", resume_sections["Professional Summary"], is_significant=True)

    if resume_sections["Skills"]:
        skills_list = [skill.strip() for skill in resume_sections["Skills"].split(',') if skill.strip()]
        if skills_list:
            resume_text += "Skills:\n"
            for skill in skills_list:
                resume_text += f"- {skill}\n"
            resume_text += "\n"
            significant_sections_added += 1

    if resume_sections["Certifications and Training"]:
        certs_list = [cert.strip() for cert in resume_sections["Certifications and Training"].split(',') if cert.strip()]
        if certs_list:
            resume_text += "Certifications and Training:\n"
            for cert in certs_list:
                resume_text += f"- {cert}\n"
            resume_text += "\n"
            significant_sections_added += 1

    if resume_sections["Professional Achievements"]:
        achievements_list = [ach.strip() for ach in resume_sections["Professional Achievements"].split(',') if ach.strip()]
        if achievements_list:
            resume_text += "Professional Achievements:\n"
            for ach in achievements_list:
                resume_text += f"- {ach}\n"
            resume_text += "\n"
            significant_sections_added += 1

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

    if resume_sections["Interests"]:
        interests_list = [interest.strip() for interest in resume_sections["Interests"].split(',') if interest.strip()]
        if interests_list:
            resume_text += "Interests:\n"
            for interest in interests_list:
                resume_text += f"- {interest}\n"
            resume_text += "\n"
            significant_sections_added += 1

    add_section("Extracurricular Activities", resume_sections["Extracurricular Activities"], is_significant=True)
    add_section("Volunteer Experience", resume_sections["Volunteer Experience"], is_significant=True)

    if resume_sections["Professional Associations"]:
        associations_list = [assoc.strip() for assoc in resume_sections["Professional Associations"].split(',') if assoc.strip()]
        if associations_list:
            resume_text += "Professional Associations:\n"
            for assoc in associations_list:
                resume_text += f"- {assoc}\n"
            resume_text += "\n"
            significant_sections_added += 1

    if significant_sections_added > 0:
        resume_text += f"References:\n{resume_sections['References']}\n"

    return resume_text.strip()

# Function to update the resume preview textbox
def update_resume_preview():
    resume_text = generate_resume_text()
    resume_preview_textbox.configure(state="normal")
    resume_preview_textbox.delete("1.0", "end")
    resume_preview_textbox.insert("end", resume_text)
    resume_preview_textbox.configure(state="disabled")
    save_responses_to_file()

# Function to save the responses to a text file
def save_responses_to_file():
    try:
        with open('responses.txt', 'w', encoding='utf-8') as f:
            for question in questions:
                field_name = field_mapping.get(question, question)
                response = transcribed_responses.get(question, "")
                f.write(f"{field_name} - {response}\n")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save responses: {e}")
        logging.error(f"Failed to save responses: {e}")

# Function to save the resume to a text file and generate formatted resume via ChatGPT
def save_resume():
    resume_text = generate_resume_text()
    try:
        with open('generated_resume.txt', 'w', encoding='utf-8') as f:
            f.write(resume_text)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save basic resume: {e}")
        logging.error(f"Failed to save basic resume: {e}")
        return
    formatted_resume = generate_formatted_resume()
    if formatted_resume:
        try:
            with open('formatted_resume.txt', 'w', encoding='utf-8') as f:
                f.write(formatted_resume)
            messagebox.showinfo("Success", "Your formatted resume has been saved as 'formatted_resume.txt'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save formatted resume: {e}")
            logging.error(f"Failed to save formatted resume: {e}")
    else:
        messagebox.showerror("Error", "Failed to generate formatted resume via ChatGPT.")
        logging.error("Failed to generate formatted resume via ChatGPT.")

# Function to generate formatted resume via ChatGPT
def generate_formatted_resume():
    try:
        input_section = ""
        for question in questions:
            field_name = field_mapping.get(question, question)
            response = transcribed_responses.get(question, "")
            input_section += f"{field_name} - {response}\n"

        full_prompt = f"""[Resume Generation Prompt

Input:

{input_section}

Instructions:

Use the provided details to generate a resume in the following format. Ensure clarity and specificity in each section based on the details given. Reword and refine the content to maintain a professional tone and proper grammar.

Output Format:

[NAME]
[CONTACT NUMBER]
[EMAIL ADDRESS]
[ADDRESS]

Professional Summary
Create a 4-line professional summary using the words from [PERSONAL DESCRIPTIONS SEPARATED BY COMMAS]. The summary should highlight key strengths, qualities, and professional attributes, including career goals and how past experiences align with industry trends.

Skills
List the skills mentioned in [SKILLS SEPARATED BY COMMAS] in bullet points or a similar format. Include subcategories if applicable.

Certifications and Training
List relevant certifications, courses, and workshops mentioned in [CERTIFICATIONS AND TRAINING SEPARATED BY COMMAS].

Professional Achievements
Highlight specific accomplishments or awards mentioned in [PROFESSIONAL ACHIEVEMENTS SEPARATED BY COMMAS].

Work Experience
Mention the name of the institution from [PRIOR WORK PLACE]. Elaborate on the position described in [DESCRIPTION OF POSITION], including key responsibilities and achievements. Include details of key projects from [KEY PROJECTS SEPARATED BY COMMAS].

Education

[PRIOR EDUCATION INSTITUTION AND DATES OF ATTENDANCE]
[CURRENT EDUCATION INSTITUTION AND DATES OF ATTENDANCE]

Interests
List the interests mentioned in [INTERESTS SEPARATED BY COMMAS] in bullet points or a similar format.

Extracurricular Activities
List and elaborate on the extracurricular activities mentioned in [EXTRACURRICULAR ACTIVITIES SEPARATED BY COMMAS AND ELABORATION]. Provide details on roles, contributions, and any relevant outcomes.

Volunteer Experience
Include volunteer work mentioned in [VOLUNTEER EXPERIENCE SEPARATED BY COMMAS AND ELABORATION], detailing roles, contributions, and impact.

Professional Associations
Mention memberships in professional organizations or networks relevant to your field from [PROFESSIONAL ASSOCIATIONS SEPARATED BY COMMAS].

References
Available upon request.

Note: The input provided above should be used to generate the resume in the specified format.]"""

        api_url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {openai_api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 2000,
            "n": 1,
            "temperature": 0.7
        }
        response = make_api_call_with_retry(api_url, headers, data)
        result = response.json()
        formatted_resume = result['choices'][0]['message']['content'].strip()
        return formatted_resume

    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate formatted resume: {e}")
        logging.error(f"Failed to generate formatted resume: {e}")
        return None

# Function to generate and save the formatted resume via ChatGPT
def generate_and_save_formatted_resume():
    update_status("Generating formatted resume...")
    logging.info("Generating formatted resume...")
    try:
        formatted_resume = generate_formatted_resume()
        if formatted_resume:
            try:
                with open('formatted_resume.txt', 'w', encoding='utf-8') as f:
                    f.write(formatted_resume)
                messagebox.showinfo("Success", "Your formatted resume has been saved as 'formatted_resume.txt'.")
                logging.info("Formatted resume saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save formatted resume: {e}")
                logging.error(f"Failed to save formatted resume: {e}")
        else:
            messagebox.showerror("Error", "Failed to generate formatted resume via ChatGPT.")
            logging.error("Failed to generate formatted resume via ChatGPT.")
    finally:
        update_status("Ready")

# Function to skip the current question
def skip_question_func():
    current_q = questions[current_question]
    responses_history.append(transcribed_responses.copy())
    transcribed_responses[current_q] = ""
    update_resume_preview()
    update_add_more_button_state()
    next_question_func()

# Function to show decision frame
def show_decision_frame():
    decision_frame.pack(pady=10, padx=20, fill="x")
    start_button.configure(state="disabled")
    stop_button.configure(state="disabled")
    next_button.configure(state="disabled")
    prev_button.configure(state="disabled")
    save_button.configure(state="disabled")
    skip_button.configure(state="disabled")
    add_more_main_button.configure(state="disabled")

# Function to hide decision frame
def hide_decision_frame():
    decision_frame.pack_forget()
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")
    next_button.configure(state="normal")
    prev_button.configure(state="normal")
    save_button.configure(state="normal")
    skip_button.configure(state="normal")
    update_add_more_button_state()

# Function when user accepts the response
def accept_response():
    hide_decision_frame()
    next_question_func()

# Function when user wants to redo the response
def redo_response():
    hide_decision_frame()
    current_q = questions[current_question]
    transcribed_responses[current_q] = ""
    update_resume_preview()
    update_add_more_button_state()
    start_recording_thread(add_more=False)

# Function when user wants to add more to the response
def add_more_response():
    hide_decision_frame()
    start_recording_thread(add_more=True)

# Function to update 'Add More' button state
def update_add_more_button_state():
    question = questions[current_question]
    if question in transcribed_responses and transcribed_responses[question].strip():
        add_more_main_button.configure(state="normal")
    else:
        add_more_main_button.configure(state="disabled")

# Function to undo the last response
def undo_response():
    if responses_history:
        transcribed_responses.clear()
        transcribed_responses.update(responses_history.pop())
        update_resume_preview()
        update_question()
        messagebox.showinfo("Undo", "The last action has been undone.")
        logging.info("Last action undone.")
    else:
        messagebox.showinfo("Undo", "No more actions to undo.")
        logging.info("No more actions to undo.")

# Function to clear all data
def clear_data():
    global transcribed_responses, responses_history
    transcribed_responses.clear()
    responses_history.clear()
    update_resume_preview()
    update_question()
    messagebox.showinfo("Clear Data", "All data has been cleared.")
    logging.info("All data has been cleared.")

# Function to open settings window
def open_settings_window():
    settings_window = ctk.CTkToplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("400x400")

    # Speech Rate Slider
    speech_rate_label = ctk.CTkLabel(settings_window, text="Speech Rate:")
    speech_rate_label.pack(pady=10)

    speech_rate_slider = ctk.CTkSlider(settings_window, from_=100, to=300, number_of_steps=20, command=update_speech_rate)
    speech_rate_slider.set(speech_rate)
    speech_rate_slider.pack(pady=10)

    # Voice Selection
    voice_label = ctk.CTkLabel(settings_window, text="Voice:")
    voice_label.pack(pady=10)

    voice_names = [voice.name for voice in voices]

    voice_option_menu = ctk.CTkOptionMenu(settings_window, values=voice_names, command=update_voice)
    voice_option_menu.set(current_voice_name)
    voice_option_menu.pack(pady=10)

    # Language Selection
    language_label = ctk.CTkLabel(settings_window, text="Transcription Language:")
    language_label.pack(pady=10)

    languages = list(language_code_mapping.keys())
    language_option_menu = ctk.CTkOptionMenu(settings_window, values=languages, command=update_language)
    language_option_menu.set(transcription_language)
    language_option_menu.pack(pady=10)

def update_speech_rate(value):
    global speech_rate
    speech_rate = int(float(value))
    engine.setProperty('rate', speech_rate)
    logging.info(f"Speech rate set to {speech_rate}")

def update_voice(voice_name):
    global current_voice_name, current_voice
    current_voice_name = voice_name
    for voice in voices:
        if voice.name == voice_name:
            current_voice = voice
            engine.setProperty('voice', voice.id)
            logging.info(f"Voice changed to {voice_name}")
            break

def update_language(selected_language):
    global transcription_language
    transcription_language = selected_language
    logging.info(f"Transcription language set to {transcription_language}")

# Autosave function
def autosave():
    save_responses_to_file()
    root.after(60000, autosave)  # Save every 60 seconds
    logging.info("Autosaved responses.")

# GUI Setup using customtkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("Resume Generator")
root.geometry("1400x800")
root.resizable(True, True)

# Load icons (Ensure the icons are in the correct path)
def load_icon(path, size=(20, 20)):
    try:
        return ctk.CTkImage(Image.open(path), size=size)
    except Exception as e:
        logging.error(f"Icon loading failed for {path}: {e}")
        return None

manual_icon = load_icon("icons/manual_icon.png")
voice_icon = load_icon("icons/voice_icon.png")
start_icon = load_icon("icons/start_icon.png")
stop_icon = load_icon("icons/stop_icon.png")
next_icon = load_icon("icons/next_icon.png")
prev_icon = load_icon("icons/prev_icon.png")
save_icon = load_icon("icons/save_icon.png")
skip_icon = load_icon("icons/skip_icon.png")
accept_icon = load_icon("icons/accept_icon.png")
redo_icon = load_icon("icons/redo_icon.png")
add_more_icon = load_icon("icons/add_more_icon.png")
settings_icon = load_icon("icons/settings_icon.png")
undo_icon = load_icon("icons/undo_icon.png")
clear_icon = load_icon("icons/clear_icon.png")

# Progress Bar
progress_bar = ctk.CTkProgressBar(root, width=400, height=20)
progress_bar.set(0)
progress_bar.pack(pady=(20, 10), padx=20)

# Function to show the start page
def show_start_page():
    start_frame = ctk.CTkFrame(root, corner_radius=10)
    start_frame.pack(pady=10, padx=20, fill="both", expand=True)

    # Welcome Image or Logo (Ensure the image exists)
    try:
        logo_image = ctk.CTkImage(Image.open("icons/logo.png"), size=(150, 150))
        logo_label = ctk.CTkLabel(start_frame, image=logo_image, text="")
        logo_label.image = logo_image
        logo_label.pack(pady=(20, 10))
    except Exception as e:
        logging.error(f"Logo loading failed: {e}")
        logo_label = ctk.CTkLabel(start_frame, text="Resume Generator", font=("Helvetica", 24, "bold"))
        logo_label.pack(pady=(20, 10))

    welcome_label = ctk.CTkLabel(start_frame, text="Welcome to the Resume Generator", font=("Helvetica", 26, "bold"))
    welcome_label.pack(pady=10)

    instruction_label = ctk.CTkLabel(start_frame, text="Please select an option to proceed", font=("Helvetica", 16))
    instruction_label.pack(pady=10)

    # Manual Walkthrough Button
    manual_button = ctk.CTkButton(
        start_frame,
        text="Manual Walkthrough",
        image=manual_icon if manual_icon else None,
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
        image=voice_icon if voice_icon else None,
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
# Function to initialize the voice GUI
def initialize_voice_gui():
    global status_label, question_label, transcribed_label, resume_preview_textbox

    voice_frame = ctk.CTkFrame(root, corner_radius=10)
    voice_frame.pack(pady=10, padx=20, fill="both", expand=True)

    status_label = ctk.CTkLabel(
        voice_frame,
        text="Status: Starting Voice Walkthrough...",
        wraplength=760,
        font=("Helvetica", 14, "italic")
    )
    status_label.pack(pady=5, padx=20, anchor="w")

    question_label = ctk.CTkLabel(
        voice_frame,
        text="",
        wraplength=760,
        font=("Helvetica", 16, "bold")
    )
    question_label.pack(pady=5, padx=20, anchor="w")

    transcribed_label = ctk.CTkLabel(
        voice_frame,
        text="Transcription: ",
        wraplength=760,
        font=("Helvetica", 12)
    )
    transcribed_label.pack(pady=5, padx=20, anchor="w")

    resume_preview_label = ctk.CTkLabel(
        voice_frame,
        text="Resume Preview:",
        font=("Helvetica", 16, "bold")
    )
    resume_preview_label.pack(pady=(10, 5), padx=20, anchor="w")

    # Scrollable Textbox
    resume_preview_frame = ctk.CTkFrame(voice_frame)
    resume_preview_frame.pack(pady=5, padx=20, fill="both", expand=True)

    resume_preview_textbox = ctk.CTkTextbox(
        resume_preview_frame,
        wrap="word",
        font=("Helvetica", 12)
    )
    resume_preview_textbox.pack(side="left", fill="both", expand=True)

    resume_preview_scrollbar = ctk.CTkScrollbar(resume_preview_frame, command=resume_preview_textbox.yview)
    resume_preview_scrollbar.pack(side="right", fill="y")
    resume_preview_textbox.configure(yscrollcommand=resume_preview_scrollbar.set)
    resume_preview_textbox.configure(state="disabled")

    # Settings Button
    settings_button = ctk.CTkButton(
        voice_frame,
        text="Settings",
        image=settings_icon if settings_icon else None,
        compound="left",
        command=open_settings_window,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    settings_button.pack(pady=10)

# Function to initialize the manual input GUI with voice recording
def initialize_manual_gui():
    global question_label, transcribed_label
    global start_button, stop_button, next_button, prev_button, save_button, skip_button, generate_button
    global status_label, resume_preview_textbox, decision_frame
    global add_more_main_button

    main_frame = ctk.CTkFrame(root, corner_radius=10)
    main_frame.pack(pady=10, padx=20, fill="both", expand=True)

    # Question Frame
    question_frame = ctk.CTkFrame(main_frame, corner_radius=10)
    question_frame.pack(pady=10, padx=20, fill="x")

    question_label = ctk.CTkLabel(
        question_frame,
        text="",
        wraplength=1000,
        font=("Helvetica", 16, "bold")
    )
    question_label.pack(anchor="w", padx=10, pady=10)

    # Button Frame
    button_frame = ctk.CTkFrame(main_frame, corner_radius=10)
    button_frame.pack(pady=10, padx=20, fill="x")

    # First Row Buttons
    start_button = ctk.CTkButton(
        button_frame,
        text="Start Recording",
        image=start_icon if start_icon else None,
        compound="left",
        command=lambda: start_recording_thread(add_more=False),
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    start_button.grid(row=0, column=0, padx=10, pady=10)

    stop_button = ctk.CTkButton(
        button_frame,
        text="Stop Recording",
        image=stop_icon if stop_icon else None,
        compound="left",
        command=stop_recording,
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    stop_button.grid(row=0, column=1, padx=10, pady=10)
    stop_button.configure(state="disabled")

    add_more_main_button = ctk.CTkButton(
        button_frame,
        text="Add More",
        image=add_more_icon if add_more_icon else None,
        compound="left",
        command=add_more_response,
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    add_more_main_button.grid(row=0, column=2, padx=10, pady=10)

    skip_button = ctk.CTkButton(
        button_frame,
        text="Skip",
        image=skip_icon if skip_icon else None,
        compound="left",
        command=skip_question_func,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    skip_button.grid(row=0, column=3, padx=10, pady=10)

    # Second Row Buttons
    prev_button = ctk.CTkButton(
        button_frame,
        text="Previous",
        image=prev_icon if prev_icon else None,
        compound="left",
        command=prev_question_func,
        width=120,
        height=40,
        font=("Helvetica", 12)
    )
    prev_button.grid(row=1, column=0, padx=10, pady=10)

    next_button = ctk.CTkButton(
        button_frame,
        text="Next",
        image=next_icon if next_icon else None,
        compound="left",
        command=next_question_func,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    next_button.grid(row=1, column=1, padx=10, pady=10)

    save_button = ctk.CTkButton(
        button_frame,
        text="Save Resume",
        image=save_icon if save_icon else None,
        compound="left",
        command=save_resume,
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    save_button.grid(row=1, column=2, padx=10, pady=10)

    generate_button = ctk.CTkButton(
        button_frame,
        text="Generate Formatted Resume",
        image=save_icon if save_icon else None,
        compound="left",
        command=generate_and_save_formatted_resume,
        width=220,
        height=40,
        font=("Helvetica", 12)
    )
    generate_button.grid(row=1, column=3, padx=10, pady=10)

    # Third Row Buttons
    undo_button = ctk.CTkButton(
        button_frame,
        text="Undo",
        image=undo_icon if undo_icon else None,
        compound="left",
        command=undo_response,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    undo_button.grid(row=2, column=0, padx=10, pady=10)

    clear_data_button = ctk.CTkButton(
        button_frame,
        text="Clear Data",
        image=clear_icon if clear_icon else None,
        compound="left",
        command=clear_data,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    clear_data_button.grid(row=2, column=1, padx=10, pady=10)

    settings_button = ctk.CTkButton(
        button_frame,
        text="Settings",
        image=settings_icon if settings_icon else None,
        compound="left",
        command=open_settings_window,
        width=100,
        height=40,
        font=("Helvetica", 12)
    )
    settings_button.grid(row=2, column=2, padx=10, pady=10)

    status_label = ctk.CTkLabel(
        main_frame,
        text="Status: Ready",
        wraplength=1000,
        font=("Helvetica", 14, "italic")
    )
    status_label.pack(pady=10, padx=20, anchor="w")

    transcribed_label = ctk.CTkLabel(
        main_frame,
        text="Transcription: ",
        wraplength=1000,
        font=("Helvetica", 12)
    )
    transcribed_label.pack(pady=5, padx=20, anchor="w")

    decision_frame = ctk.CTkFrame(main_frame, corner_radius=10)
    accept_button = ctk.CTkButton(
        decision_frame,
        text="Accept",
        image=accept_icon if accept_icon else None,
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
        image=redo_icon if redo_icon else None,
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
        image=add_more_icon if add_more_icon else None,
        compound="left",
        command=add_more_response,
        width=120,
        height=40,
        font=("Helvetica", 12)
    )
    add_more_button.pack(side="left", padx=10, pady=10)

    # Resume Preview
    resume_preview_label = ctk.CTkLabel(
        main_frame,
        text="Resume Preview:",
        font=("Helvetica", 16, "bold")
    )
    resume_preview_label.pack(pady=(20, 5), padx=20, anchor="w")

    resume_preview_frame = ctk.CTkFrame(main_frame)
    resume_preview_frame.pack(pady=5, padx=20, fill="both", expand=True)

    resume_preview_textbox = ctk.CTkTextbox(
        resume_preview_frame,
        wrap="word",
        font=("Helvetica", 12)
    )
    resume_preview_textbox.pack(side="left", fill="both", expand=True)

    resume_preview_scrollbar = ctk.CTkScrollbar(resume_preview_frame, command=resume_preview_textbox.yview)
    resume_preview_scrollbar.pack(side="right", fill="y")
    resume_preview_textbox.configure(yscrollcommand=resume_preview_scrollbar.set)
    resume_preview_textbox.configure(state="disabled")

    update_question()
    root.bind('<Control-r>', lambda event: start_recording_thread())
    root.bind('<Control-s>', lambda event: stop_recording())
    root.bind('<Control-z>', lambda event: undo_response())
    autosave()

# Start the application
show_start_page()
root.mainloop()
