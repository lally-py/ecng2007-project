import customtkinter as ctk
from tkinter import messagebox
import os
import pyaudio
import wave
import tempfile
import threading
import requests # interacts with open ai directly through http (reduces package size by making it so we dont have to use openai/whisper SDK and also allows for more customizibility in prompting)
import pyttsx3  # For text-to-speech
import speech_recognition as sr  # For real-time speech recognition
import openai  # Added for OpenAI SDK if required
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Set your OpenAI API key from the .env file
openai_api_key = os.getenv('OPENAI_API_KEY')

# Define the list of questions and their corresponding field names
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
reworded_responses = {}
add_more_flag = False  # Flag to indicate if we are adding more to the response

# Threading events
stop_recording_event = threading.Event()

# Function to update the status label
def update_status(message):
    if 'status_label' in globals():
        status_label.configure(text=f"Status: {message}")

# Function to reword text using OpenAI GPT via API
def reword_text(text):
    try:
        update_status("Rewording text...")
        prompt = f"Reword the following for better grammar and professional tone, it is meant for a resume so please keep it to the short concise answers found in a resume:\n\n{text}"
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
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.content}")
        messagebox.showerror("Error", f"HTTP error during rewording: {http_err}")
    except Exception as e:
        print(f"An error occurred: {e}")
        messagebox.showerror("Error", f"Rewording failed: {e}")
    update_status("Ready")
    return text


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
    
    
# Function to perform the voice-assisted walkthrough
def voice_walkthrough():
    global transcribed_responses, reworded_responses
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Adjust speech rate if necessary

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    for idx, question in enumerate(questions):
        # Update status
        root.after(0, update_status, f"Asking Question {idx+1}/{len(questions)}")

        # Speak the question
        engine.say(question)
        engine.say("Please say your response. Say 'stop recording' when you're done.")
        engine.runAndWait()

        # Listen and transcribe
        transcription_text = listen_and_transcribe(recognizer, microphone)

        if transcription_text is None:
            # If there was an error or no response, skip this question
            transcribed_responses[question] = ""
            reworded_responses[question] = ""
            continue

        # Reword the response
        reworded = reword_text(transcription_text)

        # Save responses
        transcribed_responses[question] = transcription_text
        reworded_responses[question] = reworded

    # After all questions are done
    root.after(0, update_status, "Voice Walkthrough Completed")
    # Generate and save the formatted resume
    generate_and_save_formatted_resume()
    # Inform the user
    engine.say("Voice walkthrough completed. Your formatted resume has been generated and saved.")
    engine.runAndWait()
    

# Function to handle recording and transcribing
def recording_thread_function():
    global transcribed_responses, reworded_responses, add_more_flag

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

    # After recording is stopped, reword the transcription
    reworded = reword_text(transcription_text)

    # Save responses
    current_q = questions[current_question]
    if add_more_flag:
        # Append to existing responses
        transcribed_responses[current_q] += " " + transcription_text if current_q in transcribed_responses else transcription_text
        reworded_responses[current_q] += " " + reworded if current_q in reworded_responses else reworded
    else:
        # Replace existing responses
        transcribed_responses[current_q] = transcription_text
        reworded_responses[current_q] = reworded

    # Reset add_more_flag
    add_more_flag = False

    # Schedule GUI updates
    root.after(0, update_reworded_label, reworded)
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

# Function to disable buttons during recording
def disable_buttons_for_recording():
    start_button.configure(state="disabled")
    stop_button.configure(state="normal")
    next_button.configure(state="disabled")
    prev_button.configure(state="disabled")
    save_button.configure(state="disabled")
    skip_button.configure(state="disabled")

