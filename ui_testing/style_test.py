import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QFrame, QComboBox,
                           QTextEdit, QSlider, QSpacerItem, QSizePolicy, QStackedWidget)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QFont, QIcon, QMouseEvent

class ThemeConfig:
    """Theme configuration for easy testing of different styles"""
    def __init__(self):
        # Default theme
        self.themes = {
            "Dark": {
                "primary": "#1E1E1E",
                "primary_gradient": "#2D2D2D",
                "secondary": "#252526",
                "secondary_gradient": "#2D2D30",
                "accent": "#0078D4",
                "accent_gradient": "#0091FF",
                "text": "#FFFFFF",
                "text_secondary": "#CCCCCC",
                "success": "#4CAF50",
                "error": "#FF3B30",
                "border": "#333333",
                "hover": "#2D2D2D",
                "selected": "#404040"
            },
            "Light": {
                "primary": "#FFFFFF",
                "primary_gradient": "#F5F5F5",
                "secondary": "#F3F3F3",
                "secondary_gradient": "#E8E8E8",
                "accent": "#0078D4",
                "accent_gradient": "#0091FF",
                "text": "#000000",
                "text_secondary": "#666666",
                "success": "#34C759",
                "error": "#FF3B30",
                "border": "#E0E0E0",
                "hover": "#E8E8E8",
                "selected": "#E0E0E0"
            },
            "Neutral": {
                "primary": "#F5F5F5",
                "primary_gradient": "#EBEBEB",
                "secondary": "#E8E8E8",
                "secondary_gradient": "#DEDEDE",
                "accent": "#2196F3",
                "accent_gradient": "#42A5F5",
                "text": "#212121",
                "text_secondary": "#757575",
                "success": "#4CAF50",
                "error": "#F44336",
                "border": "#BDBDBD",
                "hover": "#DEDEDE",
                "selected": "#D4D4D4"
            }
        }
        self.current_theme = "Dark"
        self.sizes = {
            "window": QSize(400, 500),  # Smaller default size
            "compact": QSize(300, 400),
            "sidebar": 180,  # Slightly narrower sidebar
            "spacing": 10
        }
        
    def get_color(self, name):
        return self.themes[self.current_theme][name]

class CustomTitleBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        if not isinstance(parent, QMainWindow):
            raise TypeError("CustomTitleBar parent must be a QMainWindow")
        self.parent = parent
        self.setObjectName("title-bar")
        self.setFixedHeight(36)
        self.moving = False
        self.offset = QPoint()
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        
        # App icon and title
        title = QLabel("🎯 AI Voice Assistant")
        title.setObjectName("window-title")
        
        # Window controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        minimize_btn = QPushButton("─")
        maximize_btn = QPushButton("□")
        close_btn = QPushButton("×")
        
        for btn, name, tip in [(minimize_btn, "minimize-btn", "Minimize"),
                              (maximize_btn, "maximize-btn", "Maximize"),
                              (close_btn, "close-btn", "Close")]:
            btn.setObjectName(name)
            btn.setToolTip(tip)
            btn.setFixedSize(36, 36)
            controls_layout.addWidget(btn)
        
        minimize_btn.clicked.connect(self.parent.showMinimized)
        maximize_btn.clicked.connect(self.toggle_maximize)
        close_btn.clicked.connect(self.parent.close)
        
        # Add widgets to layout
        layout.addWidget(title)
        layout.addStretch()
        layout.addLayout(controls_layout)
    
    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.moving = True
            self.offset = event.position().toPoint()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.moving and not self.parent.isMaximized():
            self.parent.move(event.globalPosition().toPoint() - self.offset)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        self.moving = False
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()

class StyleTestApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme = ThemeConfig()
        self.current_size = self.theme.sizes["window"]
        self.setMinimumSize(300, 400)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # Remove default title bar
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('UI Style Test')
        self.resize(self.current_size)
        
        # Create central widget with main layout
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
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        
        # Create sidebar and content
        self.sidebar = self.create_sidebar()
        self.content = self.create_content()
        
        # Add widgets to content layout
        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.content)
        
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
        self.avatar_combo.addItems(["Joe", "Sarah", "Alex", "Emma"])
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

    def create_content(self):
        content = QFrame()
        content.setObjectName("content")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Status area with icon
        status = QLabel("Status: Ready")
        
        # Audio level indicator (mock)
        level_frame = QFrame()
        level_frame.setFixedHeight(4)  # Thinner audio level indicator
        
        # Text area with placeholder
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Start typing or use voice input...")
        
        # Add items to layout
        layout.addWidget(status)
        layout.addWidget(level_frame)
        layout.addWidget(self.text_area)
        
        return content

    def change_mode(self, mode):
        """Handle mode changes"""
        # Update button styles
        self.avatar_chat_btn.setProperty("selected", mode == "Avatar Chat")
        self.voice_typing_btn.setProperty("selected", mode == "Voice Typing")
        
        # Force style update
        self.avatar_chat_btn.style().unpolish(self.avatar_chat_btn)
        self.avatar_chat_btn.style().polish(self.avatar_chat_btn)
        self.voice_typing_btn.style().unpolish(self.voice_typing_btn)
        self.voice_typing_btn.style().polish(self.voice_typing_btn)
        
        # Show/hide avatar selection
        if mode == "Avatar Chat":
            self.avatar_label.show()
            self.avatar_combo.show()
            self.text_area.setPlaceholderText("Chat with your AI assistant...")
        else:
            self.avatar_label.hide()
            self.avatar_combo.hide()
            self.text_area.setPlaceholderText("Voice typing mode - Press Ctrl+Space to start")

    def change_theme(self, theme_name):
        # Store current window size
        self.current_size = self.size()
        self.theme.current_theme = theme_name
        
        # Update styles without recreating UI
        self.update_styles()
        
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.current_size = self.theme.sizes["window"]
        self.resize(self.current_size)
        self.theme_combo.setCurrentText("Dark")

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
        """Update all widget styles without recreating the UI"""
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
            QFrame#title-bar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                border-bottom: 1px solid {self.theme.get_color('border')};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QLabel#window-title {{
                font-size: 14px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton#minimize-btn, QPushButton#maximize-btn, QPushButton#close-btn {{
                background: transparent;
                border: none;
                border-radius: 0;
                font-family: Arial;
                font-size: 14px;
                padding: 0;
            }}
            QPushButton#minimize-btn:hover, QPushButton#maximize-btn:hover {{
                background: rgba(255, 255, 255, 0.1);
            }}
            QPushButton#close-btn:hover {{
                background: #E81123;
                color: white;
            }}
            QPushButton#mode-btn {{
                text-align: left;
                padding: 12px;
                font-weight: bold;
            }}
            QPushButton#settings-btn {{
                text-align: left;
            }}
            QFrame#sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 10px;
            }}
            QFrame#content {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 10px;
            }}
            QTextEdit {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('secondary_gradient')});
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 6px;
                padding: 10px;
                selection-background-color: {self.theme.get_color('accent')};
            }}
            QFrame#modes-frame {{
                background: transparent;
                border: none;
            }}
        """)
        
        # Update specific widget styles
        for widget in self.findChildren(QLabel):
            if widget.text().startswith("Status:"):
                widget.setStyleSheet(f"""
                    background-color: {self.theme.get_color('accent')};
                    color: {self.theme.get_color('text')};
                    padding: 10px;
                    border-radius: 6px;
                    font-weight: bold;
                """)
                
        for widget in self.findChildren(QFrame):
            if hasattr(widget, 'height') and widget.height() == 4:  # Audio level indicator
                widget.setStyleSheet(f"""
                    background-color: {self.theme.get_color('success')};
                    border-radius: 3px;
                """)

    def resize_window(self, value):
        self.current_size = QSize(value, self.height())
        self.resize(self.current_size)
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = StyleTestApp()
    ex.show()
    sys.exit(app.exec())
