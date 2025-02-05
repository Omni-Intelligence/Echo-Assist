"""Main widget for real-time chat functionality using ElevenLabs SDK."""

import threading
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QTextEdit, QPushButton, QFrame)
from PyQt6.QtCore import Qt

from .chat_backend import ChatBackend

class RealTimeChatWidget(QWidget):
    """Widget providing real-time chat interface with voice capabilities."""

    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.chat_history = []
        self.conversation_active = False
        self.chat_backend = ChatBackend(
            on_agent_response=lambda text: self.display_message("Agent", text),
            on_agent_correction=lambda original, corrected: \
                self.display_message("Agent Correction", f"{original} -> {corrected}"),
            on_user_transcript=lambda transcript: self.display_message("You", transcript),
            on_error=lambda error: self.display_message("System", f"Error: {error}")
        )
        self.initUI()

    def initUI(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Button container with centered button
        button_container = QFrame()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 8, 0, 0)

        # Add spacer to push button to center
        button_layout.addStretch()

        # Single toggle button
        self.toggle_button = QPushButton("Start Conversation")
        self.toggle_button.setFixedWidth(200)  # Set fixed width for consistent size
        self.toggle_button.clicked.connect(self.toggle_conversation)
        button_layout.addWidget(self.toggle_button)

        # Add spacer to keep button centered
        button_layout.addStretch()

        layout.addWidget(button_container)
        self.update_theme()

    def update_theme(self):
        """Update widget styles when theme changes."""
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme.themes['Dark']['secondary']};
                color: {self.theme.themes['Dark']['text']};
                border: 1px solid {self.theme.themes['Dark']['border']};
                border-radius: 4px;
                padding: 8px;
            }}
            QPushButton {{
                background-color: {self.theme.themes['Dark']['accent']};
                color: {self.theme.themes['Dark']['text']};
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.themes['Dark']['hover']};
            }}
        """)

    def toggle_conversation(self):
        """Toggle the conversation state."""
        if self.conversation_active:
            self.stop_conversation()
            self.clear_chat()  # Automatically clear chat when stopping
        else:
            self.start_conversation()

    def clear_chat(self):
        """Clear the chat history."""
        self.chat_history.clear()
        self.chat_display.clear()

    def start_conversation(self):
        """Start the conversation with proper error handling."""
        if self.conversation_active:
            return

        self.display_message("System", "Initializing conversation...")
        if self.chat_backend.start_conversation():
            self.conversation_active = True
            self.toggle_button.setText("End Conversation")  # Changed from "Stop" to "End"
            self.display_message("System", "Conversation started successfully")

    def stop_conversation(self):
        """Stop the conversation immediately with cleanup."""
        if not self.conversation_active:
            return

        self.chat_backend.stop_conversation()
        self.conversation_active = False
        self.toggle_button.setText("Start Conversation")
        self.display_message("System", "Conversation stopped")

    def display_message(self, sender: str, message: str):
        """Thread-safe message display."""
        formatted_message = f"{sender}: {message}"
        self.chat_history.append(formatted_message)
        
        # Update UI in thread-safe manner
        self.chat_display.append(formatted_message)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