# Function to re-enable buttons after recording
def enable_buttons_after_recording():
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")
    next_button.configure(state="normal")
    prev_button.configure(state="normal")
    save_button.configure(state="normal")
    skip_button.configure(state="normal")

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
        "Name": reworded_responses.get(questions[0], "").strip(),
        "Contact Number": reworded_responses.get(questions[1], "").strip(),
        "Email Address": reworded_responses.get(questions[2], "").strip(),
        "Address": reworded_responses.get(questions[3], "").strip(),
        "Professional Summary": reworded_responses.get(questions[4], "").strip(),
        "Skills": reworded_responses.get(questions[5], "").strip(),
        "Certifications and Training": reworded_responses.get(questions[6], "").strip(),
        "Professional Achievements": reworded_responses.get(questions[7], "").strip(),
        "Work Experience": f"{reworded_responses.get(questions[8], '').strip()}\n{reworded_responses.get(questions[9], '').strip()}\nKey Projects: {reworded_responses.get(questions[10], '').strip()}".strip(),
        "Education": f"{reworded_responses.get(questions[11], '').strip()}\n{reworded_responses.get(questions[12], '').strip()}".strip(),
        "Interests": reworded_responses.get(questions[13], "").strip(),
        "Extracurricular Activities": reworded_responses.get(questions[14], "").strip(),
        "Volunteer Experience": reworded_responses.get(questions[15], "").strip(),
        "Professional Associations": reworded_responses.get(questions[16], "").strip(),
        "References": "Available upon request."
    }

    # Start building the resume text
    resume_text = ""

    # Function to add section if response exists
    def add_section(title, content):
        nonlocal resume_text
        if content:
            resume_text += f"{title}:\n{content}\n\n"

    # Add each section only if it has content
    add_section("Name", resume_sections["Name"])
    add_section("Contact Number", resume_sections["Contact Number"])
    add_section("Email Address", resume_sections["Email Address"])
    add_section("Address", resume_sections["Address"])
    add_section("Professional Summary", resume_sections["Professional Summary"])

    if resume_sections["Skills"]:
        skills_list = [skill.strip() for skill in resume_sections["Skills"].split(',') if skill.strip()]
        if skills_list:
            resume_text += "Skills:\n"
            for skill in skills_list:
                resume_text += f"- {skill}\n"
            resume_text += "\n"

    if resume_sections["Certifications and Training"]:
        certs_list = [cert.strip() for cert in resume_sections["Certifications and Training"].split(',') if cert.strip()]
        if certs_list:
            resume_text += "Certifications and Training:\n"
            for cert in certs_list:
                resume_text += f"- {cert}\n"
            resume_text += "\n"

    if resume_sections["Professional Achievements"]:
        achievements_list = [ach.strip() for ach in resume_sections["Professional Achievements"].split(',') if ach.strip()]
        if achievements_list:
            resume_text += "Professional Achievements:\n"
            for ach in achievements_list:
                resume_text += f"- {ach}\n"
            resume_text += "\n"

    add_section("Work Experience", resume_sections["Work Experience"])
    add_section("Education", resume_sections["Education"])

    if resume_sections["Interests"]:
        interests_list = [interest.strip() for interest in resume_sections["Interests"].split(',') if interest.strip()]
        if interests_list:
            resume_text += "Interests:\n"
            for interest in interests_list:
                resume_text += f"- {interest}\n"
            resume_text += "\n"

    add_section("Extracurricular Activities", resume_sections["Extracurricular Activities"])
    add_section("Volunteer Experience", resume_sections["Volunteer Experience"])

    if resume_sections["Professional Associations"]:
        associations_list = [assoc.strip() for assoc in resume_sections["Professional Associations"].split(',') if assoc.strip()]
        if associations_list:
            resume_text += "Professional Associations:\n"
            for assoc in associations_list:
                resume_text += f"- {assoc}\n"
            resume_text += "\n"

    # Always add References at the end
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
                response = reworded_responses.get(question, "")
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
        # Build the Input section from reworded responses
        input_section = ""
        for question in questions:
            field_name = field_mapping.get(question, question)
            response = reworded_responses.get(question, "")
            input_section += f"{field_name} - {response}\n"
    
        # Your initial prompt
        full_prompt = f"""[Resume Generation Prompt

Input:

{input_section}

Instructions:

Use the provided details to generate a resume in the following format. Ensure clarity and specificity in each section based on the details given.

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
    reworded_responses[current_q] = ""
    update_resume_preview()
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
    reworded_responses[current_q] = ""
    update_resume_preview()
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
root.geometry("1400x700")

# Function to show the start page
def show_start_page():
    start_frame = ctk.CTkFrame(root)
    start_frame.pack(pady=10, padx=20, fill="both", expand=True)

    welcome_label = ctk.CTkLabel(start_frame, text="Welcome to the Resume Generator", font=("Arial", 24))
    welcome_label.pack(pady=20)

    instruction_label = ctk.CTkLabel(start_frame, text="Please select an option to proceed", font=("Arial", 16))
    instruction_label.pack(pady=10)

    # Manual Walkthrough Button
    manual_button = ctk.CTkButton(start_frame, text="Manual Walkthrough", command=lambda: start_manual_mode(start_frame))
    manual_button.pack(pady=10)

    # Voice Assisted Walkthrough Button
    voice_button = ctk.CTkButton(start_frame, text="Voice Assisted Walkthrough", command=lambda: start_voice_mode(start_frame))
    voice_button.pack(pady=10)

# Function to start manual mode with voice recording
def start_manual_mode(start_frame):
    start_frame.destroy()
    initialize_manual_gui()
    
# Function to start voice mode
def start_voice_mode(start_frame):
    start_frame.destroy()
    initialize_voice_gui()
    threading.Thread(target=voice_walkthrough).start()
    
    
# Function to initialize the voice GUI
def initialize_voice_gui():
    global status_label
    # Create a frame for the voice mode
    voice_frame = ctk.CTkFrame(root)
    voice_frame.pack(pady=10, padx=20, fill="both", expand=True)

    # Status Label
    status_label = ctk.CTkLabel(voice_frame, text="Status: Starting Voice Walkthrough...", wraplength=760, font=("Arial", 12, "italic"))
    status_label.pack(pady=5, padx=20, anchor="w")


# Function to initialize the manual input GUI with voice recording
def initialize_manual_gui():
    global question_label, transcribed_label, reworded_label
    global start_button, stop_button, next_button, prev_button, save_button, skip_button, generate_button
    global status_label, resume_preview_textbox, decision_frame

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
    start_button = ctk.CTkButton(button_frame, text="Start Recording", command=lambda: start_recording_thread(add_more=False))
    start_button.pack(side="left", padx=10, pady=10)

    # Stop Recording Button
    stop_button = ctk.CTkButton(button_frame, text="Stop Recording", command=stop_recording)
    stop_button.pack(side="left", padx=10, pady=10)
    stop_button.configure(state="disabled")  # Initially disabled

    # Add More Button
    add_more_main_button = ctk.CTkButton(button_frame, text="Add More", command=add_more_response)
    add_more_main_button.pack(side="left", padx=10, pady=10)

    # Skip Button
    skip_button = ctk.CTkButton(button_frame, text="Skip", command=skip_question_func)
    skip_button.pack(side="left", padx=10, pady=10)

    # Previous Button
    prev_button = ctk.CTkButton(button_frame, text="Previous", command=prev_question_func)
    prev_button.pack(side="left", padx=10, pady=10)

    # Next Button
    next_button = ctk.CTkButton(button_frame, text="Next", command=next_question_func)
    next_button.pack(side="left", padx=10, pady=10)

    # Save Resume Button
    save_button = ctk.CTkButton(button_frame, text="Save Resume", command=save_resume)
    save_button.pack(side="right", padx=10, pady=10)

    # Generate Formatted Resume Button
    generate_button = ctk.CTkButton(button_frame, text="Generate Formatted Resume", command=generate_and_save_formatted_resume)
    generate_button.pack(side="right", padx=10, pady=10)

    # Status Label
    status_label = ctk.CTkLabel(root, text="Status: Ready", wraplength=760, font=("Arial", 12, "italic"))
    status_label.pack(pady=5, padx=20, anchor="w")

    # Labels to display transcription and reworded response
    transcribed_label = ctk.CTkLabel(root, text="Transcription: ", wraplength=760, font=("Arial", 12))
    transcribed_label.pack(pady=5, padx=20, anchor="w")

    reworded_label = ctk.CTkLabel(root, text="Reworded: ", wraplength=760, font=("Arial", 12, "bold"))
    reworded_label.pack(pady=5, padx=20, anchor="w")

    # Decision Frame
    decision_frame = ctk.CTkFrame(root)
    # Decision Frame Buttons
    accept_button = ctk.CTkButton(decision_frame, text="Accept", command=accept_response)
    accept_button.pack(side="left", padx=10, pady=10)

    redo_button = ctk.CTkButton(decision_frame, text="Redo", command=redo_response)
    redo_button.pack(side="left", padx=10, pady=10)

    add_more_button = ctk.CTkButton(decision_frame, text="Add More", command=add_more_response)
    add_more_button.pack(side="left", padx=10, pady=10)

    # Resume Preview Textbox
    resume_preview_label = ctk.CTkLabel(root, text="Resume Preview:", font=("Arial", 14))
    resume_preview_label.pack(pady=10, padx=20, anchor="w")

    resume_preview_textbox = ctk.CTkTextbox(root, width=760, height=250, wrap="word")
    resume_preview_textbox.pack(pady=5, padx=20)
    resume_preview_textbox.configure(state="disabled")  # Make it read-only

    # Initialize the first question
    update_question()

# Start the application
show_start_page()

# Start the GUI event loop
root.mainloop()