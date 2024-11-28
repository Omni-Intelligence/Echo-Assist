import pyaudio
import wave
import numpy as np
import keyboard
import faster_whisper
import torch.cuda
from threading import Thread, Event
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTextEdit, QFrame, QCheckBox
from PyQt6.QtCore import pyqtSignal, QThread, Qt

class VoiceTyperThread(QThread):
    text_ready = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    transcribing_status = pyqtSignal(str)

    def __init__(self, input_device_index=None):
        super().__init__()
        self.stop_event = Event()
        self.input_device_index = input_device_index
        try:
            # Use small model for faster processing
            self.model = faster_whisper.WhisperModel("tiny.en", 
                                                   device='cuda' if torch.cuda.is_available() else 'cpu',
                                                   compute_type="float32")
        except Exception as e:
            print(f"Error initializing Whisper model: {e}")
            self.error_occurred.emit("Failed to initialize speech recognition model")
            return

    def run(self):
        audio = None
        stream = None
        try:
            # Initialize audio
            audio = pyaudio.PyAudio()
            
            # Print available input devices for debugging
            print("\nAvailable Input Devices:")
            for i in range(audio.get_device_count()):
                dev = audio.get_device_info_by_index(i)
                if dev['maxInputChannels'] > 0:
                    print(f"Index {i}: {dev['name']}")
            
            # Use specified device or fall back to default
            if self.input_device_index is not None:
                try:
                    device_info = audio.get_device_info_by_index(self.input_device_index)
                    print(f"\nUsing selected audio device: {device_info['name']} (Index: {self.input_device_index})")
                except Exception as e:
                    print(f"Error getting selected device info: {e}")
                    device_info = audio.get_default_input_device_info()
                    print(f"Falling back to default device: {device_info['name']}")
                    self.input_device_index = None
            else:
                device_info = audio.get_default_input_device_info()
                print(f"\nUsing default audio device: {device_info['name']}")
            
            # Open stream with error handling
            try:
                stream = audio.open(
                    rate=16000,
                    format=pyaudio.paInt16,
                    channels=1,
                    input=True,
                    frames_per_buffer=512,
                    input_device_index=self.input_device_index
                )
            except Exception as e:
                print(f"Error opening audio stream: {e}")
                self.error_occurred.emit("Could not access microphone. Please check your audio settings.")
                return
            
            frames = []
            print("Started recording...")
            
            while not self.stop_event.is_set():
                try:
                    data = stream.read(512, exception_on_overflow=False)
                    frames.append(data)
                    # Emit audio level for visualization
                    level = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                    self.audio_level.emit(level)
                except Exception as e:
                    print(f"Error reading audio data: {e}")
                    self.error_occurred.emit("Error recording audio")
                    break
            
            print("Stopped recording, processing audio...")
            self.transcribing_status.emit("Processing audio...")
            
            # Clean up audio resources
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    print(f"Error closing stream: {e}")
            
            if audio:
                try:
                    audio.terminate()
                except Exception as e:
                    print(f"Error terminating audio: {e}")
            
            if not frames:
                self.error_occurred.emit("No audio recorded")
                return
            
            # Save recording with error handling
            try:
                with wave.open("voice_record.wav", 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(frames))
            except Exception as e:
                print(f"Error saving audio file: {e}")
                self.error_occurred.emit("Error saving audio recording")
                return

            # Transcribe with error handling
            try:
                print("Transcribing audio...")
                self.transcribing_status.emit("Converting speech to text...")
                segments, info = self.model.transcribe(
                    "voice_record.wav",
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                # Collect all text from segments
                full_text = ""
                for segment in segments:
                    if segment.text:
                        full_text += segment.text.strip() + " "
                
                full_text = full_text.strip()
                if full_text:
                    print(f"Transcribed text: {full_text}")
                    self.text_ready.emit(full_text)
                else:
                    self.error_occurred.emit("No speech detected")
                    
            except Exception as e:
                print(f"Error transcribing audio: {e}")
                self.error_occurred.emit("Error transcribing speech")
                
        except Exception as e:
            print(f"Unexpected error in recording thread: {e}")
            self.error_occurred.emit("An unexpected error occurred")
        finally:
            # Ensure resources are cleaned up
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            if audio:
                try:
                    audio.terminate()
                except:
                    pass
            self.stop_event.clear()

class VoiceTyperWidget(QWidget):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.recorder_thread = None
        self.is_recording = False
        self.max_level_width = 200
        self.auto_enter = True  # Changed to True for default state
        self.selected_input_device = None
        self.initUI()
        
        # Initialize keyboard hook with better event handling
        self.setup_keyboard_hook()

    def setup_keyboard_hook(self):
        """Set up keyboard hook with proper event handling"""
        try:
            keyboard.unhook_all()  # Clean up any existing hooks
            keyboard.on_press_key("space", self.handle_hotkey, suppress=False)  # Changed to not suppress
        except Exception as e:
            print(f"Error setting up keyboard hook: {e}")

    def showEvent(self, event):
        """Called when widget is shown"""
        super().showEvent(event)
        self.setup_keyboard_hook()

    def hideEvent(self, event):
        """Called when widget is hidden"""
        super().hideEvent(event)
        try:
            keyboard.unhook_all()  # Remove keyboard hooks when hidden
        except Exception as e:
            print(f"Error removing keyboard hook: {e}")

    def initUI(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Instructions
        instructions = QLabel("Press Ctrl+Space to\nstart/stop voice typing")
        instructions.setFont(self.theme.SMALL_FONT)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.get_color('text')};
                background-color: {self.theme.get_color('primary')};
                padding: 4px;
                qproperty-alignment: AlignCenter;
                border-radius: 4px;
            }}
        """)
        layout.addWidget(instructions)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setFont(self.theme.SMALL_FONT)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.get_color('text')};
                background-color: {self.theme.get_color('primary')};
                padding: 6px;
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.status_label)

        # Audio level indicator
        self.level_indicator = QFrame()
        self.level_indicator.setFixedHeight(4)
        self.level_indicator.setFixedWidth(0)
        self.level_indicator.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.get_color('accent')};
                border-radius: 2px;
            }}
        """)
        
        # Level indicator container
        level_container = QFrame()
        level_container.setFixedHeight(12)
        level_container.setMinimumWidth(self.max_level_width)
        level_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.get_color('secondary_gradient')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;
            }}
        """)
        
        # Center the level indicator in its container
        level_layout = QHBoxLayout(level_container)
        level_layout.setContentsMargins(4, 4, 4, 4)
        level_layout.addWidget(self.level_indicator)
        level_layout.addStretch()
        
        layout.addWidget(level_container)

        # Auto-enter checkbox
        self.auto_enter_checkbox = QCheckBox("Auto-press Enter")
        self.auto_enter_checkbox.setFont(self.theme.SMALL_FONT)
        self.auto_enter_checkbox.setChecked(True)  # Set checkbox to checked by default
        self.auto_enter_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {self.theme.get_color('text')};
                padding: 4px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme.get_color('accent')};
            }}
        """)
        self.auto_enter_checkbox.stateChanged.connect(self.toggle_auto_enter)
        layout.addWidget(self.auto_enter_checkbox)

        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(self.theme.SMALL_FONT)
        self.text_display.setStyleSheet(f"""
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
        layout.addWidget(self.text_display)

    def update_theme(self):
        """Update widget styles when theme changes"""
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.get_color('text')};
                background-color: {self.theme.get_color('primary')};
                padding: 6px;
                border-radius: 4px;
            }}
        """)

        self.level_indicator.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.get_color('accent')};
                border-radius: 2px;
            }}
        """)
        
        self.text_display.setStyleSheet(f"""
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

    def toggle_auto_enter(self, state):
        """Toggle the auto-enter feature"""
        self.auto_enter = bool(state)

    def handle_hotkey(self, event):
        """Handle Ctrl+Space hotkey with better event processing"""
        if not self.isVisible():
            return
            
        if keyboard.is_pressed('ctrl'):
            if self.is_recording:
                self.stop_recording()
            else:
                self.start_recording()

    def update_input_device(self, device_index):
        """Update the input device for audio capture"""
        print(f"VoiceTyper: Updating input device to index: {device_index}")
        self.selected_input_device = device_index
        # If currently recording, restart with new device
        if self.is_recording:
            self.stop_recording()
            self.start_recording()

    def start_recording(self):
        """Start recording with the selected input device"""
        if not self.is_recording:
            try:
                self.is_recording = True
                self.status_label.setText("Recording...")
                
                # Clean up any existing recorder thread
                if self.recorder_thread and self.recorder_thread.isRunning():
                    self.recorder_thread.wait()
                    self.recorder_thread = None
                
                # Create new recorder thread with selected device
                self.recorder_thread = VoiceTyperThread(input_device_index=self.selected_input_device)
                self.recorder_thread.text_ready.connect(self.handle_text)
                self.recorder_thread.error_occurred.connect(self.handle_error)
                self.recorder_thread.audio_level.connect(self.update_audio_level)
                self.recorder_thread.transcribing_status.connect(self.update_status)
                self.recorder_thread.start()
            except Exception as e:
                self.handle_error(f"Error starting recording: {str(e)}")
                self.stop_recording()

    def stop_recording(self):
        if self.recorder_thread:
            self.is_recording = False
            self.recorder_thread.stop_event.set()
            self.recorder_thread = None
            self.status_label.setText('Processing... Please wait')
            self.status_label.setStyleSheet(f"""
                color: {self.theme.get_color('text')};
                background-color: {self.theme.get_color('primary')};
                padding: 6px;
                border-radius: 4px;
            """)

    def handle_text(self, text):
        """Handle transcribed text"""
        try:
            # Preview the text first
            self.text_display.setPlainText(text)
            print(f"Received transcribed text: {text}")
            
            # Write the text without adding extra spaces
            if text:
                keyboard.write(text)
                if self.auto_enter:
                    keyboard.press_and_release('enter')
            
            # Reset the UI
            self.status_label.setText('Ready')
            self.status_label.setStyleSheet(f"""
                color: {self.theme.get_color('text')};
                background-color: {self.theme.get_color('primary')};
                padding: 6px;
                border-radius: 4px;
            """)
        except Exception as e:
            print(f"Error in handle_text: {e}")
            self.status_label.setText("Error processing text")

    def handle_error(self, error_message):
        """Handle errors from the recording thread"""
        print(f"Error in voice typer: {error_message}")
        self.status_label.setText(f"Error: {error_message}\nPress Ctrl+Space to try again")
        self.status_label.setStyleSheet(f"""
            color: white;
            background-color: #FF3B30;
            padding: 6px;
            border-radius: 4px;
        """)
        self.is_recording = False
        self.recorder_thread = None

    def update_audio_level(self, level):
        # Normalize level and constrain to max width
        normalized_level = min(100, level / 100)
        width = int(normalized_level * self.max_level_width)
        self.level_indicator.setFixedWidth(width)

    def update_status(self, message):
        """Update the status label with processing information"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            color: {self.theme.get_color('text')};
            background-color: {self.theme.get_color('primary')};
            padding: 6px;
            border-radius: 4px;
        """)
