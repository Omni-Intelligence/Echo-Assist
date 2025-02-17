from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSize

class ThemeConfig:
    """Theme configuration with support for multiple themes and dynamic styling"""
    def __init__(self):
        # Fonts
        self.HEADER_FONT = QFont("Segoe UI", 16, QFont.Weight.Bold)
        self.BODY_FONT = QFont("Segoe UI", 12)
        self.SMALL_FONT = QFont("Segoe UI", 10)  # Added small font for more compact UI elements
        self.BUTTON_FONT = QFont("Segoe UI", 12, QFont.Weight.Medium)
        
        # Default theme
        self.themes = {
            "Dark": {
                "primary": "#2D1F36",
                "primary_gradient": "#432B52",
                "secondary": "#FFFFFF",
                "accent": "#E8E1F0",
                "text": "#FFFFFF",
                "text_secondary": "rgba(255, 255, 255, 0.6)",
                "border": "#222222"
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
        """Get a color from the current theme"""
        return self.themes[self.current_theme][name]
    
    def get_button_style(self):
        """Get button style for current theme"""
        return f"""
            QPushButton {{
                background-color: {self.get_color('accent')};
                color: {self.get_color('text')};
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.get_color('primary_gradient')};
            }}
            QPushButton:pressed {{
                background-color: {self.get_color('primary')};
            }}
        """
    
    def get_combobox_style(self):
        """Get combobox style for current theme"""
        return f"""
            QComboBox {{
                background-color: {self.get_color('secondary')};
                color: {self.get_color('text')};
                border: none;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                min-width: 150px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.get_color('primary')};
                color: {self.get_color('text')};
                selection-background-color: {self.get_color('primary_gradient')};
            }}
        """
    
    def get_chat_display_style(self):
        """Get chat display style for current theme"""
        return f"""
            QTextEdit {{
                background-color: {self.get_color('secondary')};
                color: {self.get_color('text')};
                border: none;
                border-radius: 15px;
                padding: 20px;
                font-size: 14px;
            }}
        """
    
    def get_sidebar_style(self):
        """Get sidebar style for current theme"""
        return f"""
            QFrame {{
                background-color: {self.get_color('secondary')};
                border-radius: 15px;
                margin: 10px;
            }}
        """
