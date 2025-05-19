import pyaudio
import wave
import numpy as np
import os
from threading import Thread, Event
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTextEdit, QFrame, QCheckBox, QPushButton, QComboBox, QMessageBox, QSizePolicy
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from config import WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT
from openai import OpenAI
import keyboard
import time

# Helper to read API key directly from .env file
def get_api_key_from_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_path):
        raise ValueError(f".env file not found at {env_path}")
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip().startswith('OPENAI_API_KEY='):
                return line.strip().split('=', 1)[1]
    raise ValueError("OPENAI_API_KEY not found in .env file")

class VoiceTyperThread(QThread):
    text_ready = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    transcribing_status = pyqtSignal(str)

    def __init__(self, input_device_index=None):
        super().__init__()
        self.stop_event = Event()
        self.input_device_index = input_device_index
        # Always use the API key from the .env file
        api_key = get_api_key_from_env_file()
        print("API KEY BEING USED:", api_key)  # For debugging
        self.client = OpenAI(api_key=api_key)

    def run(self):
        audio = None
        stream = None
        try:
            audio = pyaudio.PyAudio()
            try:
                device_info = audio.get_device_info_by_index(self.input_device_index)
                print(f"Using audio device: {device_info['name']} (Index: {self.input_device_index})")
            except Exception as e:
                print(f"Error getting device info for index {self.input_device_index}: {e}")
                self.error_occurred.emit(f"Could not access specified microphone (index {self.input_device_index})")
                return
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
                    level = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                    self.audio_level.emit(level)
                except Exception as e:
                    print(f"Error reading audio data: {e}")
                    self.error_occurred.emit("Error recording audio")
                    break
            print("Stopped recording, processing audio...")
            self.transcribing_status.emit("Processing audio...")
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
            try:
                print("Transcribing audio...")
                self.transcribing_status.emit("Converting speech to text...")
                
                with open("voice_record.wav", "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        model="gpt-4o-mini-transcribe",
                        file=audio_file,
                        response_format="text"
                    )
                
                if transcription:
                    print(f"Transcribed text: {transcription}")
                    self.text_ready.emit(transcription)
                else:
                    self.error_occurred.emit("No speech detected")
            except Exception as e:
                print(f"Error transcribing audio: {e}")
                self.error_occurred.emit("Error transcribing speech")
        except Exception as e:
            print(f"Unexpected error in recording thread: {e}")
            self.error_occurred.emit("An unexpected error occurred")
        finally:
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
    def __init__(self, parent, theme):
        super().__init__()
        self.parent = parent
        self.theme = theme
        self.recorder_thread = None
        self.is_recording = False
        self.selected_input_device = 2
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.initUI()
        self.setup_global_hotkey()

    def setup_global_hotkey(self):
        print("Setting up global hotkey (Ctrl+Space)")
        keyboard.add_hotkey('ctrl+space', self.toggle_recording)
        print("Global hotkey connected")
        # Add global exit shortcut
        keyboard.add_hotkey('ctrl+q', self.close_app)
        print("Global exit hotkey (Ctrl+Q) connected")

    def cleanup(self):
        try:
            if self.recorder_thread and self.recorder_thread.isRunning():
                self.stop_recording()
            keyboard.remove_hotkey('ctrl+space')
            keyboard.remove_hotkey('ctrl+q')
        except Exception as e:
            print(f"Error during voice typer cleanup: {str(e)}")

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_container = QFrame()
        main_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('primary_gradient')},
                    stop:1 {self.theme.get_color('primary')});
                border-radius: 12px;
            }}
        """)
        main_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)
        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("Ctrl+Space")
        self.status_label.setFont(self.theme.SMALL_FONT)
        self.status_label.setStyleSheet(f"color: {self.theme.get_color('text_secondary')};")
        settings_button = QPushButton("⚙")
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
        # Close button
        close_button = QPushButton("✕")
        close_button.setFont(self.theme.SMALL_FONT)
        close_button.setStyleSheet(f"""
            QPushButton {{
                color: {self.theme.get_color('text_secondary')};
                background: transparent;
                border: none;
                padding: 0 4px;
            }}
            QPushButton:hover {{
                color: #FF5C5C;
            }}
        """)
        close_button.clicked.connect(self.close_app)
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(settings_button)
        # Add spacing between settings and close button
        spacer = QFrame()
        spacer.setFixedWidth(8)
        top_bar.addWidget(spacer)
        top_bar.addWidget(close_button)
        main_layout.addLayout(top_bar)
        # Manual record button
        self.record_button = QPushButton("Start/Stop Recording")
        self.record_button.setFont(self.theme.SMALL_FONT)
        self.record_button.clicked.connect(self.toggle_recording)
        main_layout.addWidget(self.record_button)
        # Audio visualization (single bar)
        viz_container = QFrame()
        viz_container.setStyleSheet("background: transparent;")
        viz_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        viz_layout = QHBoxLayout(viz_container)
        viz_layout.setContentsMargins(0, 0, 0, 0)
        viz_layout.setSpacing(4)
        self.viz_bar = QFrame()
        self.viz_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.get_color('accent')};
                border-radius: 4px;
            }}
        """)
        self.viz_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        viz_layout.addWidget(self.viz_bar)
        main_layout.addWidget(viz_container)
        # Settings panel (hidden by default)
        self.settings_panel = QFrame()
        self.settings_panel.setVisible(False)
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(0, 4, 0, 0)
        settings_layout.setSpacing(4)
        self.mic_combo = QComboBox()
        self.mic_combo.setFont(self.theme.SMALL_FONT)
        self.mic_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.theme.get_color('primary')};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px 4px;
            }}
            QComboBox QAbstractItemView {{
                color: white;
                background: {self.theme.get_color('primary')};
            }}
        """)
        input_devices = []
        hyperx_index = None
        for i in range(pyaudio.PyAudio().get_device_count()):
            device_info = pyaudio.PyAudio().get_device_info_by_index(i)
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
            lambda idx: self.change_microphone(input_devices[idx][1])
        )
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
        settings_layout.addWidget(self.mic_combo)
        settings_layout.addWidget(auto_enter_check)
        main_layout.addWidget(self.settings_panel)
        layout.addWidget(main_container)

    def toggle_settings(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
        print("Settings panel toggled")  # Debug print

    def toggle_recording(self):
        print("toggle_recording called (from hotkey or button)")
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def change_microphone(self, device_index):
        self.selected_input_device = device_index
        if self.is_recording:
            self.stop_recording()
            self.start_recording()

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recorder_thread = VoiceTyperThread(self.selected_input_device)
            self.recorder_thread.text_ready.connect(self.handle_text)
            self.recorder_thread.error_occurred.connect(self.handle_error)
            self.recorder_thread.audio_level.connect(self.update_audio_level)
            self.recorder_thread.transcribing_status.connect(self.update_status)
            self.recorder_thread.start()
            print("Recording started successfully")

    def stop_recording(self):
        if self.is_recording and self.recorder_thread:
            self.recorder_thread.stop_event.set()
            self.recorder_thread.wait()
            self.is_recording = False
            print("Recording stopped successfully")

    def handle_text(self, text):
        if text:
            print(f"Received transcribed text: {text}")
            self.status_label.setText('Ready')
            self.status_label.setStyleSheet(f"color: {self.theme.get_color('text_secondary')};")
            # Give user a moment to focus the target window
            time.sleep(0.5)
            keyboard.write(text)

    def handle_error(self, error_message):
        print(f"Voice typer error: {error_message}")
        QMessageBox.warning(self, "Warning", error_message)
        self.is_recording = False
        self.recorder_thread = None

    def update_audio_level(self, level):
        max_height = 40
        height = int(max_height * min(1.0, level / 3000))
        self.viz_bar.setFixedHeight(height)

    def update_status(self, message):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {self.theme.get_color('text_secondary')};")

    def close_app(self):
        if self.parent:
            self.parent.close()
        else:
            self.close()
