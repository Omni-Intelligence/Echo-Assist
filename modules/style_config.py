from PyQt6.QtGui import QFont

class ThemeConfig:
    def __init__(self):
        # Fonts
        self.SMALL_FONT = QFont("Segoe UI", 10)

        # Enterprise DNA brand palette
        self.colors = {
            'bg': '#0b0c18',           # EDNA black
            'bg_secondary': '#1a1b2e', # slightly lifted for inputs
            'text': '#ffffff',
            'text_muted': '#b8b9d1',   # softer for readability on gradient
            'accent': '#6654f5',       # EDNA blue
            'accent_hover': '#7e6ff7',
            'accent_pink': '#ca5a8b',  # EDNA pink
            'accent_yellow': '#f2b347',# EDNA yellow
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
                QFrame#mainContainer {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 {self.get_color('accent')},
                        stop:0.5 {self.get_color('accent_pink')},
                        stop:1 {self.get_color('accent_yellow')}
                    );
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
            'button_record': f"""
                QPushButton {{
                    color: {self.get_color('text_muted')};
                    background: {self.get_color('bg')};
                    border: 1px solid {self.get_color('text_muted')};
                    border-radius: 10px;
                    padding: 0px;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    color: {self.get_color('error')};
                    border: 1px solid {self.get_color('error')};
                }}
            """,
            'button_record_active': f"""
                QPushButton {{
                    color: white;
                    background: {self.get_color('error')};
                    border: 1px solid {self.get_color('error')};
                    border-radius: 10px;
                    padding: 0px;
                    font-size: 10px;
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
                    background-color: rgba(255, 255, 255, 0.85);
                    border-radius: 3px;
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