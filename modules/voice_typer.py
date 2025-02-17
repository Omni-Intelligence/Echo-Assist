import pyaudio
import wave
import numpy as np
import keyboard
import faster_whisper
import torch.cuda
from threading import Thread, Event
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTextEdit, QFrame, QCheckBox, QPushButton, QComboBox
from PyQt6.QtCore import pyqtSignal, QThread, Qt

class VoiceTyperThread(QThread):
    text_ready = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    transcribing_status = pyqtSignal(str)

    def __init__(self, input_device_index=None):
        super().__init__()
        self.stop_event = Event()
        # Always use the specified input device index
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
            
            # Use specified device (index 2 for HyperX SoloCast)
            try:
                device_info = audio.get_device_info_by_index(self.input_device_index)
                print(f"\nUsing audio device: {device_info['name']} (Index: {self.input_device_index})")
            except Exception as e:
                print(f"Error getting device info for index {self.input_device_index}: {e}")
                self.error_occurred.emit(f"Could not access specified microphone (index {self.input_device_index})")
                return
            
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

def find_hyperx_device():
    """Find the HyperX SoloCast device index"""
    audio = pyaudio.PyAudio()
    hyperx_index = None
    
    try:
        for i in range(audio.get_device_count()):
            dev = audio.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0 and 'HyperX SoloCast' in dev['name']:
                # Prefer devices with higher channel counts or sampling rates
                if hyperx_index is None or (
                    dev['maxInputChannels'] > audio.get_device_info_by_index(hyperx_index)['maxInputChannels']
                ):
                    hyperx_index = i
        
        if hyperx_index is not None:
            print(f"Found HyperX SoloCast at index {hyperx_index}")
            return hyperx_index
        return None
    finally:
        audio.terminate()

