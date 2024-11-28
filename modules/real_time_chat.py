from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import json
import base64
import pyaudio
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional
from websockets.sync.client import connect
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in environment variables")

class AudioInterface(ABC):
    """AudioInterface provides an abstraction for handling audio input and output."""

    @abstractmethod
    def start(self, input_callback: Callable[[bytes], None]):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def output(self, audio: bytes):
        pass

    @abstractmethod
    def interrupt(self):
        pass

class PyAudioInterface(AudioInterface):
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.chunk_size = 2048
        self.sample_rate = 16000
        self.channels = 1
        self.format = pyaudio.paInt16
        self.input_device = self._get_default_input_device()
        self.output_device = self._get_default_output_device()
        self.is_speaking = False
        self._active = False

    def _get_default_input_device(self):
        """Find the default input device index"""
        try:
            default_device = self.p.get_default_input_device_info()
            return default_device['index']
        except IOError:
            # Try to find any working input device
            for i in range(self.p.get_device_count()):
                device_info = self.p.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    return i
        return None

    def _get_default_output_device(self):
        """Find the default output device index"""
        try:
            default_device = self.p.get_default_output_device_info()
            return default_device['index']
        except IOError:
            # Try to find any working output device
            for i in range(self.p.get_device_count()):
                device_info = self.p.get_device_info_by_index(i)
                if device_info['maxOutputChannels'] > 0:
                    return i
        return None

    def start(self, input_callback: Callable[[bytes], None]):
        if self._active:
            return

        if self.input_device is None:
            raise ValueError("No valid input device found")
        if self.output_device is None:
            raise ValueError("No valid output device found")
            
        def callback(in_data, frame_count, time_info, status):
            if status:
                print(f"PyAudio callback status: {status}")
            if self._active and not self.is_speaking:
                input_callback(in_data)
            return (None, pyaudio.paContinue)

        try:
            self.input_stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=callback
            )
            
            self.output_stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.output_device,
                frames_per_buffer=self.chunk_size
            )
            
            self._active = True
            self.input_stream.start_stream()
        except Exception as e:
            print(f"Error starting audio streams: {e}")
            self.stop()
            raise

    def stop(self):
        self._active = False
        
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except Exception as e:
                print(f"Error closing input stream: {e}")
            self.input_stream = None
            
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception as e:
                print(f"Error closing output stream: {e}")
            self.output_stream = None
            
        if self.p:
            self.p.terminate()
            self.p = None

    def output(self, audio: bytes):
        if not self._active or not self.output_stream:
            return
            
        try:
            self.is_speaking = True
            self.output_stream.write(audio)
            self.is_speaking = False
        except Exception as e:
            print(f"Error playing audio: {e}")
            self.is_speaking = False

    def interrupt(self):
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.start_stream()
            except Exception as e:
                print(f"Error interrupting audio: {e}")

    def list_devices(self):
        """List all available audio devices"""
        devices = []
        for i in range(self.p.get_device_count()):
            try:
                device_info = self.p.get_device_info_by_index(i)
                devices.append({
                    'index': device_info['index'],
                    'name': device_info['name'],
                    'input_channels': device_info['maxInputChannels'],
                    'output_channels': device_info['maxOutputChannels'],
                })
            except:
                continue
        return devices

    def update_devices(self, input_device_index=None, output_device_index=None):
        """Update input and output devices"""
        was_active = self._active
        if was_active:
            self.stop()
            
        if input_device_index is not None:
            self.input_device = input_device_index
        if output_device_index is not None:
            self.output_device = output_device_index
            
        if was_active:
            self._active = False  # Reset the active flag before restarting

class ConversationConfig:
    def __init__(
        self,
        extra_body: Optional[dict] = None,
        conversation_config_override: Optional[dict] = None,
    ):
        self.extra_body = extra_body or {}
        self.conversation_config_override = conversation_config_override or {}

