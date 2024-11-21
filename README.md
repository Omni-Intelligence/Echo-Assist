# AI Voice Assistant

A powerful productivity application that combines voice typing and AI chat capabilities. This application features real-time speech-to-text transcription and interactive conversations with customizable AI avatars.

## Features

### Voice Typing
- Real-time speech-to-text transcription using Whisper
- Live audio level visualization
- Keyboard shortcuts (Ctrl+Space) for easy recording control
- Clear status updates and error feedback
- Preview window for transcribed text

### Avatar Chat
- Interactive conversations with AI avatars
- Multiple customizable avatar personalities
- Clean and intuitive chat interface
- Message history management
- Real-time response streaming

## Requirements

- Python 3.8 or higher
- CUDA-capable GPU (recommended for better performance)
- Windows OS (tested on Windows 10/11)
- Microphone for voice typing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/EDNAHQ/ai-voice-app.git
cd ai-voice-app
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the root directory with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

## Usage

### Running the Application

1. Use the provided batch file:
```bash
run_productivity_app.bat
```

Or run directly with Python:
```bash
python productivity_app.py
```

### Voice Typing

1. Select "Voice Typing" mode from the dropdown
2. Press Ctrl+Space to start recording
3. Speak clearly into your microphone
4. Press Ctrl+Space again to stop recording
5. The transcribed text will appear in the preview window

### Avatar Chat

1. Select "Avatar Chat" mode
2. Choose an avatar from the dropdown menu
3. Type your message or paste transcribed text
4. Press Enter or click Send to start the conversation

## Project Structure

- `modules/`
  - `voice_typer.py`: Voice typing implementation
  - `avatar_chat.py`: Avatar chat interface
  - `style_config.py`: UI styling configuration
- `individual_avatars/`: Avatar personality configurations
- `avatars/`: Avatar system configurations
- `productivity_app.py`: Main application entry point

## Technical Details

### Voice Typing
- Uses OpenAI's Whisper model for accurate transcription
- Real-time audio level monitoring
- Efficient resource management and cleanup
- Error handling for audio devices and transcription

### Avatar Chat
- OpenAI GPT for natural conversations
- Message history management
- Customizable avatar personalities
- Clean separation of UI and logic

## Troubleshooting

1. **Audio Device Issues**
   - Ensure your microphone is properly connected
   - Check Windows sound settings
   - Try running as administrator

2. **Performance Issues**
   - Ensure GPU drivers are up to date
   - Close resource-intensive applications
   - Check available system memory

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for Whisper and GPT models
- ElevenLabs for voice synthesis
- PyQt6 for the UI framework