class VoiceTyperWidget(QWidget):
    def __init__(self, parent, theme):
        super().__init__()
        self.parent = parent
        self.theme = theme
        self.recorder_thread = None
        self.is_recording = False
        self.auto_enter = True
        self.selected_input_device = 2
        self.settings_visible = False
        self.initUI()
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
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)  # Reduced spacing
        
        # Single container for everything
        main_container = QFrame()
        main_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('primary_gradient')},
                    stop:1 {self.theme.get_color('primary')});
                border-radius: 12px;
            }}
        """)
        
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(12, 8, 12, 8)  # Reduced vertical margins
        main_layout.setSpacing(4)  # Reduced spacing
        
        # Top bar with minimal elements
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        # Minimal status text
        self.status_label = QLabel("Ctrl+Space")
        self.status_label.setFont(self.theme.SMALL_FONT)
        self.status_label.setStyleSheet(f"color: {self.theme.get_color('text_secondary')};")
        
        # Settings button (⚙)
        settings_button = QPushButton("⚙")
        settings_button.setFixedSize(16, 16)
        settings_button.setFont(self.theme.SMALL_FONT)
        settings_button.setStyleSheet(f"""
            QPushButton {{
                color: {self.theme.get_color('text_secondary')};
                background: transparent;
                border: none;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {self.theme.get_color('text')};
            }}
        """)
        settings_button.clicked.connect(self.toggle_settings)
        
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(settings_button)
        
        main_layout.addLayout(top_bar)
        
        # Audio visualization container
        viz_container = QFrame()
        viz_container.setFixedHeight(40)  # Reduced height
        viz_container.setStyleSheet("background: transparent;")
        
        viz_layout = QHBoxLayout(viz_container)
        viz_layout.setContentsMargins(0, 0, 0, 0)
        viz_layout.setSpacing(4)
        
        # Create visualization bars
        self.viz_bars = []
        for _ in range(13):
            bar = QFrame()
            bar.setFixedWidth(4)
            bar.setFixedHeight(0)
            bar.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.theme.get_color('accent')};
                    border-radius: 2px;
                }}
            """)
            viz_layout.addWidget(bar)
            self.viz_bars.append(bar)
        
        main_layout.addWidget(viz_container)
        
        # Settings panel (hidden by default)
        self.settings_panel = QFrame()
        self.settings_panel.setVisible(False)
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(0, 4, 0, 0)  # Reduced top margin
        settings_layout.setSpacing(4)
        
        # Microphone selection
        self.mic_combo = QComboBox()
        self.mic_combo.setFont(self.theme.SMALL_FONT)
        self.mic_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.theme.get_color('primary')};
                color: {self.theme.get_color('text')};
                border: none;
                border-radius: 4px;
                padding: 2px 4px;
            }}
        """)
        
        # Get available input devices
        input_devices = []
        hyperx_index = None
        for i in range(self.parent.p.get_device_count()):
            device_info = self.parent.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                name = device_info['name']
                input_devices.append((name, i))
                if 'hyperx' in name.lower():
                    hyperx_index = len(input_devices) - 1
        
        for name, _ in input_devices:
            self.mic_combo.addItem(name)
            
        if hyperx_index is not None:
            self.mic_combo.setCurrentIndex(hyperx_index)
        
        self.mic_combo.currentIndexChanged.connect(
            lambda idx: self.parent.change_microphone(input_devices[idx][1])
        )
        
        # Auto-enter toggle
        auto_enter_check = QCheckBox("Auto-Enter")
        auto_enter_check.setFont(self.theme.SMALL_FONT)
        auto_enter_check.setChecked(True)
        auto_enter_check.setStyleSheet(f"""
            QCheckBox {{
                color: {self.theme.get_color('text_secondary')};
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                background: {self.theme.get_color('primary')};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background: {self.theme.get_color('accent')};
            }}
        """)
        auto_enter_check.stateChanged.connect(self.toggle_auto_enter)
        
        settings_layout.addWidget(self.mic_combo)
        settings_layout.addWidget(auto_enter_check)
        
        main_layout.addWidget(self.settings_panel)
        
        # Main layout
        layout.addWidget(main_container)
        
    def toggle_settings(self):
        """Toggle the settings panel visibility"""
        self.settings_visible = not self.settings_visible
        self.settings_panel.setVisible(self.settings_visible)
        # Adjust parent window size
        if self.settings_visible:
            self.parent.resize(300, 160)
        else:
            self.parent.resize(300, 80)

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
        """Start recording audio"""
        if not self.is_recording:
            self.is_recording = True
            self.status_label.setText("Recording...")
            self.recorder_thread = VoiceTyperThread(input_device_index=self.selected_input_device)
            self.recorder_thread.text_ready.connect(self.handle_text)
            self.recorder_thread.audio_level.connect(self.update_audio_level)
            self.recorder_thread.error_occurred.connect(self.handle_error)
            self.recorder_thread.transcribing_status.connect(self.update_status)
            self.recorder_thread.start()

    def stop_recording(self):
        if self.recorder_thread:
            self.is_recording = False
            self.recorder_thread.stop_event.set()
            self.recorder_thread = None
            self.status_label.setText('Processing... Please wait')
            self.status_label.setStyleSheet(f"""
                color: {self.theme.get_color('text_secondary')};
            """)

    def handle_text(self, text):
        """Handle transcribed text"""
        try:
            # Preview the text first
            print(f"Received transcribed text: {text}")
            
            # Write the text without adding extra spaces
            if text:
                keyboard.write(text)
                if self.auto_enter:
                    keyboard.press_and_release('enter')
            
            # Reset the UI
            self.status_label.setText('Ready')
            self.status_label.setStyleSheet(f"color: {self.theme.get_color('text_secondary')};")
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
        """Update the audio visualization"""
        max_height = 40  # Taller bars
        center_idx = len(self.viz_bars) // 2
        
        for i, bar in enumerate(self.viz_bars):
            # Create a smoother wave pattern
            distance = abs(i - center_idx)
            height = int(max_height * level * max(0, 1 - (distance * 0.15)))  # Smoother falloff
            bar.setFixedHeight(height)

    def update_status(self, message):
        """Update the status label with processing information"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {self.theme.get_color('text_secondary')};")

    def toggle_auto_enter(self, state):
        """Toggle the auto-enter feature"""
        self.auto_enter = bool(state)
