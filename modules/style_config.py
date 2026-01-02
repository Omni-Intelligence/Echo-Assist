from PyQt6.QtGui import QFont

class ThemeConfig:
    def __init__(self):
        # Fonts
        self.SMALL_FONT = QFont("Segoe UI", 10)

        # Minimalist dark theme
        self.colors = {
            'bg': '#0f0f0f',
            'bg_secondary': '#1a1a1a',
            'text': '#ffffff',
            'text_muted': '#888888',
            'accent': '#5ba3ff',
            'accent_hover': '#7bb3ff',
            'error': '#ff6b6b',
        }

        # Spacing
        self.PADDING = 10
        self.SPACING = 6
        self.RADIUS = 10

    def get_color(self, name):
        return self.colors.get(name, '#ffffff')

    def get_styles(self):
        """Centralized stylesheet definitions"""
        return {
            'main_container': f"""
                QFrame {{
                    background: {self.get_color('bg_secondary')};
                    border-radius: {self.RADIUS}px;
                }}
            """,
            'button': f"""
                QPushButton {{
                    color: {self.get_color('text')};
                    background: {self.get_color('accent')};
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {self.get_color('accent_hover')};
                }}
                QPushButton:pressed {{
                    background: #4a94f0;
                }}
            """,
            'button_icon': f"""
                QPushButton {{
                    color: {self.get_color('text_muted')};
                    background: transparent;
                    border: none;
                    padding: 4px;
                }}
                QPushButton:hover {{
                    color: {self.get_color('text')};
                }}
            """,
            'button_close': f"""
                QPushButton {{
                    color: {self.get_color('text_muted')};
                    background: transparent;
                    border: none;
                    padding: 4px;
                }}
                QPushButton:hover {{
                    color: {self.get_color('error')};
                }}
            """,
            'label': f"""
                QLabel {{
                    color: {self.get_color('text_muted')};
                    font-size: 10px;
                    font-weight: 500;
                }}
            """,
            'combo': f"""
                QComboBox {{
                    background: {self.get_color('bg')};
                    color: {self.get_color('text')};
                    border: 1px solid {self.get_color('text_muted')};
                    border-radius: 6px;
                    padding: 6px 8px;
                    font-size: 10px;
                }}
                QComboBox QAbstractItemView {{
                    color: {self.get_color('text')};
                    background: {self.get_color('bg_secondary')};
                    selection-background-color: {self.get_color('accent')};
                    border: none;
                }}
            """,
            'checkbox': f"""
                QCheckBox {{
                    color: {self.get_color('text_muted')};
                    font-size: 10px;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 14px;
                    height: 14px;
                    background: {self.get_color('bg')};
                    border: 1px solid {self.get_color('text_muted')};
                    border-radius: 3px;
                }}
                QCheckBox::indicator:hover {{
                    border: 1px solid {self.get_color('text')};
                }}
                QCheckBox::indicator:checked {{
                    background: {self.get_color('accent')};
                    border: 1px solid {self.get_color('accent')};
                }}
            """,
            'viz_bar': f"""
                QFrame {{
                    background-color: {self.get_color('accent')};
                    border-radius: 6px;
                }}
            """,
            'messagebox': f"""
                QMessageBox {{
                    background: {self.get_color('bg_secondary')};
                }}
                QMessageBox QLabel {{
                    color: {self.get_color('text')};
                }}
                QMessageBox QPushButton {{
                    color: {self.get_color('text')};
                    background: {self.get_color('accent')};
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: 11px;
                    min-width: 50px;
                }}
                QMessageBox QPushButton:hover {{
                    background: {self.get_color('accent_hover')};
                }}
            """
        } 