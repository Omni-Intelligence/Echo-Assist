"""Test script for the refactored real-time chat module."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from modules.style_config import ThemeConfig
from modules.real_time_chat import RealTimeChatWidget, ConversationConfig

def test_widget_creation():
    """Test that the widget can be created and initialized."""
    print("Testing widget creation...")
    theme = ThemeConfig()
    widget = RealTimeChatWidget(theme)
    assert widget is not None
    print("[PASS] Widget created successfully")
    return widget

def test_audio_interface(widget):
    """Test that the audio interface is properly initialized."""
    print("\nTesting audio interface...")
    assert widget.audio_interface is not None
    print(f"[PASS] Audio interface initialized: {widget.audio_interface.__class__.__name__}")
    print(f"[PASS] Input device index: {widget.audio_interface.input_device}")
    print(f"[PASS] Output device index: {widget.audio_interface.output_device}")

def test_conversation_config():
    """Test that the conversation config is working."""
    print("\nTesting conversation config...")
    config = ConversationConfig()
    assert config.api_key is not None, "API key not found"
    
    wss_url = config.get_wss_url()
    assert "wss://api.elevenlabs.io" in wss_url
    print("[PASS] WebSocket URL generated correctly")
    
    conv_config = config.get_conversation_config()
    assert "textInput" in conv_config
    assert "voiceId" in conv_config
    print("[PASS] Conversation config generated correctly")

def test_ui_elements(widget):
    """Test that all UI elements are present and properly configured."""
    print("\nTesting UI elements...")
    assert hasattr(widget, 'chat_display')
    assert hasattr(widget, 'toggle_button')
    print("[PASS] All UI elements present")
    
    # Test chat display properties
    assert widget.chat_display.isReadOnly()
    print("[PASS] Chat display configured correctly")
    
    # Test button text
    assert widget.toggle_button.text() == "Start Conversation"
    print("[PASS] Button text set correctly")

def run_tests():
    """Run all tests."""
    print("Starting Real-Time Chat Module Tests\n" + "="*40)
    
    app = QApplication(sys.argv)
    
    try:
        # Run tests
        widget = test_widget_creation()
        test_audio_interface(widget)
        test_conversation_config()
        test_ui_elements(widget)
        
        print("\nAll tests passed successfully!")
        
        # Optional: Show widget for visual inspection
        widget.show()
        
        # Set a timer to close the application after 5 seconds
        QTimer.singleShot(5000, app.quit)
        
        # Start the event loop
        app.exec()
        
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {str(e)}")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
    finally:
        print("\nTest session completed.")

if __name__ == '__main__':
    run_tests()
