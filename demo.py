import os
import signal
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    # Load your Agent ID and API Key from environment variables
    agent_id = os.getenv("AGENT_ID")                # Required for both public and private agents
    api_key = os.getenv("ELEVENLABS_API_KEY")       # Required only if your agent is private
    
    print("Environment variables present:")
    print(f"AGENT_ID: {'YES' if agent_id else 'NO'} (Length: {len(str(agent_id)) if agent_id else 0})")
    print(f"ELEVENLABS_API_KEY: {'YES' if api_key else 'NO'} (Length: {len(str(api_key)) if api_key else 0})")
    
    if not agent_id:
        raise ValueError("AGENT_ID environment variable is not set")

    # Create the ElevenLabs client
    client = ElevenLabs(api_key=api_key)

    # Initialize the Conversation
    conversation = Conversation(
        client,
        agent_id,
        requires_auth=bool(api_key),  # If there's an API key, auth is required
        audio_interface=DefaultAudioInterface(),
        # Simple callbacks to print conversation transcripts
        callback_agent_response=lambda text: print(f"Agent: {text}"),
        callback_agent_response_correction=lambda original, corrected: \
            print(f"Agent corrected: {original} -> {corrected}"),
        callback_user_transcript=lambda transcript: print(f"User: {transcript}"),
    )

    # Start the session
    conversation.start_session()

    # Handle Ctrl+C to cleanly end the session
    signal.signal(signal.SIGINT, lambda sig, frame: conversation.end_session())

    # Wait for the session to finish, then print the conversation ID
    conversation_id = conversation.wait_for_session_end()
    print(f"Conversation ID: {conversation_id}")

if __name__ == "__main__":
    main()
