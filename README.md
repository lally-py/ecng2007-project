
# Project Title: Resume Generator with Voice Input

## Overview
This project is a resume generator application with both manual input and voice-assisted input modes. The application uses OpenAI's GPT-3.5-turbo for rewording text responses and Whisper for speech recognition. It allows users to build their resume by answering a set of questions through voice or manual input, rewords the responses in a professional tone, and generates a formatted resume.

## Prerequisites
Before running the application, make sure the following tools and dependencies are installed:

### 1. Install Python
- Download and install Python from the [official website](https://www.python.org/downloads/).
- Ensure you check the option to add Python to the PATH during installation.

### 2. Install Visual Studio Code (VS Code)
- Download and install VS Code from [here](https://code.visualstudio.com/download).

### 3. Clone the repository
```bash
git clone https://github.com/yourusername/resume-generator
cd resume-generator
```

### 4. Install Dependencies
- Open a terminal in VS Code, and run the following command to install the required dependencies using `pip`:
```bash
pip install -r requirements.txt
```

**Note**: If the `requirements.txt` file is missing, create it and add the following dependencies:
```
customtkinter
pyaudio
wave
tempfile
threading
requests
pyttsx3
speech_recognition
openai
Pillow
whisper
numpy
sounddevice
python-dotenv
```

### 5. Set up Environment Variables
- Create a `.env` file in the project root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key
```

## Running the Application

1. Open the folder containing `temp.py` in VS Code.
2. Open a terminal in VS Code.
3. Run the following command:
```bash
python temp.py
```

## How the Code Works

1. **Main Libraries Used:**
   - `customtkinter`: Used for creating the GUI.
   - `pyaudio`, `speech_recognition`, `whisper`: Used for real-time voice recording and transcription.
   - `requests`, `openai`: Interact with OpenAI GPT-3.5-turbo for text rewording and formatting.
   - `pyttsx3`: Converts text to speech for the voice-assisted walkthrough.

2. **Core Features:**
   - **Voice Walkthrough**: The application asks a series of resume-related questions, records your voice, and transcribes your responses using Whisper. These responses are then reworded to fit a professional resume format using OpenAI.
   - **Manual Mode**: Users can manually type their responses and have them reworded similarly.
   - **Resume Generation**: The app takes the transcribed responses and generates a complete formatted resume.
   - **Real-time Feedback**: The application reads the reworded responses back to the user for confirmation.

3. **Key Functionalities:**
   - **Recording and Transcribing**: Utilizes `pyaudio` and `speech_recognition` to record and transcribe user input.
   - **Rewording Responses**: Text is sent to OpenAI's GPT for rewording into a professional format.
   - **Formatted Resume Generation**: The app compiles user input into a structured resume format, saving it as a text file.
