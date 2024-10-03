import customtkinter as ctk
import os
import pyaudio
import wave
import tempfile
import threading
import time
import requests
from tkinter import messagebox
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Set your OpenAI API key from the .env file
openai_api_key = os.getenv('OPENAI_API_KEY')

# Define the list of questions
questions = [
    "Please say your name.",
    "Please provide your contact number.",
    "Please provide your email address.",
    "Please provide your address.",
    "Please describe yourself with personal descriptions separated by commas.",
    "Please list your skills separated by commas.",
    "Please list your certifications and training separated by commas.",
    "Please list your professional achievements separated by commas.",
    "Please describe your prior workplace.",
    "Please describe your prior education institution and dates.",
    "Please describe your current education institution and dates.",
    "Please list your interests separated by commas.",
    "Please describe your extracurricular activities separated by commas and elaboration.",
    "Please describe your volunteer experience separated by commas and elaboration.",
    "Please list your professional associations separated by commas."
]

# Initialize global variables
current_question = 0
transcribed_responses = {}
reworded_responses = {}

# Threading events
stop_recording_event = threading.Event()

# Function to update the status label
def update_status(message):
    status_label.configure(text=f"Status: {message}")

# Function to reword text using OpenAI GPT via API
def reword_text(text):
    try:
        update_status("Rewording text...")
        prompt = f"Reword the following for better grammar and professional tone:\n\n{text}"
        api_url = 'https://api.openai.com/v1/chat/completions'

        headers = {
            'Authorization': f'Bearer {openai_api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 150,
            "n": 1,
            "temperature": 0.7
        }

        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        reworded = result['choices'][0]['message']['content'].strip()
        update_status("Rewording completed.")
        return reworded
    except Exception as e:
        messagebox.showerror("Error", f"Rewording failed: {e}")
        update_status("Ready")
        return text

# Function to handle recording and transcribing
def recording_thread_function():
    global transcribed_responses, reworded_responses

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
        update_status("Ready")
        return False

    frames = []

    print("Recording...")
    update_status("Recording...")

    while not stop_recording_event.is_set():
        try:
            data = stream.read(CHUNK)
            frames.append(data)
        except Exception as e:
            messagebox.showerror("Error", f"Error while recording: {e}")
            break

    print("Finished recording.")
    update_status("Processing transcription...")

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

    # After recording is stopped, reword the transcription
    reworded = reword_text(transcription_text)

    # Save responses
    current_q = questions[current_question]
    transcribed_responses[current_q] = transcription_text
    reworded_responses[current_q] = reworded

    # Schedule GUI updates
    root.after(0, update_reworded_label, reworded)
    root.after(0, update_resume_preview)
    root.after(0, enable_buttons_after_recording)
    root.after(0, update_status, "Ready")

# Function to start recording in a new thread
def start_recording_thread():
    stop_recording_event.clear()
    # Disable buttons during recording
    start_button.configure(state="disabled")
    stop_button.configure(state="normal")
    next_button.configure(state="disabled")
    prev_button.configure(state="disabled")
    save_button.configure(state="disabled")
    # Update labels to indicate recording
    transcribed_label.configure(text="Transcription: Recording...")
    reworded_label.configure(text="Reworded: ")
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

# Function to re-enable buttons after recording
def enable_buttons_after_recording():
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")
    next_button.configure(state="normal")
    prev_button.configure(state="normal")
    save_button.configure(state="normal")

# Function to update the transcription label
def update_transcription_label(transcription_text):
    transcribed_label.configure(text=f"Transcription: {transcription_text}")

# Function to update the reworded label
def update_reworded_label(reworded_text):
    reworded_label.configure(text=f"Reworded: {reworded_text}")

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

    # Update transcription and reworded labels if responses exist
    if question in transcribed_responses:
        transcribed_label.configure(text=f"Transcription: {transcribed_responses[question]}")
    else:
        transcribed_label.configure(text="Transcription: ")

    if question in reworded_responses:
        reworded_label.configure(text=f"Reworded: {reworded_responses[question]}")
    else:
        reworded_label.configure(text="Reworded: ")