class RealTimeChatWidget(QWidget):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.chat_history = []
        self.audio_interface = None
        self.ws = None
        self.conversation_active = False
        self.conversation_thread = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.initUI()
        self.initialize_audio()

    def initialize_audio(self):
        """Initialize audio interface with error handling"""
        try:
            if self.audio_interface:
                self.audio_interface.stop()
            self.audio_interface = PyAudioInterface()
        except Exception as e:
            self.display_message("System", f"Error initializing audio: {str(e)}")
            self.toggle_button.setEnabled(False)

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setObjectName("chatDisplay")
        layout.addWidget(self.chat_display)

        # Button container
        button_container = QFrame()
        button_container.setObjectName("buttonContainer")
        button_layout = QVBoxLayout(button_container)  
        button_layout.setContentsMargins(4, 4, 4, 4)
        button_layout.setSpacing(4)  

        # Start/Stop button
        self.toggle_button = QPushButton("Start Conversation")
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.setFixedHeight(36)  
        self.toggle_button.clicked.connect(self.toggle_conversation)
        button_layout.addWidget(self.toggle_button)

        # Clear chat button
        self.clear_button = QPushButton("Clear Chat")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.setFixedHeight(36)  
        self.clear_button.clicked.connect(self.clear_chat)
        button_layout.addWidget(self.clear_button)

        layout.addWidget(button_container)
        
        self.update_theme()

    def update_theme(self):
        accent_color = self.theme.get_color('accent')
        stop_color = "#e74c3c"  
        
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme.get_color('secondary')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 4px;
                padding: 8px;
            }}
            QPushButton {{
                color: {self.theme.get_color('text')};
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
                font-weight: bold;
                min-width: 120px;
            }}
            QPushButton:disabled {{
                background-color: {self.theme.get_color('secondary_gradient')};
            }}
            #toggleButton {{
                background-color: {stop_color if self.conversation_active else accent_color};
            }}
            #clearButton {{
                background-color: {self.theme.get_color('secondary')};
                border: 1px solid {self.theme.get_color('border')};
            }}
            #clearButton:hover {{
                background-color: {self.theme.get_color('secondary_gradient')};
            }}
            #buttonContainer {{
                background-color: {self.theme.get_color('secondary')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 4px;
            }}
        """)

    def toggle_conversation(self):
        if not self.conversation_active:
            self.start_conversation()
        else:
            self.stop_conversation()
        self.update_theme()  

    def clear_chat(self):
        self.chat_history = []
        self.chat_display.clear()

    def start_conversation(self):
        """Start conversation with proper error handling"""
        if self.conversation_active:
            return

        try:
            # Reset state
            self.conversation_active = True
            self.reconnect_attempts = 0
            self.toggle_button.setEnabled(False)  # Temporarily disable while starting
            self.toggle_button.setText("Starting...")
            self.update_theme()

            # Initialize audio if needed
            if not self.audio_interface:
                self.initialize_audio()

            # Start conversation thread
            self.conversation_thread = threading.Thread(target=self._run_conversation)
            self.conversation_thread.daemon = True  # Make thread daemon so it doesn't block application exit
            self.conversation_thread.start()

        except Exception as e:
            self.display_message("System", f"Error starting conversation: {str(e)}")
            self.stop_conversation()

    def stop_conversation(self):
        """Stop conversation with proper cleanup"""
        if not self.conversation_active:
            return

        self.conversation_active = False
        self.toggle_button.setEnabled(False)  # Temporarily disable while stopping
        self.toggle_button.setText("Stopping...")
        self.update_theme()

        try:
            # Close WebSocket
            if self.ws:
                try:
                    self.ws.close()
                except Exception as e:
                    print(f"Error closing WebSocket: {e}")
                self.ws = None

            # Stop audio
            if self.audio_interface:
                try:
                    self.audio_interface.stop()
                except Exception as e:
                    print(f"Error stopping audio: {e}")

            # Wait for thread to finish with timeout
            if self.conversation_thread and self.conversation_thread.is_alive():
                self.conversation_thread.join(timeout=2.0)

        except Exception as e:
            self.display_message("System", f"Error during cleanup: {str(e)}")
        finally:
            self.toggle_button.setEnabled(True)
            self.toggle_button.setText("Start Conversation")
            self.update_theme()

    def _run_conversation(self):
        """Main conversation loop with improved error handling and recovery"""
        ws_url = self._get_wss_url()
        
        while self.conversation_active and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # Connect to WebSocket
                self.ws = connect(ws_url, timeout=10)  # Add connection timeout
                self.ws.send(json.dumps({
                    "type": "conversation_initiation_client_data",
                    "custom_llm_extra_body": {},
                    "conversation_config_override": {},
                }))

                # Update UI state
                self.toggle_button.setEnabled(True)
                self.toggle_button.setText("Stop Conversation")
                self.update_theme()

                def input_callback(audio):
                    if not self.conversation_active or not self.ws:
                        return
                    try:
                        self.ws.send(json.dumps({
                            "user_audio_chunk": base64.b64encode(audio).decode(),
                        }))
                    except Exception as e:
                        print(f"Error sending audio: {e}")
                        self.handle_connection_error()

                # Start audio processing
                try:
                    self.audio_interface.start(input_callback)
                except Exception as e:
                    self.display_message("System", f"Error starting audio: {str(e)}")
                    self.stop_conversation()
                    return

                # Main message processing loop
                while self.conversation_active:
                    try:
                        message = json.loads(self.ws.recv(timeout=1.0))
                        self._handle_message(message)
                    except TimeoutError:
                        continue  # Normal timeout, just continue
                    except Exception as e:
                        print(f"Error in message loop: {e}")
                        if not self.conversation_active:
                            break
                        self.handle_connection_error()
                        break

            except Exception as e:
                if not self.conversation_active:
                    break
                self.handle_connection_error()

            finally:
                if self.ws:
                    try:
                        self.ws.close()
                    except:
                        pass
                    self.ws = None

        # Final cleanup if we exit the retry loop
        if self.conversation_active:
            self.display_message("System", "Connection lost. Please try again.")
            self.stop_conversation()

    def handle_connection_error(self):
        """Handle connection errors with retry logic"""
        if not self.conversation_active:
            return

        self.reconnect_attempts += 1
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.display_message("System", f"Connection lost. Retrying... (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            time.sleep(2)  # Wait before retrying
        else:
            self.display_message("System", "Connection lost. Maximum retry attempts reached.")
            self.stop_conversation()

    def _handle_message(self, message):
        """Handle incoming messages with error checking"""
        try:
            msg_type = message.get("type")
            
            if msg_type == "audio":
                event = message.get("audio_event")
                if not event:
                    return
                audio = base64.b64decode(event.get("audio_base_64", ""))
                if audio:
                    self.audio_interface.output(audio)
                
            elif msg_type == "agent_response":
                event = message.get("agent_response_event")
                if not event:
                    return
                response = event.get("agent_response", "").strip()
                if response:
                    self.display_message("Assistant", response)
                
            elif msg_type == "user_transcript":
                event = message.get("user_transcription_event")
                if not event:
                    return
                transcript = event.get("user_transcript", "").strip()
                if transcript:
                    self.display_message("You", transcript)
                
            elif msg_type == "interruption":
                self.audio_interface.interrupt()

        except Exception as e:
            print(f"Error handling message: {e}")

    def display_message(self, sender, message):
        """Thread-safe message display"""
        try:
            cursor = self.chat_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(f"\n{sender}: {message}")
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"Error displaying message: {e}")

    def _get_wss_url(self):
        """Get the WebSocket URL for ElevenLabs conversation API"""
        agent_id = "pspjYrUiP27uMM2b9WmZ"
        base_url = "wss://api.elevenlabs.io"
        return f"{base_url}/v1/convai/conversation?agent_id={agent_id}&api_key={ELEVENLABS_API_KEY}"

    def update_input_device(self, device_index):
        """Update the input device for audio capture"""
        self.audio_interface.input_device = device_index
        # If we're currently recording, restart the audio stream
        if self.conversation_active:
            self.stop_conversation()
            self.start_conversation()
