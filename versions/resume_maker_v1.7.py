# Testing program without rewording at each stage, and just a final resume generation which does all the rewording and formatting.

# corrected ui bugs, and fixed text apearing in the manual mode text box for parts that were not done yet
# fixed problem where add more button would be able to be used even on questions that have not been answered yet.

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
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Set your OpenAI API key from the .env file
openai_api_key = os.getenv('OPENAI_API_KEY')

# Define the list of questions and their corresponding field names
questions = [
    "Please spell your name seperated by a space.",
    "Please provide your contact number.",
    "Please provide your email address(provide spelling if necessary).",
    "Please provide your address(provide spelling if necessary).",
    "Please describe yourself with personal descriptions separated by commas.",
    "Please list your skills separated by commas.",
    "Please list your certifications and training separated by commas.",
    "Please list your professional achievements separated by commas.",
    "Please describe your prior workplace.",
    "Please provide your job title or position in the prior workplace.",
    "Please list key projects separated by commas.",
    "Please describe your prior education institution and dates.",
    "Please describe your current education institution and dates.",
    "Please list your interests separated by commas.",
    "Please describe your extracurricular activities separated by commas and elaboration.",
    "Please describe your volunteer experience separated by commas and elaboration.",
    "Please list your professional associations separated by commas."
]

field_mapping = {
    "Please say your name.": "[NAME]",
    "Please provide your contact number.": "[CONTACT NUMBER]",
    "Please provide your email address.": "[EMAIL ADDRESS]",
    "Please provide your address.": "[ADDRESS]",
    "Please describe yourself with personal descriptions separated by commas.": "[PERSONAL DESCRIPTIONS SEPARATED BY COMMAS]",
    "Please list your skills separated by commas.": "[SKILLS SEPARATED BY COMMAS]",
    "Please list your certifications and training separated by commas.": "[CERTIFICATIONS AND TRAINING SEPARATED BY COMMAS]",
    "Please list your professional achievements separated by commas.": "[PROFESSIONAL ACHIEVEMENTS SEPARATED BY COMMAS]",
    "Please describe your prior workplace.": "[PRIOR WORK PLACE]",
    "Please provide your job title or position in the prior workplace.": "[DESCRIPTION OF POSITION]",
    "Please list key projects separated by commas.": "[KEY PROJECTS SEPARATED BY COMMAS]",
    "Please describe your prior education institution and dates.": "[PRIOR EDUCATION INSTITUTION AND DATES OF ATTENDANCE]",
    "Please describe your current education institution and dates.": "[CURRENT EDUCATION INSTITUTION AND DATES OF ATTENDANCE]",
    "Please list your interests separated by commas.": "[INTERESTS SEPARATED BY COMMAS]",
    "Please describe your extracurricular activities separated by commas and elaboration.": "[EXTRACURRICULAR ACTIVITIES SEPARATED BY COMMAS AND ELABORATION]",
    "Please describe your volunteer experience separated by commas and elaboration.": "[VOLUNTEER EXPERIENCE SEPARATED BY COMMAS AND ELABORATION]",
    "Please list your professional associations separated by commas.": "[PROFESSIONAL ASSOCIATIONS SEPARATED BY COMMAS]"
}

# Initialize global variables
current_question = 0
transcribed_responses = {}
add_more_flag = False  # Flag to indicate if we are adding more to the response

# Threading events
stop_recording_event = threading.Event()

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

                response = requests.post(api_url, headers=headers, files=files)
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
                    text = recognizer.recognize_google(audio)
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

# Function to listen for voice commands
def listen_for_command(recognizer, microphone):
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening for command...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)

        # Recognize speech using Google's speech recognition
        command = recognizer.recognize_google(audio)
        print(f"Command recognized: {command}")
        return command.lower()

    except sr.UnknownValueError:
        print("Could not understand command.")
        return None
    except sr.WaitTimeoutError:
        print("Listening timed out while waiting for command.")
        return None
    except sr.RequestError as e:
        messagebox.showerror("Error", f"Could not request results from Google Speech Recognition service; {e}")
        return None

