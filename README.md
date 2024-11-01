
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

### 5. Set up Environment Variables (Message me for API Key)
- Create a `.env` file in the project root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key
```

## Running the Application

1. Open the folder containing `resume_maker_2.4.py` in VS Code.
2. Open a terminal in VS Code.
3. Run the following command:
```bash
python resume_maker_2.4.py
```

## How the Code Works

### 1. **Main Libraries Used:**
- **`customtkinter`**: Utilized for creating a modern and responsive Graphical User Interface (GUI).
- **`pyaudio`**, **`speech_recognition`**, **`whisper`**: Employed for real-time voice recording, speech recognition, and transcription using OpenAI's Whisper model.
- **`requests`**, **`openai`**: Facilitates interaction with OpenAI's GPT-3.5-turbo for text rewording, formatting, and generating formatted resumes.
- **`pyttsx3`**: Converts text to speech, enabling voice-assisted walkthroughs and user confirmations.
- **`python-docx`**, **`docx2pdf`**: Handles the creation of styled Word documents and their conversion to PDF format.
- **`Pillow (PIL)`**: Manages image processing for icons and logos within the GUI.
- **`webrtcvad`**, **`fuzzywuzzy`**: Enhances audio processing with Voice Activity Detection (VAD) and fuzzy string matching for address verification.
- **`dotenv`**: Loads environment variables securely from a `.env` file.
- **`numpy`**, **`sounddevice`**: Assists in advanced audio processing tasks.
- **`json`**: Handles loading and saving configuration and user response data.
- **`tkinter.messagebox`**: Provides dialog boxes for user notifications and error messages.

### 2. **Core Features:**
- **Voice Walkthrough**: 
  - **Interactive Q&A**: The application guides users through a series of resume-related questions, recording and transcribing their verbal responses in real-time.
  - **Real-time Transcription & Rewording**: Utilizes Whisper for transcription and OpenAI's GPT-3.5-turbo to rephrase responses into professional resume language.
  - **Voice Confirmation**: Reads back reworded responses to users, allowing them to confirm or redo inputs via voice commands.
  
- **Manual Mode**:
  - **Direct Input**: Users can manually type their responses to the resume questions.
  - **Text Rewording**: Similar to voice inputs, typed responses are sent to OpenAI for professional rewording and formatting.
  
- **Resume Generation**:
  - **Structured Compilation**: Compiles transcribed and reworded responses into a well-structured resume format.
  - **Document Formatting**: Uses `python-docx` to apply custom styles and layouts, ensuring a polished final document.
  - **Export Options**: Allows users to save their resumes as both Word (`.docx`) and PDF (`.pdf`) files.
  
- **Real-time Feedback**:
  - **Live Updates**: Displays transcribed responses and a live preview of the resume within the GUI.
  - **Voice Feedback**: Provides auditory confirmations and prompts to enhance user interaction.

- **Settings & Customization**:
  - **Text-to-Speech (TTS) Configuration**: Users can adjust speech rates, select different TTS voices, and choose preferred languages to tailor the voice walkthrough experience.
  - **Language Selection**: Supports multiple languages for transcription and TTS to accommodate diverse user needs.
  
- **User Assistance & Recovery**:
  - **Help Menu**: Offers comprehensive guidance on using the application, including keyboard shortcuts and troubleshooting tips.
  - **Autosave & Recovery**: Automatically saves user progress at regular intervals and allows recovery of the last session in case of interruptions.
  
- **Keyboard Shortcuts**:
  - Implements intuitive shortcuts (e.g., `Ctrl+R` to start/stop recording, `Ctrl+S` to save) to streamline user interactions and enhance accessibility.

### 3. **Key Functionalities:**
- **Recording and Transcribing**:
  - **Voice Capture**: Leverages `pyaudio` and `webrtcvad` for efficient audio recording with voice activity detection to determine speech segments.
  - **Transcription Service**: Sends recorded audio to OpenAI's Whisper API for accurate transcription, supporting multiple languages as configured.
  
- **Rewording and Formatting Responses**:
  - **OpenAI Integration**: Sends both manual and transcribed responses to OpenAI's GPT-3.5-turbo for rewording, ensuring professional and coherent resume content.
  - **Template-Based Processing**: Utilizes a predefined resume prompt template to maintain consistency in the formatting and structure of the generated resumes.
  
- **Resume Document Creation**:
  - **Dynamic Styling**: Applies custom styles (e.g., fonts, sizes, alignments) using `python-docx` to create aesthetically pleasing and standardized resume sections.
  - **Section Parsing**: Automatically parses and organizes user inputs into relevant resume sections such as Professional Summary, Skills, Work Experience, Education, etc.
  
- **PDF Conversion**:
  - **Seamless Export**: Converts the formatted Word document to PDF using `docx2pdf`, providing users with versatile file formats for their resumes.
  
- **Address Verification**:
  - **Location Matching**: Utilizes `fuzzywuzzy` to match transcribed addresses against a catalogue of Trinidad locations, ensuring address accuracy and consistency.
  - **Automated Formatting**: Cleans and formats the address input by removing unmatched segments and appending verified location names.
  
- **User Interface Enhancements**:
  - **Responsive Design**: Ensures the GUI adapts to different screen sizes and resolutions for optimal user experience.
  - **Interactive Elements**: Incorporates buttons with icons, progress bars, and textboxes to facilitate user interactions and provide visual feedback.
  
- **Data Management**:
  - **Autosave Mechanism**: Periodically saves user inputs and progress to prevent data loss.
  - **Clear and Reset Functionality**: Allows users to clear all inputs and restart the resume creation process seamlessly.
  
- **Error Handling and Notifications**:
  - **Robust Error Messages**: Provides clear and descriptive error messages for issues like API failures, missing configuration files, or hardware problems.
  - **User Alerts**: Uses dialog boxes to inform users about successful operations, errors, and important prompts.

### 4. **Additional Functionalities:**
- **Menu Bar Integration**:
  - **Settings Access**: Allows users to access and modify application settings directly from the menu bar.
  - **Help and Support**: Provides easy access to the help documentation and support contact information.
  - **Recovery Options**: Enables users to recover their last session through the menu bar in case of unexpected closures or crashes.
  
- **Voice-Controlled Commands**:
  - **Interactive Voice Commands**: Supports voice commands such as "restart voice walkthrough" to enhance hands-free interactions during the resume creation process.
  
- **Customization Options**:
  - **Theme and Appearance**: Offers theme settings (e.g., dark mode, light mode) to personalize the application's look and feel.
  
- **Resource Management**:
  - **Temporary File Handling**: Efficiently manages temporary files created during recording and transcription, ensuring they are deleted after use to save storage space.
  
- **Extensibility**:
  - **Modular Design**: Structured in a way that allows easy addition of new features, questions, or integrations in the future.

### 5. **Workflow Overview:**
1. **Initialization**:
   - Loads environment variables and necessary configurations from `.env` and JSON files.
   - Initializes the GUI with options for Manual and Voice Assisted Walkthroughs.
  
2. **User Interaction**:
   - **Manual Mode**: Users input their resume details through text fields, with options to navigate between questions, add more details, or skip sections.
   - **Voice Mode**: Users respond to questions verbally, with the application handling recording, transcription, and confirmation via voice commands.
  
3. **Data Processing**:
   - Captures user inputs (text or voice), transcribes them, and sends them to OpenAI for rewording.
   - Organizes the processed inputs into structured resume sections.
  
4. **Resume Generation**:
   - Compiles the organized data into a Word document with custom styling.
   - Converts the Word document to PDF format for user convenience.
  
5. **Finalization**:
   - Allows users to review, save, and export their completed resumes.
   - Provides options to clear data, recover sessions, or adjust settings as needed.