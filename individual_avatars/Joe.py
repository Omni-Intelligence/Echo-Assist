import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QTextEdit, QFrame, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon
import pyaudio, wave, numpy, collections, os
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from elevenlabs import stream
import faster_whisper
import torch.cuda
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

system_prompt = {
    'role': 'system', 
    'content': '''You are Brian, a knowledgeable and approachable data and programming educator. 
    Focus on teaching and guiding me through coding tasks, explaining concepts clearly with simple examples. 
    Be patient, supportive, and confident, ensuring I understand while challenging me when needed. 
    Your style is direct and practical, with a bit of humor. Absolutely no lists please.
    Treat this like a real conversation, keeping responses concise and engaging. 
    Never mention that you are an AI.'''
}

model = faster_whisper.WhisperModel(model_size_or_path="tiny.en", device='cuda' if torch.cuda.is_available() else 'cpu')
answer = ""
history = []

def generate(messages):
    global answer
    answer = ""        
    for chunk in openai_client.chat.completions.create(model="gpt-4o-mini", messages=messages, stream=True):
        if (text_chunk := chunk.choices[0].delta.content):
            answer += text_chunk
            yield text_chunk

def get_levels(data, long_term_noise_level, current_noise_level):
    pegel = numpy.abs(numpy.frombuffer(data, dtype=numpy.int16)).mean()
    long_term_noise_level = long_term_noise_level * 0.995 + pegel * (1.0 - 0.995)
    current_noise_level = current_noise_level * 0.920 + pegel * (1.0 - 0.920)
    return pegel, long_term_noise_level, current_noise_level