# Function to perform the voice-assisted walkthrough
def voice_walkthrough():
    global transcribed_responses
    engine = pyttsx3.init()
    engine.setProperty('rate', 200)  # Adjust speech rate if necessary

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    idx = 0
    while idx < len(questions):
        question = questions[idx]
        question_accepted = False
        while not question_accepted:
            # Update status
            root.after(0, update_status, f"Asking Question {idx+1}/{len(questions)}")

            # Speak the question
            engine.say(question)
            engine.say("Please say your response and say 'stop recording' when you're done.")
            engine.runAndWait()

            # Listen and transcribe
            transcription_text = listen_and_transcribe(recognizer, microphone)

            if transcription_text is None:
                # If there was an error or no response, skip this question
                transcribed_responses[question] = ""
                break  # Move to next question

            # Read back the response
            engine.say("Your response is:")
            engine.say(transcription_text)
            engine.runAndWait()

            # Now listen for command
            while True:
                engine.say("If you are satisfied with this response, please say 'accept'. To redo, say 'redo'. To skip this question, say 'skip'. To finish the walkthrough, say 'finish'.")
                engine.runAndWait()

                command = listen_for_command(recognizer, microphone)
                if command is None:
                    # Could not understand command, ask again
                    engine.say("Sorry, I did not understand. Please say 'accept', 'redo', 'skip', or 'finish'.")
                    engine.runAndWait()
                    continue
                elif 'accept' in command:
                    # Save responses
                    transcribed_responses[question] = transcription_text
                    question_accepted = True
                    break  # Exit inner while loop, proceed to next question
                elif 'redo' in command:
                    # Redo the current question
                    # Continue the outer while loop to ask the question again
                    break  # Break out of inner while loop to redo question
                elif 'skip' in command or 'skip question' in command:
                    # Skip the current question
                    transcribed_responses[question] = ""
                    question_accepted = True
                    break  # Exit inner while loop, proceed to next question
                elif 'finish' in command or 'stop' in command or 'stop recording' in command:
                    # Finish the walkthrough
                    engine.say("Finishing the walkthrough.")
                    engine.runAndWait()
                    # Generate and save the formatted resume before exiting
                    root.after(0, update_status, "Voice Walkthrough Completed")
                    generate_and_save_formatted_resume()
                    engine.say("Your formatted resume has been generated and saved.")
                    engine.runAndWait()
                    return  # Exit the function
                else:
                    # Unrecognized command
                    engine.say("Sorry, I did not understand. Please say 'accept', 'redo', 'skip', or 'finish'.")
                    engine.runAndWait()
        idx += 1  # Move to the next question

    # After all questions are done
    root.after(0, update_status, "Voice Walkthrough Completed")
    # Generate and save the formatted resume
    generate_and_save_formatted_resume()
    # Inform the user
    engine.say("Voice walkthrough completed. Your formatted resume has been generated and saved.")
    engine.runAndWait()

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

            response = requests.post(api_url, headers=headers, files=files)
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
    add_more_flag = add_more
    # Hide decision frame first
    hide_decision_frame()
    # Disable buttons during recording
    disable_buttons_for_recording()
    # Update labels to indicate recording
    transcribed_label.configure(text="Transcription: Recording...")
    # Start recording thread
    recording_thread = threading.Thread(target=recording_thread_function)
    recording_thread.start()

# Function to stop recording
def stop_recording():
    stop_recording_event.set()
    # Update label to indicate processing
    transcribed_label.configure(text="Transcription: Processing...")
    update_status("Processing transcription...")
    # Disable the stop button to prevent multiple presses
    stop_button.configure(state="disabled")

# Function to disable buttons during recording
def disable_buttons_for_recording():
    start_button.configure(state="disabled")
    stop_button.configure(state="normal")
    next_button.configure(state="disabled")
    prev_button.configure(state="disabled")
    save_button.configure(state="disabled")
    skip_button.configure(state="disabled")
    add_more_main_button.configure(state="disabled")  # Disable 'Add More' button


# Function to re-enable buttons after recording
def enable_buttons_after_recording():
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")
    next_button.configure(state="normal")
    prev_button.configure(state="normal")
    save_button.configure(state="normal")
    skip_button.configure(state="normal")
    update_add_more_button_state()  # Update 'Add More' button state


# Function to update the transcription label
def update_transcription_label(transcription_text):
    transcribed_label.configure(text=f"Transcription: {transcription_text}")
    # Update 'Add More' button state
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
    try:
        # Build the Input section from transcribed responses
        input_section = ""
        for question in questions:
            field_name = field_mapping.get(question, question)
            response = transcribed_responses.get(question, "")
            input_section += f"{field_name} - {response}\n"

        # Your initial prompt
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

        # Send the prompt to the OpenAI API
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

        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        formatted_resume = result['choices'][0]['message']['content'].strip()
        return formatted_resume

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

# GUI Setup using customtkinter
ctk.set_appearance_mode("System")  # Options: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue" (default), "green", "dark-blue"

root = ctk.CTk()
root.title("Resume Generator")
root.geometry("1400x800")
root.resizable(True, True)  # Make the window resizable

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
    global status_label
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
    status_label.pack(pady=20, padx=20, anchor="w")

    # Add a placeholder or loading animation if desired
    # For simplicity, it's omitted here


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
    global start_button, stop_button, next_button, prev_button, save_button, skip_button, generate_button
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

    # Stop Recording Button
    stop_button = ctk.CTkButton(
        button_frame,
        text="Stop Recording",
        image=stop_icon,
        compound="left",
        command=stop_recording,
        width=150,
        height=40,
        font=("Helvetica", 12)
    )
    stop_button.grid(row=0, column=1, padx=10, pady=10)
    stop_button.configure(state="disabled")  # Initially disabled

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
    add_more_main_button.grid(row=0, column=2, padx=10, pady=10)

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
    skip_button.grid(row=0, column=3, padx=10, pady=10)

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
    prev_button.grid(row=0, column=4, padx=10, pady=10)

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
    next_button.grid(row=0, column=5, padx=10, pady=10)

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
    save_button.grid(row=0, column=6, padx=10, pady=10)

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
    generate_button.grid(row=0, column=7, padx=10, pady=10)

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
