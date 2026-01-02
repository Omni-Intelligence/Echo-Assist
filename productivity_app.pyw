import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QPoint
from modules.voice_typer import VoiceTyperWidget
from modules.style_config import ThemeConfig

class ProductivityApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Voice Typer')
        self.setFixedSize(300, 200)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Initialize theme
        self.theme = ThemeConfig()

        # Set window background transparent
        self.setStyleSheet("QMainWindow { background: transparent; }")

        # Create central widget and layout
        central_widget = QWidget()
        central_widget.setStyleSheet("QWidget { background: transparent; }")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add voice typer widget with theme
        self.voice_typer = VoiceTyperWidget(self, self.theme)
        layout.addWidget(self.voice_typer)

        # Initialize dragging variables
        self.dragging = False
        self.drag_position = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = ProductivityApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        sys.exit(1)
