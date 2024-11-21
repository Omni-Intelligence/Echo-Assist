import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QFrame, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import speech_recognition as sr
import numpy as np
import pyaudio
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

class AudioRecorderThread(QThread):
    recording_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._recording = False
        self.audio = None
        self.silence_threshold = 800  # Reduced from 1000 to 800
        self.silence_duration = 1.0   # Reduced from 1.5 to 1.0 seconds
        self.chunk_size = 1024
        self.sample_format = pyaudio.paInt16
        self.channels = 1
        self.sample_rate = 44100
        self.min_phrase_time = 0.5    # Reduced from 1.0 to 0.5 seconds

    def is_silent(self, audio_data):
        rms = np.sqrt(np.mean(np.array(audio_data) ** 2))
        print(f"Current RMS: {rms}")  # Debug output
        return rms < self.silence_threshold

    def run(self):
        try:
            import time
            import wave
            import io

            p = pyaudio.PyAudio()
            stream = p.open(format=self.sample_format,
                          channels=self.channels,
                          rate=self.sample_rate,
                          input=True,
                          frames_per_buffer=self.chunk_size)

            print("Recording...")
            frames = []
            self._recording = True
            last_sound_time = time.time()
            start_time = time.time()
            silence_start = None

            while self._recording:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
                current_time = time.time()
                
                # Don't check for silence during the minimum phrase time
                if current_time - start_time < self.min_phrase_time:
                    continue

                # Check for silence
                audio_data = np.frombuffer(data, dtype=np.int16)
                if self.is_silent(audio_data):
                    if silence_start is None:
                        silence_start = current_time
                    elif current_time - silence_start > self.silence_duration:
                        print(f"Silence detected for {current_time - silence_start:.2f} seconds, stopping recording")
                        break
                else:
                    silence_start = None
                    last_sound_time = current_time

            total_duration = time.time() - start_time
            print(f"Recording finished. Total duration: {total_duration:.2f} seconds")
            
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            p.terminate()

            # Only process if we have enough audio
            if total_duration < 0.5:  # Ignore very short recordings
                self.error_occurred.emit("Recording too short, please try again")
                return

            # Convert frames to AudioData format
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(p.get_sample_size(self.sample_format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))

            wav_buffer.seek(0)
            self.audio = sr.AudioData(wav_buffer.read(),
                                    self.sample_rate,
                                    p.get_sample_size(self.sample_format))

            # Convert to text
            r = sr.Recognizer()
            try:
                text = r.recognize_google(self.audio)
                print("Recognized text:", text)
                self.recording_finished.emit(text)
            except sr.UnknownValueError:
                self.error_occurred.emit("Could not understand audio")
            except sr.RequestError as e:
                self.error_occurred.emit(f"Could not request results; {str(e)}")

        except Exception as e:
            error_msg = f"Error in audio recording: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.error_occurred.emit("Error recording audio")

    def stop(self):
        self._recording = False

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
        self.chat_display.setFont(self.theme.SMALL_FONT)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme.get_color('primary')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {self.theme.get_color('secondary')};
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
        layout.addWidget(self.chat_display)

        # Controls container
        controls = QFrame()
        controls.setObjectName("controls")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(12, 0, 12, 0)
        controls_layout.setSpacing(8)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Record button
        self.record_button = QPushButton("🎤 Click to Talk")
        self.record_button.setFont(self.theme.SMALL_FONT)
        self.record_button.setFixedSize(150, 32)
        self.record_button.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.get_color('primary_gradient')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 16px;
                padding: 6px;
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
        self.record_button.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.record_button)
        controls_layout.addStretch()

        layout.addWidget(controls)

    def update_theme(self):
        """Update widget styles when theme changes"""
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme.get_color('primary')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {self.theme.get_color('secondary')};
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
        
        self.record_button.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.get_color('primary_gradient')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 16px;
                padding: 6px;
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
        """Handle recording button click"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start recording audio"""
        try:
            self.recording = True
            self.record_button.setText("🎤 Recording...")
            self.record_button.setEnabled(False)
            
            # Clean up any existing recorder thread
            if self.recorder_thread and self.recorder_thread.isRunning():
                self.recorder_thread.wait()
                self.recorder_thread = None
            
            # Start new recording thread
            self.recorder_thread = AudioRecorderThread()
            self.recorder_thread.recording_finished.connect(self.process_audio)
            self.recorder_thread.error_occurred.connect(self.handle_error)
            self.recorder_thread.start()
            
        except Exception as e:
            error_msg = f"Error starting recording: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.handle_error("Error starting recording")
            self.recording = False
            self.record_button.setText("🎤 Click to Talk")
            self.record_button.setEnabled(True)

    def stop_recording(self):
        """Stop recording audio"""
        try:
            if self.recorder_thread and self.recorder_thread.isRunning():
                self.recorder_thread.stop()
            self.recording = False
            self.record_button.setText("🎤 Click to Talk")
            self.record_button.setEnabled(True)
        except Exception as e:
            error_msg = f"Error stopping recording: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.handle_error("Error stopping recording")

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
                
            # Reset button state
            self.recording = False
            self.record_button.setText("🎤 Click to Talk")
            self.record_button.setEnabled(True)
            
        except Exception as e:
            error_msg = f"Error processing audio: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.handle_error("Error processing your speech. Please try again.")
            self.recording = False
            self.record_button.setText("🎤 Click to Talk")
            self.record_button.setEnabled(True)

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
        pass
