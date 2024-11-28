from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QMainWindow
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent

class CustomTitleBar(QFrame):
    """A custom title bar with window controls and dragging functionality"""
    def __init__(self, parent=None, title="🎯 Echo Assist"):
        super().__init__(parent)
        if not isinstance(parent, QMainWindow):
            raise TypeError("CustomTitleBar parent must be a QMainWindow")
        
        self.parent = parent
        self.title_text = title
        self.setObjectName("title-bar")
        self.setFixedHeight(36)
        self.moving = False
        self.offset = QPoint()
        
        self.init_ui()
        self.setup_styles()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        
        # App icon and title
        self.title = QLabel(self.title_text)
        self.title.setObjectName("window-title")
        
        # Window controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        # Create window control buttons
        self.minimize_btn = QPushButton("─")
        self.maximize_btn = QPushButton("□")
        self.close_btn = QPushButton("×")
        
        # Configure buttons
        for btn, name, tip in [(self.minimize_btn, "minimize-btn", "Minimize"),
                              (self.maximize_btn, "maximize-btn", "Maximize"),
                              (self.close_btn, "close-btn", "Close")]:
            btn.setObjectName(name)
            btn.setToolTip(tip)
            btn.setFixedSize(36, 36)
            controls_layout.addWidget(btn)
        
        # Connect button signals
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self.parent.close)
        
        # Add widgets to layout
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addLayout(controls_layout)
    
    def setup_styles(self):
        """Set up the styles for the title bar components"""
        # Get theme colors from parent if available
        theme = getattr(self.parent, 'theme', None)
        if theme:
            self.setStyleSheet(f"""
                #title-bar {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {theme.get_color('secondary')},
                        stop:1 {theme.get_color('secondary_gradient')});
                    border-bottom: 1px solid {theme.get_color('border')};
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }}
                #window-title {{
                    color: {theme.get_color('text')};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0;
                }}
                QPushButton#minimize-btn,
                QPushButton#maximize-btn,
                QPushButton#close-btn {{
                    background: transparent;
                    border: none;
                    border-radius: 0;
                    font-family: Arial;
                    font-size: 14px;
                    padding: 0;
                    color: {theme.get_color('text')};
                }}
                QPushButton#minimize-btn:hover,
                QPushButton#maximize-btn:hover {{
                    background: rgba(255, 255, 255, 0.1);
                }}
                QPushButton#close-btn:hover {{
                    background: #E81123;
                    color: white;
                }}
            """)
    
    def update_theme(self):
        """Update the title bar styles when theme changes"""
        self.setup_styles()
    
    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.parent.showMaximized()
            self.maximize_btn.setText("❐")
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events for window dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.moving = True
            self.offset = event.position().toPoint()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events for window dragging"""
        if self.moving and not self.parent.isMaximized():
            self.parent.move(event.globalPosition().toPoint() - self.offset)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events for window dragging"""
        self.moving = False
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle mouse double click events for maximizing/restoring"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
