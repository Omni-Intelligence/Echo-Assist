import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QFrame, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import pyaudio
import wave
import numpy as np
import collections
import faster_whisper
import torch.cuda
from openai import OpenAI
import traceback
from elevenlabs import stream
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize API clients
openai_client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

# Initialize Whisper model
model = faster_whisper.WhisperModel(model_size_or_path="tiny.en", device='cuda' if torch.cuda.is_available() else 'cpu')

def get_levels(data, long_term_noise_level, current_noise_level):
    """Calculate audio levels from raw audio data"""
    # Calculate RMS of the audio data
    pegel = np.sqrt(np.mean(data**2)) * 1000  # Increased scaling factor

    # Initialize noise levels if empty
    if not long_term_noise_level:
        long_term_noise_level.append(pegel)
    if not current_noise_level:
        current_noise_level.append(pegel)

    # Update noise levels with slower adaptation
    long_term_noise_level.append(pegel * 0.001 + long_term_noise_level[-1] * 0.999)
    current_noise_level.append(pegel * 0.05 + current_noise_level[-1] * 0.95)

    return pegel, long_term_noise_level, current_noise_level

class AudioRecorderThread(QThread):
    finished = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=16000,
                          input=True,
                          frames_per_buffer=1024)

            frames = []
            silence_counter = 0
            voice_started = False
            long_term_noise_level = collections.deque(maxlen=50)
            current_noise_level = collections.deque(maxlen=5)

            print("Starting audio recording...")

            # Record for at least 0.5 second to establish baseline
            for _ in range(8):  # 8 * 1024/16000 = ~0.5 second
                data = np.frombuffer(stream.read(1024, exception_on_overflow=False), dtype=np.int16)
                normalized_data = data.astype(np.float32) / 32768.0
                level, long_term_noise_level, current_noise_level = get_levels(
                    normalized_data, long_term_noise_level, current_noise_level)
                print(f"Baseline level: {level}")
                self.audio_level.emit(float(level))

            baseline = sum(long_term_noise_level) / len(long_term_noise_level)
            voice_threshold = max(10, baseline * 2)  # Dynamic threshold based on baseline
            print(f"Baseline noise: {baseline}, Voice threshold: {voice_threshold}")

            # Main recording loop
            while not self.isInterruptionRequested():
                try:
                    data = np.frombuffer(stream.read(1024, exception_on_overflow=False), dtype=np.int16)
                    frames.append(data.tobytes())  # Always keep the audio data
                    
                    # Normalize data to float for level calculation
                    normalized_data = data.astype(np.float32) / 32768.0
                    level, long_term_noise_level, current_noise_level = get_levels(
                        normalized_data, long_term_noise_level, current_noise_level)
                    
                    self.audio_level.emit(float(level))
                    
                    # Debug print
                    if level > voice_threshold:
                        print(f"Voice detected: {level} > {voice_threshold}")

                    # Detect voice activity with dynamic threshold
                    if level > voice_threshold:
                        voice_started = True
                        silence_counter = 0
                    elif voice_started:
                        silence_counter += 1
                    
                    # Stop after 2 seconds of silence (31 frames * 64ms = ~2s)
                    if voice_started and silence_counter > 31:
                        print("Stopping recording due to silence")
                        break

                except IOError as e:
                    print(f"IOError during recording: {e}")
                    self.error_occurred.emit("Error recording audio. Please check your microphone.")
                    return

            stream.stop_stream()
            stream.close()
            p.terminate()

            if len(frames) > 0:  # Always try to process the audio if we have frames
                print(f"Processing {len(frames)} frames of audio")
                wf = wave.open("voice_record.wav", 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                try:
                    user_text = " ".join(seg.text for seg in model.transcribe("voice_record.wav", language="en")[0])
                    if user_text.strip():
                        print(f"Transcribed text: {user_text}")
                        self.finished.emit(user_text)
                    else:
                        print("No text transcribed")
                        self.finished.emit("")
                except Exception as e:
                    print(f"Error transcribing audio: {e}")
                    self.error_occurred.emit("Error transcribing audio. Please try again.")
            else:
                print("No frames recorded")
                self.finished.emit("")

        except Exception as e:
            error_msg = f"Error in audio recording: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.error_occurred.emit("Error with audio recording. Please check your microphone settings.")

class ChatResponseThread(QThread):
    response_ready = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        try:
            ai_response = ""
            for chunk in openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.messages,
                stream=True
            ):
                if chunk.choices and chunk.choices[0].delta and (text_chunk := chunk.choices[0].delta.content):
                    ai_response += text_chunk
                    self.progress_update.emit(text_chunk)
            self.response_ready.emit(ai_response)
        except Exception as e:
            error_msg = f"Error during chat response: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)  # Log the error
            self.error_occurred.emit("Sorry, there was an error processing your request. Please try again.")

