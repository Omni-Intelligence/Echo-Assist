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
        self.resize(self.current_size)
        
        # Position window in the top-left corner
        self.move(0, 0)
        
        # Create main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add custom title bar
        self.title_bar = CustomTitleBar(self, self.theme)
        main_layout.addWidget(self.title_bar)
        
        # Create content container
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(8, 8, 8, 8)  # Increased margins
        content_layout.setSpacing(8)  # Increased spacing
        
        # Create sidebar and content
        self.sidebar = self.create_sidebar()
        content_frame = self.create_content_area()
        
        # Add widgets to content layout
        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(content_frame)
        
        # Add content container to main layout
        main_layout.addWidget(content_container)
        
        # Set window style
        self.update_styles()

    def create_sidebar(self):
        """Create the sidebar with navigation buttons"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)  # Increased margins
        sidebar_layout.setSpacing(8)  # Increased spacing
        
        # Create navigation buttons - only Voice Typer and Settings
        nav_buttons = [
            ("⌨️ Voice Typer", 0),
            ("⚙️ Settings", 1)
        ]
        
        # Store buttons for state management
        self.nav_buttons = []
        
        for text, index in nav_buttons:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFont(self.theme.SMALL_FONT)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 8px;
                    color: {self.theme.get_color('text')};
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {self.theme.get_color('secondary')},
                        stop:1 {self.theme.get_color('secondary_gradient')});
                    border: 1px solid {self.theme.get_color('border')};
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background: {self.theme.get_color('secondary')};
                }}
                QPushButton:checked {{
                    background: {self.theme.get_color('accent')};
                }}
            """)
            
            btn.clicked.connect(lambda checked, i=index: self.handle_navigation(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        # Set initial button state
        self.nav_buttons[0].setChecked(True)
        
        sidebar_layout.addStretch()
        return sidebar

    def handle_navigation(self, index):
        """Handle navigation button clicks"""
        # Uncheck all buttons first
        for btn in self.nav_buttons:
            btn.setChecked(False)
        
        # Set the clicked button as checked and switch page
        self.nav_buttons[index].setChecked(True)
        self.switch_page(index)

    def create_content_area(self):
        """Create the main content area with stacked widgets"""
        content_frame = QFrame()
        content_frame.setObjectName("content")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create stacked widget to hold different pages
        self.stack = QStackedWidget()
        
        # Only add Voice Typer and Settings
        self.voice_typer = VoiceTyperWidget(self.theme)
        self.voice_typer.selected_input_device = self.selected_input_device
        self.settings_widget = self.create_settings_widget()
        
        self.stack.addWidget(self.voice_typer)
        self.stack.addWidget(self.settings_widget)
        
        content_layout.addWidget(self.stack)
        return content_frame

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)

    def create_settings_widget(self):
        """Create the settings panel with window size and theme controls"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(12, 12, 12, 12)
        settings_layout.setSpacing(8)

        # Window size control
        size_label = QLabel("Window Size")
        size_label.setFont(self.theme.SMALL_FONT)
        settings_layout.addWidget(size_label)

        size_slider = QSlider(Qt.Orientation.Horizontal)
        size_slider.setMinimum(300)
        size_slider.setMaximum(800)
        size_slider.setValue(self.width())
        size_slider.valueChanged.connect(self.resize_window)
        settings_layout.addWidget(size_slider)

        # Theme selection
        theme_label = QLabel("Theme")
        theme_label.setFont(self.theme.SMALL_FONT)
        settings_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText("Dark")
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.theme_combo.setFont(self.theme.SMALL_FONT)
        settings_layout.addWidget(self.theme_combo)

        # Microphone selection
        mic_label = QLabel("Microphone")
        mic_label.setFont(self.theme.SMALL_FONT)
        settings_layout.addWidget(mic_label)

        self.mic_combo = QComboBox()
        self.mic_combo.setFont(self.theme.SMALL_FONT)
        
        # Get available input devices
        input_devices = []
        hyperx_index = None
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # Only add input devices
                name = device_info['name']
                input_devices.append((name, i))
                self.mic_combo.addItem(name, i)  # Store device index in user data
                # Check if this is the HyperX device
                if 'HyperX SoloCast' in name and i == 2:
                    hyperx_index = i
        
        # Set HyperX SoloCast (index 2) as default if available
        if hyperx_index is not None:
            hyperx_name = self.p.get_device_info_by_index(hyperx_index)['name']
            index = self.mic_combo.findText(hyperx_name)
            if index >= 0:
                self.mic_combo.setCurrentIndex(index)
                self.selected_input_device = hyperx_index
                print(f"Selected HyperX SoloCast microphone (index {hyperx_index})")
        
        self.mic_combo.currentIndexChanged.connect(self.change_microphone)
        settings_layout.addWidget(self.mic_combo)

        # Add stretch to push everything to the top
        settings_layout.addStretch()

        return settings_widget

    def change_microphone(self, index):
        """Update the selected input device when microphone selection changes"""
        device_index = self.mic_combo.itemData(index)  # Get the stored device index
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
                background: {self.theme.get_color('primary')};
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

    def resize_window(self, width):
        """Resize the window while maintaining aspect ratio"""
        current_ratio = self.height() / self.width()
        new_height = int(width * current_ratio)
        self.resize(width, new_height)

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
