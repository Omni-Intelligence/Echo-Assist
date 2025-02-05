"""
Backend implementation for real-time chat using ElevenLabs API.
Revised to fix mic capture issues.
"""

import os
import queue
import threading
import time
import numpy as np
import pyaudio
from typing import Optional
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, AudioInterface

class AdvancedAudioInterface(AudioInterface):
    """Audio interface with advanced echo cancellation and noise reduction (simplified)."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 frames_per_buffer: int = 1024,
                 input_device_index: Optional[int] = None,  # Changed to None for default
                 output_device_index: Optional[int] = None):
        super().__init__()
        self.sample_rate = sample_rate
        self.frames_per_buffer = frames_per_buffer
        self.input_device_index = input_device_index
        self.output_device_index = output_device_index
        
        self.audio_queue = queue.Queue()
        self.is_speaking = False
        self.speaking_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._input_callback_fn = None
        
        # Initialize PyAudio
        self.pa = pyaudio.PyAudio()
        
        # Print all devices for debugging
        print("\nAvailable Audio Devices:")
        for i in range(self.pa.get_device_count()):
            dev_info = self.pa.get_device_info_by_index(i)
            print(f" - Device {i}: {dev_info['name']}")
        if self.input_device_index is not None:
            dev_info = self.pa.get_device_info_by_index(self.input_device_index)
            print(f"Selected input device: {dev_info['name']}")
        
        self._setup_streams()

    def _setup_streams(self):
        try:
            # Input (microphone) in callback mode
            self.input_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.frames_per_buffer,
                stream_callback=self._input_callback
            )
            
            # Output (speakers)
            self.output_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.output_device_index,
                frames_per_buffer=self.frames_per_buffer
            )
            
            print("Audio streams initialized successfully")
            print(f" - Input device index: {self.input_device_index}")
            print(f" - Output device index: {self.output_device_index}")
            print(f" - Sample rate: {self.sample_rate}")
            print(f" - Buffer size: {self.frames_per_buffer}")
            
            # **Important**: Manually start the input stream in callback mode
            self.input_stream.start_stream()
            print("Input stream started")
            
        except Exception as e:
            print(f"Error setting up audio streams: {e}")
            raise
    
    def _input_callback(self, in_data, frame_count, time_info, status):
        try:
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            audio_level = np.abs(audio_data).mean()
            
            # Very low threshold to ensure we pick up quiet speech
            threshold = 5
            
            # Debug
            if audio_level > threshold:
                print(f"Audio level: {audio_level:.2f} - capturing")
                self.audio_queue.put(in_data)
                if self._input_callback_fn:
                    self._input_callback_fn(in_data)
            
            if not self.input_stream.is_active():
                print("Input stream inactive in callback, restarting...")
                self.input_stream.start_stream()
            
            return (None, pyaudio.paContinue)
            
        except Exception as e:
            print(f"Error in input callback: {e}")
            return (None, pyaudio.paContinue)
    
    def start(self, input_callback=None) -> None:
        """
        Start audio capture with optional input callback.
        Revised so it doesn't bail out due to event logic.
        """
        print("start() called on AdvancedAudioInterface")
        self._stop_event.clear()
        self._input_callback_fn = input_callback
        
        if not hasattr(self, '_capture_thread') or not self._capture_thread.is_alive():
            self._capture_thread = threading.Thread(target=self._capture_audio_loop, daemon=True)
            self._capture_thread.start()
            print("Audio capture thread started")
    
    def _capture_audio_loop(self):
        """Continuously checks if the stream is active. If not, restarts it."""
        print("Audio capture loop started")
        while not self._stop_event.is_set():
            if not self.input_stream.is_active():
                print("Input stream became inactive; restarting...")
                self.input_stream.start_stream()
            time.sleep(0.1)
    
    def stop(self) -> None:
        """Stop audio capture."""
        print("stop() called on AdvancedAudioInterface")
        self._stop_event.set()
        if hasattr(self, '_capture_thread') and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.0)
        
        if hasattr(self, 'input_stream'):
            self.input_stream.stop_stream()
        if hasattr(self, 'output_stream'):
            self.output_stream.stop_stream()
        print("Audio capture stopped")
    
    def interrupt(self) -> None:
        """
        Interrupt current audio playback. Also ensures subsequent mic frames 
        are captured for debugging. 
        """
        with self.speaking_lock:
            self.is_speaking = False
            while not self.audio_queue.empty():
                self.audio_queue.get_nowait()
        print("Audio playback interrupted")
    
    def output(self, audio_data: bytes) -> None:
        """Output TTS data to speakers in a blocking fashion."""
        with self.speaking_lock:
            self.is_speaking = True
            print("Started speaking - is_speaking set to True")
        
        try:
            print(f"Playing TTS audio of length: {len(audio_data)} bytes")
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            chunk_size = self.frames_per_buffer
            
            for i in range(0, len(audio_array), chunk_size):
                chunk = audio_array[i : i + chunk_size]
                self.output_stream.write(chunk.tobytes())
            
            # brief delay
            time.sleep(0.1)
            print("TTS playback complete.")
            
        except Exception as e:
            print(f"Error during audio playback: {e}")
        finally:
            with self.speaking_lock:
                print("Finished speaking - is_speaking set to False")
                self.is_speaking = False
                print("Input stream active status:", self.input_stream.is_active())
                print("Input stream stopped status:", self.input_stream.is_stopped())
                if not self.input_stream.is_active():
                    print("Restarting input stream after speech...")
                    self.input_stream.start_stream()
            
    def process_audio(self, audio_data: bytes = None) -> None:
        """
        The conversation framework calls this to feed mic data upstream.
        We retrieve the top item from self.audio_queue.
        """
        try:
            data = self.audio_queue.get_nowait()
            print("Sending audio to conversation engine...")
            if self.input_stream and not self.input_stream.is_active():
                print("Input stream inactive during process_audio, restarting...")
                self.input_stream.start_stream()
            super().process_audio(data)
        except queue.Empty:
            if self.input_stream:
                print(f"Queue empty. Input stream active: {self.input_stream.is_active()}")
            pass

    def __del__(self):
        """Clean up."""
        self.stop()
        if hasattr(self, 'input_stream'):
            self.input_stream.close()
        if hasattr(self, 'output_stream'):
            self.output_stream.close()
        if hasattr(self, 'pa'):
            self.pa.terminate()
        print("Audio resources cleaned up")

class ChatBackend:
    """Handles the ElevenLabs conversation backend."""

    def __init__(self, 
                 on_agent_response: callable,
                 on_agent_correction: callable,
                 on_user_transcript: callable,
                 on_error: callable):
        self.conversation = None
        self.on_agent_response = on_agent_response
        self.on_agent_correction = on_agent_correction
        self.on_user_transcript = on_user_transcript
        self.on_error = on_error
        
    def start_conversation(self) -> bool:
        try:
            load_dotenv()
            agent_id = os.getenv("AGENT_ID")
            api_key = os.getenv("ELEVENLABS_API_KEY")
            
            if not agent_id:
                raise ValueError("AGENT_ID not set in environment.")
            
            client = ElevenLabs(api_key=api_key)
            
            # Use the advanced interface with hardcoded device index for HyperX SoloCast
            audio_if = AdvancedAudioInterface(
                sample_rate=16000,
                frames_per_buffer=1024,
                input_device_index=2,   # HyperX SoloCast
                output_device_index=None
            )
            
            self.conversation = Conversation(
                client=client,
                agent_id=agent_id,
                requires_auth=bool(api_key),
                audio_interface=audio_if,
                callback_agent_response=self.on_agent_response,
                callback_agent_response_correction=self.on_agent_correction,
                callback_user_transcript=self.on_user_transcript,
            )
            
            self.conversation.start_session()
            return True
        except Exception as e:
            self.on_error(str(e))
            self.stop_conversation()
            return False
    
    def stop_conversation(self) -> None:
        try:
            if self.conversation:
                self.conversation.end_session()
                self.conversation = None
        except Exception as e:
            self.on_error(str(e))
