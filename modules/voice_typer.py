import pyaudio
import wave
import numpy as np
import os
from threading import Thread, Event
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QCheckBox, QPushButton, QComboBox, QMessageBox, QSizePolicy
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from config import WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT
from openai import OpenAI
import keyboard
import time
from dotenv import load_dotenv

load_dotenv()

class VoiceTyperThread(QThread):
    text_ready = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    transcribing_status = pyqtSignal(str)

    def __init__(self, input_device_index=None):
        super().__init__()
        self.stop_event = Event()
        self.input_device_index = input_device_index
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)

    def run(self):
        audio = None
        stream = None
        try:
            audio = pyaudio.PyAudio()
            try:
                device_info = audio.get_device_info_by_index(self.input_device_index)
            except Exception as e:
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
                self.error_occurred.emit("Could not access microphone. Please check your audio settings.")
                return
            frames = []
            while not self.stop_event.is_set():
                try:
                    data = stream.read(512, exception_on_overflow=False)
                    frames.append(data)
                    level = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                    self.audio_level.emit(level)
                except Exception as e:
                    self.error_occurred.emit("Error recording audio")
                    break
            self.transcribing_status.emit("Processing audio...")
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if audio:
                try:
                    audio.terminate()
                except Exception:
                    pass
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
                self.error_occurred.emit("Error saving audio recording")
                return
            try:
                self.transcribing_status.emit("Converting speech to text...")

                with open("voice_record.wav", "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        model="gpt-4o-mini-transcribe",
                        file=audio_file,
                        response_format="text"
                    )

                if transcription:
                    self.text_ready.emit(transcription)
                    # Clean up temporary audio file
                    try:
                        os.remove("voice_record.wav")
                    except Exception:
                        pass
                else:
                    self.error_occurred.emit("No speech detected")
            except Exception as e:
                self.error_occurred.emit("Error transcribing speech")
        except Exception as e:
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
        keyboard.add_hotkey('ctrl+space', self.toggle_recording)
        keyboard.add_hotkey('ctrl+q', self.close_app)

    def cleanup(self):
        try:
            if self.recorder_thread and self.recorder_thread.isRunning():
                self.stop_recording()
            keyboard.remove_hotkey('ctrl+space')
            keyboard.remove_hotkey('ctrl+q')
        except Exception:
            pass

    def initUI(self):
        styles = self.theme.get_styles()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self.theme.PADDING, self.theme.PADDING, self.theme.PADDING, self.theme.PADDING)
        layout.setSpacing(self.theme.SPACING)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_container = QFrame()
        main_container.setStyleSheet(styles['main_container'])
        main_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(self.theme.PADDING, self.theme.PADDING, self.theme.PADDING, self.theme.PADDING)
        main_layout.setSpacing(self.theme.SPACING)

        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("Ctrl+Space")
        self.status_label.setFont(self.theme.SMALL_FONT)
        self.status_label.setStyleSheet(styles['label'])

        settings_button = QPushButton("⚙")
        settings_button.setFont(self.theme.SMALL_FONT)
        settings_button.setStyleSheet(styles['button_icon'])
        settings_button.clicked.connect(self.toggle_settings)

        close_button = QPushButton("✕")
        close_button.setFont(self.theme.SMALL_FONT)
        close_button.setStyleSheet(styles['button_close'])
        close_button.clicked.connect(self.close_app)

        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(settings_button)
        top_bar.addWidget(close_button)
        main_layout.addLayout(top_bar)

        # Record button
        self.record_button = QPushButton("Start/Stop Recording")
        self.record_button.setFont(self.theme.SMALL_FONT)
        self.record_button.setStyleSheet(styles['button'])
        self.record_button.clicked.connect(self.toggle_recording)
        main_layout.addWidget(self.record_button)

        # Audio visualization
        viz_container = QFrame()
        viz_container.setStyleSheet("background: transparent;")
        viz_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        viz_layout = QHBoxLayout(viz_container)
        viz_layout.setContentsMargins(0, 0, 0, 0)
        viz_layout.setSpacing(0)
        self.viz_bar = QFrame()
        self.viz_bar.setStyleSheet(styles['viz_bar'])
        self.viz_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        viz_layout.addWidget(self.viz_bar)
        main_layout.addWidget(viz_container)

        # Settings panel
        self.settings_panel = QFrame()
        self.settings_panel.setVisible(False)
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(0, self.theme.SPACING, 0, 0)
        settings_layout.setSpacing(self.theme.SPACING)

        self.mic_combo = QComboBox()
        self.mic_combo.setFont(self.theme.SMALL_FONT)
        self.mic_combo.setStyleSheet(styles['combo'])

        input_devices = []
        hyperx_index = None
        audio = pyaudio.PyAudio()
        try:
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    name = device_info['name']
                    input_devices.append((name, i))
                    if 'hyperx' in name.lower():
                        hyperx_index = len(input_devices) - 1
        finally:
            audio.terminate()
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
        auto_enter_check.setStyleSheet(styles['checkbox'])

        settings_layout.addWidget(self.mic_combo)
        settings_layout.addWidget(auto_enter_check)
        main_layout.addWidget(self.settings_panel)
        layout.addWidget(main_container)

    def toggle_settings(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())

    def toggle_recording(self):
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

    def stop_recording(self):
        if self.is_recording and self.recorder_thread:
            self.recorder_thread.stop_event.set()
            self.recorder_thread.wait()
            self.is_recording = False

    def handle_text(self, text):
        if text:
            self.status_label.setText('Ready')
            styles = self.theme.get_styles()
            self.status_label.setStyleSheet(styles['label'])
            # Give user a moment to focus the target window
            time.sleep(0.5)
            keyboard.write(text)

    def handle_error(self, error_message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(error_message)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStyleSheet(self.theme.get_styles()['messagebox'])
        msg_box.exec()
        self.is_recording = False
        self.recorder_thread = None

    def update_audio_level(self, level):
        max_height = 40
        height = int(max_height * min(1.0, level / 3000))
        self.viz_bar.setFixedHeight(height)

    def update_status(self, message):
        self.status_label.setText(message)
        styles = self.theme.get_styles()
        self.status_label.setStyleSheet(styles['label'])

    def close_app(self):
        if self.parent:
            self.parent.close()
        else:
            self.close()