# Function to generate resume text from responses
def generate_resume_text():
    # Define the resume sections based on the provided prompt
    resume_sections = {
        "Name": reworded_responses.get(questions[0], ""),
        "Contact Number": reworded_responses.get(questions[1], ""),
        "Email Address": reworded_responses.get(questions[2], ""),
        "Address": reworded_responses.get(questions[3], ""),
        "Professional Summary": reworded_responses.get(questions[4], ""),
        "Skills": reworded_responses.get(questions[5], ""),
        "Certifications and Training": reworded_responses.get(questions[6], ""),
        "Professional Achievements": reworded_responses.get(questions[7], ""),
        "Work Experience": reworded_responses.get(questions[8], ""),
        "Education": f"{reworded_responses.get(questions[9], '')}\n{reworded_responses.get(questions[10], '')}",
        "Interests": reworded_responses.get(questions[11], ""),
        "Extracurricular Activities": reworded_responses.get(questions[12], ""),
        "Volunteer Experience": reworded_responses.get(questions[13], ""),
        "Professional Associations": reworded_responses.get(questions[14], ""),
        "References": "Available upon request."
    }

    # Format the resume text
    resume_text = f"{resume_sections['Name']}\n"
    resume_text += f"{resume_sections['Contact Number']}\n"
    resume_text += f"{resume_sections['Email Address']}\n"
    resume_text += f"{resume_sections['Address']}\n\n"

    resume_text += "Professional Summary\n"
    resume_text += f"{resume_sections['Professional Summary']}\n\n"

    resume_text += "Skills\n"
    skills = resume_sections['Skills'].split(',')
    for skill in skills:
        resume_text += f"- {skill.strip()}\n"
    resume_text += "\n"

    resume_text += "Certifications and Training\n"
    certifications = resume_sections['Certifications and Training'].split(',')
    for cert in certifications:
        resume_text += f"- {cert.strip()}\n"
    resume_text += "\n"

    resume_text += "Professional Achievements\n"
    achievements = resume_sections['Professional Achievements'].split(',')
    for ach in achievements:
        resume_text += f"- {ach.strip()}\n"
    resume_text += "\n"

    resume_text += "Work Experience\n"
    resume_text += f"{resume_sections['Work Experience']}\n\n"

    resume_text += "Education\n"
    resume_text += f"{resume_sections['Education']}\n\n"

    resume_text += "Interests\n"
    interests = resume_sections['Interests'].split(',')
    for interest in interests:
        resume_text += f"- {interest.strip()}\n"
    resume_text += "\n"

    resume_text += "Extracurricular Activities\n"
    resume_text += f"{resume_sections['Extracurricular Activities']}\n\n"

    resume_text += "Volunteer Experience\n"
    resume_text += f"{resume_sections['Volunteer Experience']}\n\n"

    resume_text += "Professional Associations\n"
    associations = resume_sections['Professional Associations'].split(',')
    for assoc in associations:
        resume_text += f"- {assoc.strip()}\n"
    resume_text += "\n"

    resume_text += "References\n"
    resume_text += f"{resume_sections['References']}\n"

    return resume_text

# Function to update the resume preview textbox
def update_resume_preview():
    resume_text = generate_resume_text()
    resume_preview_textbox.configure(state="normal")
    resume_preview_textbox.delete("1.0", "end")
    resume_preview_textbox.insert("end", resume_text)
    resume_preview_textbox.configure(state="disabled")

# Function to save the resume to a text file
def save_resume():
    resume_text = generate_resume_text()
    try:
        with open('generated_resume.txt', 'w', encoding='utf-8') as f:
            f.write(resume_text)
        messagebox.showinfo("Success", "Your resume has been saved as 'generated_resume.txt'.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save resume: {e}")

# GUI Setup using customtkinter
ctk.set_appearance_mode("System")  # Options: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue" (default), "green", "dark-blue"

root = ctk.CTk()
root.title("Voice-Powered Resume Generator")
root.geometry("800x700")

# Frame for question and recording
question_frame = ctk.CTkFrame(root)
question_frame.pack(pady=10, padx=20, fill="x")

# Label to display the current question
question_label = ctk.CTkLabel(question_frame, text="", wraplength=760, font=("Arial", 14))
question_label.pack(pady=10)

# Frame for buttons
button_frame = ctk.CTkFrame(root)
button_frame.pack(pady=10, padx=20, fill="x")

# Start Recording Button
start_button = ctk.CTkButton(button_frame, text="Start Recording", command=start_recording_thread)
start_button.pack(side="left", padx=10, pady=10)

# Stop Recording Button
stop_button = ctk.CTkButton(button_frame, text="Stop Recording", command=stop_recording)
stop_button.pack(side="left", padx=10, pady=10)
stop_button.configure(state="disabled")  # Initially disabled

# Previous Button
prev_button = ctk.CTkButton(button_frame, text="Previous", command=prev_question_func)
prev_button.pack(side="left", padx=10, pady=10)

# Next Button
next_button = ctk.CTkButton(button_frame, text="Next", command=next_question_func)
next_button.pack(side="left", padx=10, pady=10)

# Save Resume Button
save_button = ctk.CTkButton(button_frame, text="Save Resume", command=save_resume)
save_button.pack(side="right", padx=10, pady=10)

# Status Label
status_label = ctk.CTkLabel(root, text="Status: Ready", wraplength=760, font=("Arial", 12, "italic"))
status_label.pack(pady=5, padx=20, anchor="w")

# Labels to display transcription and reworded response
transcribed_label = ctk.CTkLabel(root, text="Transcription: ", wraplength=760, font=("Arial", 12))
transcribed_label.pack(pady=5, padx=20, anchor="w")

reworded_label = ctk.CTkLabel(root, text="Reworded: ", wraplength=760, font=("Arial", 12, "bold"))
reworded_label.pack(pady=5, padx=20, anchor="w")

# Resume Preview Textbox
resume_preview_label = ctk.CTkLabel(root, text="Resume Preview:", font=("Arial", 14))
resume_preview_label.pack(pady=10, padx=20, anchor="w")

resume_preview_textbox = ctk.CTkTextbox(root, width=760, height=250, wrap="word")
resume_preview_textbox.pack(pady=5, padx=20)
resume_preview_textbox.configure(state="disabled")  # Make it read-only

# Initialize the first question
update_question()

# Start the GUI event loop
root.mainloop()
