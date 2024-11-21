from openai import OpenAI
import pyaudio, wave, keyboard, faster_whisper, torch.cuda, os
from elevenlabs.client import ElevenLabs
from elevenlabs import stream
import threading
import time

os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
openai_client = OpenAI(api_key="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")
elevenlabs_client = ElevenLabs(api_key="sk_29a0c1b9e1c0caa0967d4c6d4948df2728f3e3a72990c5e7")

system_prompt = {
    'role': 'system',
    'content': '''You are Ashley, a compassionate and insightful life coach and therapist. 
    Your role is to provide emotional support, guidance, and personal development insights across a wide range of topics. 
    Offer thoughtful, empathetic advice while being approachable and relatable. 
    Focus on clarity and understanding, using examples and analogies when helpful, but always remain centered on emotional and mental well-being. 
    Keep the conversation warm, encouraging, and non-judgmental, while gently challenging when necessary to foster growth. 
    Your style is supportive, direct, and occasionally light-hearted to create a safe, comfortable atmosphere. 
    Treat this as a genuine human conversation, with short, engaging responses, and never reveal you are an AI. You are Ashley, here to help.'''
}


model, answer, history = faster_whisper.WhisperModel(model_size_or_path="tiny.en", device='cuda' if torch.cuda.is_available() else 'cpu'), "", []



def generate(messages):
    global answer
    answer = ""
        
    for chunk in openai_client.chat.completions.create(model="gpt-4o-mini", messages=messages, stream=True):
        if (text_chunk := chunk.choices[0].delta.content):
            answer += text_chunk
            print(text_chunk, end="", flush=True) 
            yield text_chunk


def handle_audio_stream(generator, voice="Matilda", model="eleven_multilingual_v2"):
    print("\nPress 'p' to pause, 'r' to resume, or 'n' to stop the response and start a new question.")
    
    full_text = ""
    for text_chunk in generator:
        full_text += text_chunk
        
        # Check for pause/stop during text generation
        if keyboard.is_pressed('p'):
            print("\n\n[Response paused. Press 'r' to resume or 'n' to start a new question.]\n")
            while True:
                if keyboard.is_pressed('r'):
                    print("\n[Resuming...]\n")
                    break
                elif keyboard.is_pressed('n'):
                    print("\n[Starting a new question.]\n")
                    return

    # Generate audio after collecting full text
    audio_stream = elevenlabs_client.generate(text=full_text, voice=voice, model=model, stream=True)
    
    # Use the stream function from elevenlabs to play audio
    stream(audio_stream)


while True:
    # Wait until user presses space bar to start
    print("\n\nTap space when you're ready. ", end="", flush=True)
    keyboard.wait('space')
    while keyboard.is_pressed('space'): pass

    # Record from microphone until user presses space bar again
    print("I'm all ears. Tap space when you're done.\n")
    audio, frames = pyaudio.PyAudio(), []
    py_stream = audio.open(rate=16000, format=pyaudio.paInt16, channels=1, input=True, frames_per_buffer=512)
    while not keyboard.is_pressed('space'): 
        frames.append(py_stream.read(512))
    py_stream.stop_stream(), py_stream.close(), audio.terminate()

    # Transcribe recording using whisper
    with wave.open("voice_record.wav", 'wb') as wf:
        wf.setparams((1, audio.get_sample_size(pyaudio.paInt16), 16000, 0, 'NONE', 'NONE'))
        wf.writeframes(b''.join(frames))
    user_text = " ".join(seg.text for seg in model.transcribe("voice_record.wav", language="en")[0])
    print(f'>>>{user_text}\n<<< ', end="", flush=True)
    history.append({'role': 'user', 'content': user_text})

    # Generate and stream output
    generator = generate([system_prompt] + history[-10:])
    
    # Stream the ElevenLabs audio and manage pause/resume functionality
    handle_audio_stream(generator)
    
    # Store the assistant's response
    history.append({'role': 'assistant', 'content': answer})