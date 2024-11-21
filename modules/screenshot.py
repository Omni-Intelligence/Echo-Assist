import tkinter as tk
from PIL import Image, ImageTk, ImageGrab
import openai
import base64
import requests
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QPen
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
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Instructions label
        self.instructions_label = QLabel("Select an area to analyze...")
        self.instructions_label.setFont(self.theme.SMALL_FONT)
        self.instructions_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.get_color('text')};
                background-color: {self.theme.get_color('primary')};
                padding: 6px;
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.instructions_label)

        # Analysis text display
        self.analysis_display = QTextEdit()
        self.analysis_display.setReadOnly(True)
        self.analysis_display.setFont(self.theme.SMALL_FONT)
        self.analysis_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme.get_color('secondary')};
                color: {self.theme.get_color('text')};
                border: 1px solid {self.theme.get_color('border')};
                border-radius: 4px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {self.theme.get_color('secondary')};
                width: 8px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme.get_color('accent')};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                border: none;
                background: none;
                color: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        layout.addWidget(self.analysis_display)

    def showEvent(self, event):
        """Start screenshot mode when widget becomes visible"""
        super().showEvent(event)
        print("Screenshot widget is now visible, starting screenshot mode...")
        self.start_screenshot()

    def start_screenshot(self):
        print("Initializing screenshot overlay...")
        self.instructions_label.setText("Click and drag to select an area...")
        self.analysis_display.clear()
        self.screenshot_overlay = ScreenshotOverlay(self)
        self.screenshot_overlay.showFullScreen()
        print("Screenshot overlay is now visible")

    def process_screenshot(self, image_path):
        print("\n=== Starting Screenshot Analysis ===")
        try:
            print(f"1. Processing screenshot from: {image_path}")
            self.instructions_label.setText("Analyzing image...")
            
            # Verify the image exists and its size
            import os
            if os.path.exists(image_path):
                size = os.path.getsize(image_path)
                print(f"2. Image file exists, size: {size} bytes")
            else:
                print("ERROR: Image file does not exist!")
                self.instructions_label.setText("Error: Screenshot file not found")
                return
            
            # Encode the screenshot
            print("3. Encoding image to base64...")
            base64_image = self.encode_image(image_path)
            print(f"4. Image encoded successfully, length: {len(base64_image)} chars")

            # Prepare the API request
            print("5. Preparing API request...")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai.api_key}"
            }

            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please describe what you see in this image in detail."
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

            # Make the request to the OpenAI API
            print("6. Sending request to OpenAI API...")
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            print(f"7. Received response, status code: {response.status_code}")
            if response.status_code != 200:
                print(f"ERROR: API response error: {response.text}")
                self.instructions_label.setText("Error: API request failed")
                return
                
            result = response.json()
            print("8. Parsed JSON response successfully")
            
            # Display the analysis
            if 'choices' in result and len(result['choices']) > 0:
                analysis = result['choices'][0]['message']['content']
                print(f"9. Analysis received: {analysis[:100]}...")  # Print first 100 chars
                self.analysis_display.setText(analysis)
                self.instructions_label.setText("Select an area to analyze...")
                self.screenshot_taken.emit(analysis)
                print("=== Screenshot Analysis Complete ===\n")
            else:
                print(f"ERROR: Unexpected API response format: {result}")
                self.instructions_label.setText("Error: Unexpected API response")
                
        except Exception as e:
            print(f"ERROR in process_screenshot: {str(e)}")
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
            self.instructions_label.setText("Error analyzing image. Try again.")

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

class ScreenshotOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        print("Initializing ScreenshotOverlay...")
        self.parent = parent
        self.start_pos = None
        self.current_pos = None
        
        # Set window flags to stay on top and capture all screens
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Create semi-transparent overlay
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        print("ScreenshotOverlay initialized")

    def paintEvent(self, event):
        if self.start_pos and self.current_pos:
            painter = QPainter(self)
            
            # Fill the entire screen with semi-transparent overlay
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            
            # Calculate selection rectangle
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            width = abs(self.current_pos.x() - self.start_pos.x())
            height = abs(self.current_pos.y() - self.start_pos.y())
            
            # Clear the selected area
            painter.eraseRect(x, y, width, height)
            
            # Draw a border around the selection
            pen = QPen(QColor(0, 120, 215), 1)  # Blue border
            painter.setPen(pen)
            painter.drawRect(x, y, width, height)

    def mousePressEvent(self, event):
        print(f"Mouse pressed at: ({event.pos().x()}, {event.pos().y()})")
        self.start_pos = event.pos()
        self.current_pos = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.current_pos = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.start_pos and self.current_pos:
            print("\n=== Taking Screenshot ===")
            print(f"1. Mouse released at: ({event.pos().x()}, {event.pos().y()})")
            
            # Get the screen where the selection was made
            screen = QApplication.screenAt(event.globalPos())
            if not screen:
                print("WARNING: Couldn't detect screen at cursor position, using primary screen")
                screen = QApplication.primaryScreen()
            
            # Calculate selection rectangle in global coordinates
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            width = abs(self.current_pos.x() - self.start_pos.x())
            height = abs(self.current_pos.y() - self.start_pos.y())
            
            print(f"2. Selection area: x={x}, y={y}, width={width}, height={height}")
            
            # Convert to global coordinates
            global_rect = self.mapToGlobal(QRect(x, y, width, height))
            print(f"3. Global coordinates: x={global_rect.x()}, y={global_rect.y()}, " +
                  f"width={global_rect.width()}, height={global_rect.height()}")
            
            try:
                # Take the screenshot using PIL
                print("4. Attempting to capture screenshot...")
                screenshot = ImageGrab.grab(bbox=(
                    global_rect.x(),
                    global_rect.y(),
                    global_rect.x() + global_rect.width(),
                    global_rect.y() + global_rect.height()
                ))
                
                screenshot_path = 'screenshot.png'
                screenshot.save(screenshot_path)
                print(f"5. Screenshot saved to: {screenshot_path}")
                
                # Close the overlay and process the screenshot
                print("6. Closing overlay and processing screenshot...")
                self.close()
                self.parent.show()
                self.parent.process_screenshot(screenshot_path)
                
            except Exception as e:
                print(f"ERROR taking screenshot: {str(e)}")
                import traceback
                print("Full traceback:")
                print(traceback.format_exc())
                self.close()
                self.parent.show()
                self.parent.instructions_label.setText("Error taking screenshot")

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = ScreenshotWidget(None)
    widget.show()
    sys.exit(app.exec())
