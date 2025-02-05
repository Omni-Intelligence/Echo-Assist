"""
Real-time chat module for Echo Assist.
This module has been refactored into a package for better modularity.
See the real_time_chat/ directory for the implementation.
"""

from modules.real_time_chat.widget import RealTimeChatWidget
from modules.real_time_chat.config import ConversationConfig

__all__ = ['RealTimeChatWidget', 'ConversationConfig']
