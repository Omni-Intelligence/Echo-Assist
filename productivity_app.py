import sys
import os
import ctypes
import traceback
import pyaudio
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QFrame, QComboBox, QMessageBox,
                           QPushButton, QSlider, QStackedWidget)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QScreen

# Import our modules
from modules.style_config import ThemeConfig
from modules.custom_title_bar import CustomTitleBar
from modules.voice_typer import VoiceTyperWidget
from modules.avatar_chat import AvatarChatWidget
from modules.screenshot import ScreenshotWidget
from modules.real_time_chat import RealTimeChatWidget
from avatars.avatar_configs import AVATARS

class ProductivityApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Remove window frame and set up theme
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.theme = ThemeConfig()
        self.current_size = self.theme.sizes["window"]
        self.setMinimumSize(300, 400)
        
        # Initialize PyAudio for device enumeration
        self.p = pyaudio.PyAudio()
        # Set default input device to HyperX SoloCast (index 2)
        self.selected_input_device = 2
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Echo Assist')
        self.resize(300, 80)  # Reduced height
        
        # Center the window on screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)
        
        # Enable window dragging and transparency
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Create main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create outer layout that will contain both close button and main content
        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # Create a container for the close button
        top_bar = QWidget()
        top_bar.setFixedHeight(20)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 5, 0)
        top_bar_layout.addStretch()
        
        # Add close button
        close_button = QPushButton("×")
        close_button.setFixedSize(15, 15)
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 14px;
                margin: 0;
                padding: 0;
            }
            QPushButton:hover {
                color: red;
            }
        """)
        top_bar_layout.addWidget(close_button)
        
        # Add top bar to outer layout
        outer_layout.addWidget(top_bar)
        
        # Create voice typer widget
        self.voice_typer = VoiceTyperWidget(self, self.theme)
        self.voice_typer.selected_input_device = self.selected_input_device
        
        # Add voice typer to outer layout
        outer_layout.addWidget(self.voice_typer)
        
        # Set window style
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: transparent;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def change_microphone(self, index):
        """Update the selected input device when microphone selection changes"""
        device_index = index  # Get the stored device index
        if device_index is not None:
            self.selected_input_device = device_index
            # Update the voice typer's input device
            if hasattr(self, 'voice_typer'):
                self.voice_typer.selected_input_device = device_index
            print(f"Changed microphone to index {device_index}")

    def update_styles(self):
        """Update styles for all components"""
        # Update title bar
        self.title_bar.update_theme()
        
        # Apply styles
        self.setStyleSheet(f"""
            QMainWindow {{
                background: transparent;
                color: {self.theme.get_color('text')};
                padding: 5px;
                background: transparent;
            }}
            #sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 10px;
                margin: 10px;
            }}
            #content {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 10px;
            }}
            QComboBox, QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 4px;
                padding: 5px;
                color: {self.theme.get_color('text')};
            }}
            QComboBox:hover, QPushButton:hover {{
                background: {self.theme.get_color('secondary')};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QLabel {{
                color: {self.theme.get_color('text')};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {self.theme.get_color('border')};
                height: 8px;
                background: {self.theme.get_color('secondary')};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {self.theme.get_color('accent')};
                border: 1px solid {self.theme.get_color('border')};
                width: 18px;
                margin: -2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {self.theme.get_color('accent_gradient')};
            }}
        """)

    def change_theme(self, theme_name):
        """Update application theme"""
        self.theme.current_theme = theme_name
        self.update_styles()

def exception_hook(exctype, value, tb):
    """Global exception handler to prevent app from crashing silently"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print('Error:', error_msg)  # Print to console
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setText("An error occurred")
    msg.setInformativeText(str(value))
    msg.setDetailedText(error_msg)
    msg.setWindowTitle("Error")
    msg.exec()
    # Keep the default exception hook behavior
    sys.__excepthook__(exctype, value, tb)

if __name__ == '__main__':
    # Install global exception handler
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    try:
        ex = ProductivityApp()
        ex.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error starting app: {e}")
        traceback.print_exc()