class AvatarChatWidget(QWidget):
    def __init__(self, theme, avatars):
        super().__init__()
        self.theme = theme
        self.avatars = avatars
        self.current_avatar = None
        self.chat_history = []
        self.display_messages = []
        self.recorder_thread = None
        self.response_thread = None
        self.recording = False
        self.current_response = ""
        self.initUI()

    def initUI(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)  # Increased from 8 to 12 to match test
        layout.setSpacing(8)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(self.theme.SMALL_FONT)  # Changed from BODY_FONT to SMALL_FONT
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background: {self.theme.get_color('primary_gradient')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;  # Reduced from 8px to 6px
                padding: 8px;  # Reduced from 12px to 8px
            }}
            QScrollBar:vertical {{
                border: none;
                background: {self.theme.get_color('primary')};
                width: 6px;  # Reduced from 8px to 6px
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme.get_color('accent')};
                min-height: 20px;
                border-radius: 3px;  # Reduced from 4px to 3px
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        layout.addWidget(self.chat_display)

        # Audio level indicator
        self.level_indicator = QFrame()
        self.level_indicator.setFixedHeight(4)
        self.level_indicator.setFixedWidth(0)
        self.level_indicator.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.get_color('accent_gradient')};
                border-radius: 2px;
            }}
        """)
        
        # Level indicator container
        level_container = QFrame()
        level_container.setFixedHeight(12)
        level_container.setMinimumWidth(180)
        level_container.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.get_color('primary_gradient')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;
            }}
        """)
        
        # Center the level indicator in its container
        level_layout = QHBoxLayout(level_container)
        level_layout.setContentsMargins(4, 4, 4, 4)
        level_layout.addWidget(self.level_indicator)
        level_layout.addStretch()
        
        # Controls container
        controls = QFrame()
        controls.setObjectName("controls")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        # Record button
        self.record_button = QPushButton("🎤 Hold to Talk")
        self.record_button.setFont(self.theme.BODY_FONT)
        self.record_button.setFixedSize(180, 40)
        self.record_button.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.get_color('primary_gradient')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 20px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background: {self.theme.get_color('accent_gradient')};
                border: 1px solid {self.theme.get_color('accent')};
            }}
            QPushButton:pressed {{
                background: {self.theme.get_color('selected_gradient')};
                border: 1px solid {self.theme.get_color('selected')};
            }}
        """)
        self.record_button.pressed.connect(self.start_recording)
        self.record_button.released.connect(self.stop_recording)

        # Add controls to layout
        controls_layout.addStretch()
        controls_layout.addWidget(level_container)
        controls_layout.addWidget(self.record_button)
        controls_layout.addStretch()

        layout.addWidget(controls)

    def update_theme(self):
        """Update widget styles when theme changes"""
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background: {self.theme.get_color('primary_gradient')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {self.theme.get_color('primary')};
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme.get_color('accent')};
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        self.level_indicator.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.get_color('accent_gradient')};
                border-radius: 2px;
            }}
        """)
        
        self.record_button.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.get_color('primary_gradient')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 20px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background: {self.theme.get_color('accent_gradient')};
                border: 1px solid {self.theme.get_color('accent')};
            }}
            QPushButton:pressed {{
                background: {self.theme.get_color('selected_gradient')};
                border: 1px solid {self.theme.get_color('selected')};
            }}
        """)
        
    def set_avatar(self, avatar_name):
        self.current_avatar = avatar_name
        self.chat_history = [{"role": "system", "content": self.avatars[avatar_name]['system_prompt']}]
        self.display_messages = []  # Clear display messages
        self.chat_display.clear()
        self.chat_display.append(f'Chatting with {avatar_name}. Click the button to start recording.')

    def toggle_recording(self):
        """Toggle recording state"""
        if not self.recording and not self.response_thread:  # Only start if not already processing
            self.start_recording()
        elif self.recording:
            self.stop_recording()

    def start_recording(self):
        """Start a new recording"""
        self.recorder_thread = AudioRecorderThread()
        self.recorder_thread.finished.connect(self.process_audio)
        self.recorder_thread.audio_level.connect(self.update_audio_level)
        self.recorder_thread.error_occurred.connect(self.handle_error)
        
        self.recording = True
        self.recorder_thread.start()

    def stop_recording(self):
        """Stop the current recording"""
        if self.recorder_thread:
            self.recorder_thread.requestInterruption()
            self.recorder_thread.wait()
            self.recorder_thread = None
            
        self.recording = False

    def process_audio(self, text):
        """Process recorded audio text"""
        try:
            if text:
                # Clean up any existing response thread
                if self.response_thread and self.response_thread.isRunning():
                    self.response_thread.wait()
                    self.response_thread = None

                # Add user message to display messages and chat history
                self.display_messages.append(("User", text))
                self.chat_history.append({"role": "user", "content": text})
                
                # Update display with all messages
                self.update_display()
                
                # Start new response thread with full context
                self.response_thread = ChatResponseThread(self.chat_history)
                self.response_thread.progress_update.connect(self.update_chat_response)
                self.response_thread.response_ready.connect(self.handle_chat_response)
                self.response_thread.error_occurred.connect(self.handle_error)
                self.response_thread.finished.connect(self.cleanup_response_thread)
                
                # Reset the current response
                self.current_response = ""
                
                self.response_thread.start()
            else:
                self.handle_error("No speech detected. Try again.")
                self.recording = False
                self.response_thread = None
        except Exception as e:
            error_msg = f"Error processing audio: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.handle_error("Error processing your speech. Please try again.")
            self.recording = False
            self.response_thread = None

    def update_chat_response(self, chunk):
        """Display incoming chat response chunks"""
        try:
            # Add the chunk to the current response
            self.current_response += chunk
            
            # Update the last message if it's from the avatar, or add a new one
            if self.display_messages and self.display_messages[-1][0] == self.current_avatar:
                self.display_messages[-1] = (self.current_avatar, self.current_response)
            else:
                self.display_messages.append((self.current_avatar, self.current_response))
            
            # Update the display
            self.update_display()
            
        except Exception as e:
            print(f"Error updating chat response: {str(e)}")
            self.handle_error("Error updating the chat display. Please try again.")

    def update_display(self):
        """Update the chat display with all messages"""
        try:
            # Clear the display
            self.chat_display.clear()
            
            # Add the initial message in italics
            self.chat_display.append(f'<i>Chatting with {self.current_avatar}. Click the button to start recording.</i>\n')
            
            # Add all messages with proper styling
            for speaker, message in self.display_messages:
                if speaker == "User":
                    # User messages are right-aligned with accent color
                    self.chat_display.append(
                        f'<div style="text-align: right; margin: 8px 0;">'
                        f'<span style="background: {self.theme.get_color("accent_gradient")}; '
                        f'color: {self.theme.get_color("text")}; padding: 8px 12px; '
                        f'border-radius: 12px 12px 2px 12px; display: inline-block;">'
                        f'{message}</span></div>\n'
                    )
                else:
                    # Avatar messages are left-aligned with primary color
                    self.chat_display.append(
                        f'<div style="text-align: left; margin: 8px 0;">'
                        f'<span style="background: {self.theme.get_color("primary_gradient")}; '
                        f'color: {self.theme.get_color("text")}; padding: 8px 12px; '
                        f'border-radius: 12px 12px 12px 2px; display: inline-block;">'
                        f'{message}</span></div>\n'
                    )
            
            # Keep the display scrolled to the bottom
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"Error updating display: {str(e)}")
            self.handle_error("Error updating the chat display.")

    def handle_chat_response(self, response):
        """Handle the complete chat response"""
        try:
            # Update chat history
            self.chat_history.append({"role": "assistant", "content": response})
            
            # Update display messages with the final response
            if self.display_messages and self.display_messages[-1][0] == self.current_avatar:
                self.display_messages[-1] = (self.current_avatar, response)
            else:
                self.display_messages.append((self.current_avatar, response))
            
            # Update the display
            self.update_display()
            
            # Generate and play voice response
            try:
                voice_id = self.avatars[self.current_avatar]['voice_id']
                audio_stream = elevenlabs_client.generate(
                    text=response,
                    voice=voice_id,
                    model="eleven_multilingual_v2",
                    stream=True
                )
                # Play the audio stream
                stream(audio_stream)
                
            except Exception as e:
                print(f"Error generating voice: {e}")
                self.handle_error("Error generating voice response")
                
            finally:
                # Always reset the state, regardless of voice generation success
                self.recording = False
                self.current_response = ""
                
        except Exception as e:
            print(f"Error in handle_chat_response: {str(e)}")
            self.handle_error("Error processing AI response")
            self.recording = False

    def cleanup_response_thread(self):
        """Clean up after response is complete"""
        if self.response_thread:
            if self.response_thread.isRunning():
                self.response_thread.wait()
            self.response_thread = None

    def handle_error(self, error_message):
        self.chat_display.append(f'\n<b>Error:</b> {error_message}')

    def update_audio_level(self, level):
        bars = int(level / 100) if level > 0 else 0
        width = min(self.width() * 0.8, bars * 20)  # Scale bars to widget width
        self.level_indicator.setFixedWidth(int(width))
