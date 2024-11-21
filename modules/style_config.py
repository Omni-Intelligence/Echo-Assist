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
                "selected": "#404040",
                "selected_gradient": "#505050"
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
                "selected": "#E0E0E0",
                "selected_gradient": "#D0D0D0"
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
                "selected": "#D4D4D4",
                "selected_gradient": "#C4C4C4"
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
                background-color: {self.get_color('accent_gradient')};
            }}
            QPushButton:pressed {{
                background-color: {self.get_color('hover')};
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
                selection-background-color: {self.get_color('selected')};
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
