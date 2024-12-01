# Echo Assist - AI Voice Assistant & Chat Application

A powerful desktop productivity application that combines voice typing, AI chat capabilities, and screenshot functionality. Echo Assist features real-time speech-to-text transcription, interactive conversations with customizable AI avatars, and a modern, user-friendly interface.

## Key Features

### Voice Typing
- Real-time speech-to-text transcription powered by OpenAI's Whisper model
- Live audio level visualization for input monitoring
- Convenient keyboard shortcuts (Ctrl+Space) for recording control
- Clear status updates and error feedback
- Preview window for transcribed text before use

### Avatar Chat
- Interactive conversations with AI-powered avatars
- Multiple customizable avatar personalities
- Clean and intuitive chat interface
- Message history tracking and management
- Real-time response streaming for natural conversation flow

### Screenshot Functionality
- Capture and annotate screen content
- Quick access to screen capture tools
- Integration with chat and voice features

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Windows 10/11
- CUDA-capable GPU (recommended for optimal performance)
- Working microphone for voice features
- Internet connection for AI services

### Installation

1. Clone the Repository
   ```bash
   git clone [your-repository-url]
   cd echo-assist
   ```

2. Install Dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment Variables
   Create a `.env` file in the root directory:
   ```plaintext
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ```

### Quick Start

1. Launch the Application
   - Double-click `run.bat`, or
   - Run from command line:
     ```bash
     python productivity_app.py
     ```

2. Select Your Mode
   - Choose between Voice Typing, Avatar Chat, or Screenshot mode
   - Each mode has its own specialized interface and features

## Usage Guide

### Voice Typing Mode
1. Select "Voice Typing" from the mode dropdown
2. Press Ctrl+Space to begin recording
3. Speak naturally - the app will transcribe in real-time
4. Press Ctrl+Space again to stop
5. Review and use the transcribed text

### Avatar Chat Mode
1. Switch to "Avatar Chat" mode
2. Select your preferred AI avatar
3. Type or paste your message
4. Use the chat interface to interact with your AI assistant

### Screenshot Mode
1. Select "Screenshot" mode
2. Use the capture tools to select screen areas
3. Annotate or mark up your captures as needed
4. Save or share your screenshots

## Technical Details

### Dependencies
- PyQt6: Modern UI framework
- OpenAI API: Powers AI chat and transcription
- ElevenLabs: Advanced voice synthesis
- faster-whisper: Optimized speech recognition
- Additional requirements listed in `requirements.txt`

### Project Structure
```
echo-assist/
├── modules/                 # Core functionality modules
│   ├── voice_typer.py      # Voice transcription
│   ├── avatar_chat.py      # Chat interface
│   ├── screenshot.py       # Screen capture
│   └── style_config.py     # UI styling
├── avatars/                # Avatar configurations
├── individual_avatars/     # Custom avatar settings
└── productivity_app.py     # Main application
```

## Troubleshooting

### Common Issues
1. Audio Device Not Detected
   - Check microphone connections
   - Verify Windows permissions
   - Select correct input device in settings

2. API Connection Issues
   - Verify internet connection
   - Check API keys in `.env` file
   - Ensure valid API subscription

3. Performance Issues
   - Update GPU drivers
   - Close resource-intensive applications
   - Check system requirements

## Contributing

We welcome contributions! Please feel free to submit pull requests, report bugs, or suggest features.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT and Whisper APIs
- ElevenLabs for voice synthesis
- PyQt team for the UI framework
- All contributors and users of Echo Assist
