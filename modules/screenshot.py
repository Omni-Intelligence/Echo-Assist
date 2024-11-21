import tkinter as tk
import pyautogui
from PIL import Image
import openai
import base64
import requests
from PIL import ImageGrab

# Set your OpenAI API key
openai.api_key = "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"


# Function to encode the image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to take a screenshot
def take_screenshot():
    # Take screenshot
    screenshot = pyautogui.screenshot()
    screenshot_path = 'screenshot.png'
    screenshot.save(screenshot_path)  # Save the screenshot
    print("Screenshot taken and saved!")

    # Encode the screenshot to base64
    base64_image = encode_image(screenshot_path)

    # Prepare headers and payload
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }

    # Prepare payload with base64 image data
    payload = {
        "model": "gpt-4o-mini",  # Replace with the correct model
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is in this image?"
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
        "max_tokens": 300
    }

    # Make the POST request to OpenAI API
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # Print the response from OpenAI
    print("Response from OpenAI:", response.json())


# Set up the simple GUI using Tkinter
root = tk.Tk()
root.title("Simple Screenshot App")

# Create a button to capture the selected region of the screen
button = tk.Button(root, text="Take Screenshot of Region", command=take_screenshot_of_region)
button.pack(pady=20)

# Run the application
root.mainloop()

