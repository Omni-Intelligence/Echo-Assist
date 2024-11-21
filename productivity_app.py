import sys
import os
import ctypes
import traceback
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QFrame, QComboBox, QMessageBox,
                           QPushButton, QSlider, QStackedWidget)
from PyQt6.QtCore import Qt, QSize, QPoint

# Import our modules
from modules.style_config import ThemeConfig
from modules.custom_title_bar import CustomTitleBar
from modules.voice_typer import VoiceTyperWidget
from modules.avatar_chat import AvatarChatWidget
from avatars.avatar_configs import AVATARS

class ProductivityApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Remove window frame and set up theme
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.theme = ThemeConfig()
        self.current_size = self.theme.sizes["window"]
        self.setMinimumSize(300, 400)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('AI Assistant')
        self.resize(self.current_size)
        
        # Create main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add custom title bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        # Create content container
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(4)
        
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
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMaximumWidth(self.theme.sizes["sidebar"])
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Mode buttons container
        modes_frame = QFrame()
        modes_frame.setObjectName("modes-frame")
        modes_layout = QVBoxLayout(modes_frame)
        modes_layout.setContentsMargins(0, 0, 0, 0)
        modes_layout.setSpacing(4)
        
        # Create mode buttons
        self.avatar_chat_btn = QPushButton("💬 Avatar Chat")
        self.voice_typing_btn = QPushButton("🎤 Voice Typing")
        
        # Set object names for styling
        self.avatar_chat_btn.setObjectName("mode-btn")
        self.voice_typing_btn.setObjectName("mode-btn")
        
        # Connect mode buttons
        self.avatar_chat_btn.clicked.connect(lambda: self.change_mode("Avatar Chat"))
        self.voice_typing_btn.clicked.connect(lambda: self.change_mode("Voice Typing"))
        
        # Add mode buttons to layout
        modes_layout.addWidget(self.avatar_chat_btn)
        modes_layout.addWidget(self.voice_typing_btn)
        
        # Avatar selection (initially hidden)
        self.avatar_label = QLabel("Avatar")
        self.avatar_combo = QComboBox()
        self.avatar_combo.addItems(list(AVATARS.keys()))
        self.avatar_combo.currentTextChanged.connect(self.change_avatar)  # Connect the change event
        self.avatar_label.hide()
        self.avatar_combo.hide()
        
        # Settings button and stacked widget
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("settings-btn")
        settings_btn.clicked.connect(self.toggle_settings)
        
        # Create stacked widget for settings
        self.settings_stack = QStackedWidget()
        self.settings_stack.setObjectName("settings-panel")
        
        # Create settings panel
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(8)
        
        # Theme selection
        theme_label = QLabel("Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self.theme.themes.keys()))
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        
        # Window size slider
        size_label = QLabel("Window Size")
        size_slider = QSlider(Qt.Orientation.Horizontal)
        size_slider.setMinimum(300)
        size_slider.setMaximum(800)
        size_slider.setValue(self.width())
        size_slider.valueChanged.connect(self.resize_window)
        
        # Add settings controls
        for widget in [theme_label, self.theme_combo,
                      size_label, size_slider]:
            settings_layout.addWidget(widget)
        
        # Add reset button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_to_defaults)
        settings_layout.addWidget(reset_button)
        settings_layout.addStretch()
        
        # Add panels to stacked widget
        self.settings_stack.addWidget(settings_panel)
        self.settings_stack.addWidget(QWidget())  # Empty widget for collapsed state
        self.settings_stack.setCurrentIndex(1)  # Start with settings collapsed
        
        # Add everything to main layout
        layout.addWidget(modes_frame)
        layout.addWidget(self.avatar_label)
        layout.addWidget(self.avatar_combo)
        layout.addSpacing(8)
        layout.addWidget(settings_btn)
        layout.addWidget(self.settings_stack)
        layout.addStretch()
        
        return sidebar

    def create_content_area(self):
        content_frame = QFrame()
        content_frame.setObjectName("content")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Initialize widgets
        self.avatar_chat = AvatarChatWidget(self.theme, AVATARS)
        self.voice_typer = VoiceTyperWidget(self.theme)
        
        # Add widgets to content area
        content_layout.addWidget(self.avatar_chat)
        content_layout.addWidget(self.voice_typer)
        
        # Set initial state
        self.voice_typer.hide()
        self.avatar_chat.set_avatar(self.avatar_combo.currentText())

        return content_frame

    def change_mode(self, mode):
        if mode == 'Avatar Chat':
            self.avatar_chat.show()
            self.voice_typer.hide()
            self.avatar_label.show()
            self.avatar_combo.show()
        else:
            self.avatar_chat.hide()
            self.voice_typer.show()
            self.avatar_label.hide()
            self.avatar_combo.hide()

    def change_avatar(self, avatar_name):
        """Update the current avatar and its voice"""
        if avatar_name in AVATARS:
            self.avatar_chat.set_avatar(avatar_name)

    def change_theme(self, theme_name):
        """Update application theme"""
        self.theme.current_theme = theme_name
        self.update_styles()
        
    def resize_window(self, width):
        """Resize the window while maintaining aspect ratio"""
        current_ratio = self.height() / self.width()
        new_height = int(width * current_ratio)
        self.resize(width, new_height)

    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.current_size = self.theme.sizes["window"]
        self.resize(self.current_size)
        self.theme_combo.setCurrentText("Dark")
        self.update_styles()

    def toggle_settings(self):
        """Toggle settings panel visibility"""
        current_index = self.settings_stack.currentIndex()
        new_index = 1 if current_index == 0 else 0
        self.settings_stack.setCurrentIndex(new_index)
        
        # Update button text
        settings_btn = self.findChild(QPushButton, "settings-btn")
        if settings_btn:
            settings_btn.setText("⚙ Settings" if new_index == 1 else "⚙ Hide Settings")

    def update_styles(self):
        """Update styles for all components"""
        # Update title bar
        self.title_bar.update_theme()
        
        # Update main application styles
        self.setStyleSheet(f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self.theme.get_color('primary')},
                    stop:1 {self.theme.get_color('primary_gradient')});
            }}
            QLabel {{
                color: {self.theme.get_color('text')};
                font-size: 13px;
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
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;
                padding: 8px;
                min-height: 20px;
            }}
            QComboBox:hover, QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('hover')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                border: 1px solid {self.theme.get_color('accent')};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('accent')},
                    stop:1 {self.theme.get_color('accent_gradient')});
            }}
            QPushButton[selected=true] {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('accent')},
                    stop:1 {self.theme.get_color('accent_gradient')});
                border: 1px solid {self.theme.get_color('accent')};
            }}
            QSlider::groove:horizontal {{
                background: {self.theme.get_color('secondary_gradient')};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {self.theme.get_color('accent')};
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {self.theme.get_color('accent_gradient')};
            }}
            #settings-btn {{
                text-align: left;
            }}
            QFrame#modes-frame {{
                background: transparent;
                border: none;
            }}
        """)

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
