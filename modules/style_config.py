from PyQt6.QtGui import QFont

class ThemeConfig:
    def __init__(self):
        # Fonts
        self.SMALL_FONT = QFont("Segoe UI", 10)
        
        # Colors
        self.colors = {
            'primary': '#2D1F36',
            'primary_gradient': '#432B52',
            'accent': '#E8E1F0',
            'text': '#FFFFFF',
            'text_secondary': 'rgba(255, 255, 255, 0.6)'
        }
    
    def get_color(self, name):
        return self.colors.get(name, '#FFFFFF') 