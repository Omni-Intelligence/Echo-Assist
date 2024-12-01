import tkinter as tk
from PIL import Image, ImageTk, ImageGrab
import openai
import base64
import requests
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QPushButton, 
                              QTextEdit, QMainWindow, QApplication)
from PyQt6.QtCore import Qt, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor
import sys
from elevenlabs import stream
from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize API clients
openai.api_key = os.getenv('OPENAI_API_KEY')
elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

class ScreenshotWidget(QWidget):
    screenshot_taken = pyqtSignal(str)  # Signal to emit when screenshot analysis is ready

    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.start_pos = None
        self.current_pos = None
        self.screenshot_overlay = None
        self.is_selecting = False
        self.is_processing = False
        self.main_window = None  # Store reference to main window
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Instructions label
        self.instructions_label = QLabel("Click 'Take Screenshot' to start")
        self.instructions_label.setFont(self.theme.SMALL_FONT)
        self.instructions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instructions_label)
        
        # Take screenshot button
        self.screenshot_button = QPushButton("Take Screenshot")
        self.screenshot_button.setFont(self.theme.SMALL_FONT)
        self.screenshot_button.clicked.connect(self.start_screenshot)
        layout.addWidget(self.screenshot_button)
        
        # Analysis display
        self.analysis_display = QTextEdit()
        self.analysis_display.setFont(self.theme.SMALL_FONT)
        self.analysis_display.setReadOnly(True)
        self.analysis_display.setMinimumHeight(200)
        layout.addWidget(self.analysis_display)
        
        # Set widget styles
        self.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.get_color('text')};
                background: transparent;
                padding: 10px;
            }}
            QPushButton {{
                background: {self.theme.get_color('accent')};
                color: {self.theme.get_color('text')};
                border: none;
                padding: 10px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {self.theme.get_color('accent_gradient')};
            }}
            QTextEdit {{
                background: {self.theme.get_color('secondary')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 5px;
                padding: 10px;
            }}
        """)

    def start_screenshot(self):
        print("\n=== Starting Screenshot Process ===")
        
        # Cleanup any existing overlay
        print("1. Checking for existing overlay...")
        if self.screenshot_overlay and self.screenshot_overlay.isVisible():
            print("   - Found existing overlay, cleaning up")
            self.screenshot_overlay.close()
            self.screenshot_overlay = None
        else:
            print("   - No existing overlay found")
            
        # Find the main window
        print("2. Looking for main window...")
        parent = self.parent()
        parent_chain = []
        while parent is not None:
            parent_type = type(parent).__name__
            parent_chain.append(parent_type)
            print(f"   - Found parent: {parent_type}")
            if isinstance(parent, QMainWindow):
                self.main_window = parent
                print("   - Found main window!")
                break
            parent = parent.parent()
            
        print(f"   Parent chain: {' -> '.join(parent_chain)}")
            
        if not self.main_window:
            print("ERROR: Could not find main window")
            print("   - Widget hierarchy:", ' -> '.join(parent_chain))
            return
            
        # Create new screenshot overlay
        print("3. Creating screenshot overlay...")
        try:
            self.screenshot_overlay = ScreenshotOverlay(self)
            print("   - Overlay created successfully")
            
            # Show overlay immediately
            print("4. Showing overlay...")
            self.screenshot_overlay.showFullScreen()
            print("   - showFullScreen() called")
            self.screenshot_overlay.raise_()
            print("   - raise() called")
            self.screenshot_overlay.activateWindow()
            print("   - activateWindow() called")
            print("Screenshot overlay is now visible")
            print("=== Screenshot Process Complete ===\n")
        except Exception as e:
            print(f"ERROR creating/showing overlay: {str(e)}")
            import traceback
            print(traceback.format_exc())

    def show_main_window(self):
        """Helper function to safely show main window"""
        if self.main_window:
            self.main_window.activateWindow()
            QApplication.processEvents()

    def process_screenshot(self, image_path):
        print(f"\n=== Processing Screenshot: {image_path} ===")
        try:
            if self.is_processing:
                print("Already processing a screenshot")
                return
                
            self.is_processing = True
            self.instructions_label.setText("Analyzing screenshot...")
            
            # Verify the image exists and is readable
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Screenshot file not found: {image_path}")
                
            print("Encoding image...")
            base64_image = self.encode_image(image_path)
            
            print("Preparing API request...")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai.api_key}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What do you see in this screenshot? Please describe it in detail."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500
            }
            
            print("Sending request to OpenAI API...")
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30  # 30 second timeout
            )
            
            print(f"API Response status: {response.status_code}")
            response.raise_for_status()  # Raise exception for bad status codes
            
            result = response.json()
            print("Response received and parsed")
            
            # Validate response format
            if 'choices' not in result or not result['choices']:
                raise ValueError("Invalid API response format")
                
            analysis = result['choices'][0]['message']['content']
            print(f"Analysis: {analysis[:100]}...")  # Print first 100 chars
            
            # Update UI with the analysis
            self.analysis_display.setText(analysis)
            self.screenshot_taken.emit(analysis)
            self.instructions_label.setText("Analysis complete!")
            
        except FileNotFoundError:
            self.analysis_display.setText("Error: Screenshot file not found. Please try again.")
            self.instructions_label.setText("Error: Screenshot file not found")
        except ValueError as e:
            self.analysis_display.setText(f"Error: {str(e)}")
            self.instructions_label.setText("Error: Invalid API response")
        except requests.exceptions.RequestException as e:
            self.analysis_display.setText("Error: Failed to connect to API. Please check your internet connection and try again.")
            self.instructions_label.setText("Error: API connection failed")
        except Exception as e:
            self.analysis_display.setText(f"Error: An unexpected error occurred. Please try again.\nDetails: {str(e)}")
            self.instructions_label.setText("Error: Unexpected error occurred")
            print(f"ERROR in process_screenshot: {str(e)}")
            import traceback
            print(traceback.format_exc())
        finally:
            self.is_processing = False
            print("=== Screenshot Processing Complete ===\n")

    def encode_image(self, image_path):
        print(f"Encoding image from {image_path}")
        try:
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                print("Image encoded successfully")
                return encoded
        except Exception as e:
            print(f"ERROR encoding image: {str(e)}")
            raise

    def closeEvent(self, event):
        """Clean up when widget is closed"""
        if self.screenshot_overlay:
            self.screenshot_overlay.close()
            self.screenshot_overlay = None
        super().closeEvent(event)

class ScreenshotOverlay(QWidget):
    def __init__(self, parent=None):
        print("\n=== Initializing ScreenshotOverlay ===")
        super().__init__(None)  # Create without parent
        self.parent = parent
        self.start_pos = None
        self.current_pos = None
        self.min_size = 50  # Minimum selection size in pixels
        
        print("Setting window flags and attributes...")
        # Set window flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Set window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Make sure we cover the full screen
        print("Setting overlay geometry...")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        print(f"Overlay geometry set to: {self.geometry().x()}, {self.geometry().y()}, {self.geometry().width()}, {self.geometry().height()}")
        print("=== ScreenshotOverlay initialized ===\n")

    def showEvent(self, event):
        """Handle widget show event"""
        super().showEvent(event)
        # Make sure we're on top of everything
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Handle widget close event"""
        super().closeEvent(event)
        # Make sure parent window is shown
        if self.parent:
            self.parent.show_main_window()

    def paintEvent(self, event):
        print("Paint event triggered")
        painter = QPainter(self)
        
        # Fill the entire screen with a more transparent overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 70))  # Reduced opacity from 128 to 70
        
        if self.start_pos and self.current_pos:
            # Calculate selection rectangle
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            width = abs(self.current_pos.x() - self.start_pos.x())
            height = abs(self.current_pos.y() - self.start_pos.y())
            
            print(f"Drawing selection rectangle: x={x}, y={y}, width={width}, height={height}")
            
            # Make the selected area completely transparent
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.eraseRect(x, y, width, height)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Draw a more visible border around the selection
            pen = QPen(QColor(0, 120, 215), 3)  # Blue border
            painter.setPen(pen)
            painter.drawRect(x, y, width, height)
            
            # Draw size indicator
            size_text = f"{width} x {height}"
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            text_rect = QRect(x, y - 25, width, 20)
            painter.fillRect(text_rect, QColor(0, 0, 0, 160))  # Background for text
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, size_text)
        else:
            # Draw instructions
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(14)
            painter.setFont(font)
            
            # Add background to make text more readable
            text = "Click and drag to select an area\nPress Esc to cancel"
            text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            text_rect.adjust(-20, -10, 20, 10)  # Add padding
            text_rect.moveCenter(self.rect().center())
            painter.fillRect(text_rect, QColor(0, 0, 0, 160))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            print(f"Mouse pressed at: {event.pos().x()}, {event.pos().y()}")
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        print(f"Mouse moved to: {event.pos().x()}, {event.pos().y()}")
        if event.buttons() & Qt.MouseButton.LeftButton:  # Only update if left button is pressed
            self.current_pos = event.pos()
            self.update()

    def keyPressEvent(self, event):
        """Handle escape key to cancel screenshot"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def mouseReleaseEvent(self, event):
        print("\n=== Mouse Released ===")
        if not self.start_pos or not self.current_pos:
            print("No selection made, closing overlay")
            self.close()
            return
            
        # Calculate selection rectangle
        x = min(self.start_pos.x(), self.current_pos.x())
        y = min(self.start_pos.y(), self.current_pos.y())
        width = abs(self.current_pos.x() - self.start_pos.x())
        height = abs(self.current_pos.y() - self.start_pos.y())
        
        print(f"Selection area: x={x}, y={y}, width={width}, height={height}")
        
        # Check minimum size
        if width < self.min_size or height < self.min_size:
            print("Selection too small")
            self.close()
            if self.parent:
                self.parent.instructions_label.setText("Selection too small. Please try again.")
            return
            
        try:
            print("Taking screenshot...")
            # Get device pixel ratio for high DPI screens
            ratio = self.screen().devicePixelRatio()
            print(f"Screen device pixel ratio: {ratio}")
            
            # Convert to global coordinates with DPI scaling
            global_rect = self.mapToGlobal(QRect(x, y, width, height))
            scaled_rect = QRect(
                int(global_rect.x() * ratio),
                int(global_rect.y() * ratio),
                int(global_rect.width() * ratio),
                int(global_rect.height() * ratio)
            )
            
            print(f"Scaled screenshot area: {scaled_rect.x()}, {scaled_rect.y()}, {scaled_rect.width()}, {scaled_rect.height()}")
            
            # Take the screenshot
            screenshot = ImageGrab.grab(bbox=(
                scaled_rect.x(),
                scaled_rect.y(),
                scaled_rect.x() + scaled_rect.width(),
                scaled_rect.y() + scaled_rect.height()
            ))
            
            # Save with error handling
            screenshot_path = 'screenshot.png'
            screenshot.save(screenshot_path, 'PNG')
            print(f"Screenshot saved to: {screenshot_path}")
            
            if not os.path.exists(screenshot_path):
                raise Exception("Failed to save screenshot")
                
            # Close overlay
            self.close()
            
            # Process the screenshot after a short delay
            print("Processing screenshot...")
            QTimer.singleShot(100, lambda: self.parent.process_screenshot(screenshot_path))
            
        except Exception as e:
            print(f"ERROR taking screenshot: {str(e)}")
            import traceback
            print(traceback.format_exc())
            self.close()
            if self.parent:
                self.parent.instructions_label.setText(f"Error taking screenshot: {str(e)}")

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from modules.style_config import ThemeConfig
    
    app = QApplication(sys.argv)
    window = QMainWindow()
    theme = ThemeConfig()  # Create a proper theme instance
    widget = ScreenshotWidget(theme)  # Pass the theme to the widget
    window.setCentralWidget(widget)
    window.show()
    sys.exit(app.exec())
