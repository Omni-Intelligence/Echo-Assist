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

    def __init__(self, input_device_index=None):
        super().__init__()
        self._recording = False
        self.audio = None
        self.silence_threshold = 300  # Even lower threshold
        self.silence_duration = 2.5   # Longer silence duration
        self.chunk_size = 1024
        self.sample_format = pyaudio.paInt16
        self.channels = 1
        self.sample_rate = 44100
        self.min_phrase_time = 0.5
        self.debug_mode = True
        self.buffer_size = 50  # Number of frames to keep for rolling average
        self.audio_buffer = collections.deque(maxlen=self.buffer_size)
        self.post_speech_buffer = 1.0  # Additional recording time after speech
        self.input_device_index = input_device_index

    def is_silent(self, audio_data):
        rms = np.sqrt(np.mean(np.array(audio_data) ** 2))
        self.audio_buffer.append(rms)
        
        # Calculate rolling average
        rolling_rms = np.mean(self.audio_buffer) if len(self.audio_buffer) > 0 else rms
        
        if self.debug_mode:
            if np.random.random() < 0.1:
                print(f"Current Level: {rms:.2f} | Rolling Avg: {rolling_rms:.2f} | Threshold: {self.silence_threshold}")
        
        return rolling_rms < self.silence_threshold

    def run(self):
        try:
            import time
            import wave
            import io

            p = pyaudio.PyAudio()
            
            # Print available input devices if in debug mode
            if self.debug_mode:
                print("\nAvailable Input Devices:")
                for i in range(p.get_device_count()):
                    dev = p.get_device_info_by_index(i)
                    if dev['maxInputChannels'] > 0:
                        print(f"Index {i}: {dev['name']}")
                if self.input_device_index is not None:
                    print(f"\nUsing input device index: {self.input_device_index}")
                    dev = p.get_device_info_by_index(self.input_device_index)
                    print(f"Selected device: {dev['name']}")
                else:
                    print("\nUsing default input device")

            stream = p.open(format=self.sample_format,
                          channels=self.channels,
                          rate=self.sample_rate,
                          input=True,
                          input_device_index=self.input_device_index,
                          frames_per_buffer=self.chunk_size)

            print("Recording started - Listening for voice...")
            frames = []
            self._recording = True
            start_time = time.time()
            silence_start = None
            last_speech_time = time.time()
            recording_buffer_active = False

            while self._recording:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
                current_time = time.time()
                
                # Don't check for silence during the minimum phrase time
                if current_time - start_time < self.min_phrase_time:
                    continue

                # Check for silence
                audio_data = np.frombuffer(data, dtype=np.int16)
                if not self.is_silent(audio_data):
                    if self.debug_mode and silence_start is not None:
                        print("Voice detected, continuing recording...")
                    silence_start = None
                    last_speech_time = current_time
                    recording_buffer_active = True
                else:
                    if silence_start is None:
                        silence_start = current_time
                        if self.debug_mode:
                            print("Potential silence detected...")
                    
                    # Check if we're in the post-speech buffer period
                    if recording_buffer_active and current_time - last_speech_time <= self.post_speech_buffer:
                        if self.debug_mode and np.random.random() < 0.1:
                            print(f"In post-speech buffer: {self.post_speech_buffer - (current_time - last_speech_time):.1f}s remaining")
                        continue
                    
                    # Only stop if we've been silent for long enough and we're past the buffer period
                    if current_time - silence_start > self.silence_duration:
                        if self.debug_mode:
                            print(f"Stopping: Silence duration: {current_time - silence_start:.1f}s")
                            print(f"Total recording: {current_time - start_time:.1f}s")
                        break

            total_duration = time.time() - start_time
            if self.debug_mode:
                print(f"Recording finished. Duration: {total_duration:.1f}s")
            
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

class VoicePlaybackThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, text, voice_id):
        super().__init__()
        self.text = text
        self.voice_id = voice_id
        self._stop = False
        self.audio_stream = None
    
    def run(self):
        try:
            self.audio_stream = elevenlabs_client.generate(
                text=self.text,
                voice=self.voice_id,
                model="eleven_multilingual_v2",
                stream=True
            )
            if not self._stop:
                stream(self.audio_stream)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.cleanup()
    
    def stop(self):
        self._stop = True
        self.cleanup()
    
    def cleanup(self):
        if self.audio_stream:
            try:
                self.audio_stream.close()
            except:
                pass
            self.audio_stream = None

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
        self.voice_thread = None
        self.recording = False
        self.current_response = ""
        self.selected_input_device = None
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
        self.chat_display.append(f'<i>Echo Assist is ready. Chatting with {avatar_name}. Click the button to start recording.</i>\n')

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
            
            # Start new recording thread with selected input device
            self.recorder_thread = AudioRecorderThread(input_device_index=self.selected_input_device)
            self.recorder_thread.recording_finished.connect(self.process_audio)
            self.recorder_thread.error_occurred.connect(self.handle_error)
            self.recorder_thread.start()
            
        except Exception as e:
            error_msg = f"Error starting recording: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.handle_error(error_msg)
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
            self.chat_display.append(f'<i>Echo Assist is ready. Chatting with {self.current_avatar}. Click the button to start recording.</i>\n')
            
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
                self.voice_thread = VoicePlaybackThread(response, voice_id)
                self.voice_thread.finished.connect(self.on_voice_finished)
                self.voice_thread.error.connect(self.handle_error)
                self.record_button.setText("🔊 Stop")
                self.record_button.setEnabled(True)
                self.record_button.clicked.disconnect()
                self.record_button.clicked.connect(self.stop_voice)
                self.voice_thread.start()
                
            except Exception as e:
                error_msg = f"Error generating voice: {str(e)}\nFull traceback:\n{traceback.format_exc()}"
                print(error_msg)
                self.handle_error(f"ElevenLabs Error: {str(e)}")
                self.reset_record_button()
                
        except Exception as e:
            print(f"Error in handle_chat_response: {str(e)}")
            self.handle_error("Error processing AI response")
            self.reset_record_button()

    def stop_voice(self):
        """Stop the current voice playback"""
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.cleanup_voice_thread()
        self.reset_record_button()

    def on_voice_finished(self):
        """Handle voice playback completion"""
        self.cleanup_voice_thread()
        self.reset_record_button()

    def reset_record_button(self):
        """Reset the record button to its initial state"""
        self.record_button.setText("🎤 Click to Talk")
        self.record_button.setEnabled(True)
        try:
            self.record_button.clicked.disconnect()
        except:
            pass
        self.record_button.clicked.connect(self.toggle_recording)

    def cleanup_response_thread(self):
        """Clean up after response is complete"""
        if self.response_thread:
            if self.response_thread.isRunning():
                self.response_thread.wait()
            self.response_thread = None

    def cleanup_voice_thread(self):
        """Clean up after voice playback is complete"""
        if self.voice_thread:
            if self.voice_thread.isRunning():
                self.voice_thread.wait()
            self.voice_thread = None

    def handle_error(self, error_message):
        self.chat_display.append(f'\n<b>Error:</b> {error_message}')

    def update_audio_level(self, level):
        pass

    def update_input_device(self, device_index):
        """Update the input device for audio capture"""
        print(f"Updating input device to index: {device_index}")
        self.selected_input_device = device_index
        if self.recording:
            self.stop_recording()
            self.start_recording()