class AudioRecorderThread(QThread):
    finished = pyqtSignal(str)
    audio_level = pyqtSignal(float)

    def run(self):
        audio = pyaudio.PyAudio()
        py_stream = audio.open(rate=16000, format=pyaudio.paInt16, channels=1, input=True, frames_per_buffer=512)
        audio_buffer = collections.deque(maxlen=int((16000 // 512) * 0.5))
        frames, long_term_noise_level, current_noise_level, voice_activity_detected = [], 0.0, 0.0, False
        silence_duration = 0

        while not self.isInterruptionRequested():
            data = py_stream.read(512)
            pegel, long_term_noise_level, current_noise_level = get_levels(data, long_term_noise_level, current_noise_level)
            self.audio_level.emit(current_noise_level)
            audio_buffer.append(data)

            if voice_activity_detected:
                frames.append(data)
                if current_noise_level < ambient_noise_level + 100:
                    silence_duration += 1
                    if silence_duration > 30:  # About 1.5 seconds of silence
                        break
                else:
                    silence_duration = 0
            
            if not voice_activity_detected and current_noise_level > long_term_noise_level + 300:
                voice_activity_detected = True
                ambient_noise_level = long_term_noise_level
                frames.extend(list(audio_buffer))

        py_stream.stop_stream()
        py_stream.close()
        audio.terminate()        

        if len(frames) > 0:
            with wave.open("voice_record.wav", 'wb') as wf:
                wf.setparams((1, audio.get_sample_size(pyaudio.paInt16), 16000, 0, 'NONE', 'NONE'))
                wf.writeframes(b''.join(frames))
            
            user_text = " ".join(seg.text for seg in model.transcribe("voice_record.wav", language="en")[0])
            self.finished.emit(user_text)
        else:
            self.finished.emit("")

class AIResponseThread(QThread):
    response_ready = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        generator = generate(self.messages)
        ai_response = ""
        for chunk in generator:
            ai_response += chunk
            self.progress_update.emit(chunk)
        self.response_ready.emit(ai_response)

class AIVoiceChatApp(QWidget):
    def __init__(self):
        super().__init__()
        self.chat_visible = True
        self.recorder_thread = None
        self.response_thread = None
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                border: 2px solid #007AFF;
                border-radius: 25px;
                font-size: 16px;
                padding: 15px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #007AFF;
            }
            QPushButton:pressed {
                background-color: #0056B3;
            }
            QLabel {
                font-size: 18px;
                margin: 10px;
            }
            QTextEdit {
                background-color: #2C2C2C;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                margin: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        self.title_label = QLabel('AI Voice Assistant')
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont('Segoe UI', 28, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        self.status_label = QLabel('Ready to start')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont('Segoe UI', 16))
        layout.addWidget(self.status_label)

        self.record_button = QPushButton()
        self.record_button.setIcon(QIcon('audio_icon.png'))
        self.record_button.setIconSize(QSize(40, 40))
        self.record_button.setFixedSize(80, 80)
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.audio_level_indicator = QLabel()
        self.audio_level_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_level_indicator.setStyleSheet("color: #007AFF;")  # Match button color
        layout.addWidget(self.audio_level_indicator)

        self.toggle_chat_button = QPushButton("Hide Chat")
        self.toggle_chat_button.setFixedSize(150, 40)  # Increased height to 40
        self.toggle_chat_button.clicked.connect(self.toggle_chat)
        layout.addWidget(self.toggle_chat_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.conversation_text = QTextEdit()
        self.conversation_text.setReadOnly(True)
        self.conversation_text.setMinimumHeight(200)  # Reduced minimum height
        layout.addWidget(self.conversation_text)

        self.setLayout(layout)
        self.setWindowTitle('AI Voice Assistant')
        self.adjust_size()

        self.audio_update_timer = QTimer(self)
        self.audio_update_timer.timeout.connect(self.update_audio_level)
        self.audio_update_timer.start(100)  # Update every 100ms

    def adjust_size(self):
        if self.chat_visible:
            self.setGeometry(300, 300, 400, 500)  # Smaller height
        else:
            self.setGeometry(300, 300, 400, 300)  # Even smaller when chat is hidden

    def toggle_chat(self):
        self.chat_visible = not self.chat_visible
        if self.chat_visible:
            self.conversation_text.show()
            self.toggle_chat_button.setText("Hide Chat")
        else:
            self.conversation_text.hide()
            self.toggle_chat_button.setText("Show Chat")
        self.adjust_size()

    def toggle_recording(self):
        if self.recorder_thread is None or not self.recorder_thread.isRunning():
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.status_label.setText('Listening...')
        self.record_button.setStyleSheet("background-color: #FF3B30;")  # Red when recording
        self.recorder_thread = AudioRecorderThread()
        self.recorder_thread.finished.connect(self.process_audio)
        self.recorder_thread.audio_level.connect(self.update_audio_level)
        self.recorder_thread.start()

    def stop_recording(self):
        if self.recorder_thread:
            self.recorder_thread.requestInterruption()
            self.recorder_thread.wait()
        self.status_label.setText('Processing...')
        self.record_button.setStyleSheet("")  # Reset to default style

    def process_audio(self, user_text):
        if user_text:
            self.status_label.setText('AI is responding...')
            self.conversation_text.append(f'<b>You:</b><br>{user_text}<br>')
            history.append({'role': 'user', 'content': user_text})

            self.response_thread = AIResponseThread([system_prompt] + history[-10:])
            self.response_thread.response_ready.connect(self.handle_ai_response)
            self.response_thread.progress_update.connect(self.update_ai_response)
            self.response_thread.start()
        else:
            self.status_label.setText('No speech detected. Try again.')
            self.record_button.setStyleSheet("")  # Reset to default style

    def update_ai_response(self, chunk):
        current_text = self.conversation_text.toPlainText()
        if current_text.endswith('Brian:\n'):
            self.conversation_text.insertPlainText(chunk)
        else:
            self.conversation_text.insertPlainText(chunk)
        self.conversation_text.verticalScrollBar().setValue(self.conversation_text.verticalScrollBar().maximum())

    def handle_ai_response(self, ai_response):
        self.status_label.setText('Ready')
        self.record_button.setStyleSheet("")  # Reset to default style

        self.conversation_text.append(f'<b>Brian:</b><br>{ai_response}<br>')
        history.append({'role': 'assistant', 'content': ai_response})
        stream(elevenlabs_client.generate(text=ai_response, voice="Chris", model="eleven_multilingual_v2", stream=True))

    def update_audio_level(self, level=0):
        bars = int(level / 100) if level > 0 else 0
        self.audio_level_indicator.setText('▮' * bars + '▯' * (10 - bars))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AIVoiceChatApp()
    ex.show()
    sys.exit(app.exec())