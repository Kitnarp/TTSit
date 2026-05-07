import requests
import time

# The URL where your FastAPI server is running
BASE_URL = "http://127.0.0.1:8000"

def send_speak(text, engine="online", voice=None, volume=None):
    payload = {"text": text, "engine": engine}
    if voice:
        payload["voice"] = voice
    if volume is not None:
        payload["volume"] = volume

    print(f"[Client] Sending {engine} request: {text}")
    try:
        response = requests.post(f"{BASE_URL}/speak", json=payload)
        return response.json()
    except Exception as e:
        print(f"[Client] Connection Error: {e}")

def set_volume(level):
    print(f"[Client] Changing system volume to {level * 100}%")
    requests.post(f"{BASE_URL}/volume", json={"volume": level})

def test_suite():
    print("--- Starting TTS System Test ---")

    # 1. Test Online (Edge-TTS)
    send_speak("Hello! This is a test of the online streaming engine via F Fmpeg.", 
               engine="online", voice="female_en")
    
    # 2. Test Volume Change Mid-Speech
    time.sleep(2)
    set_volume(0.2) # Drop volume while it's talking
    
    time.sleep(3)
    set_volume(0.8) # Raise it back up
    
    # 3. Test Interruption (Stop current and start new)
    time.sleep(1)
    send_speak("I am interrupting the previous sentence with this new one.", engine="online")
    
    time.sleep(5)

    # 4. Test Offline (pyttsx3)
    send_speak("Switching to offline mode now. This uses the local system voice.", 
               engine="offline", voice="male_en")

    print("\n--- Test Suite Finished ---")

if __name__ == "__main__":
    # Ensure you have 'requests' installed: pip install requests
    test_suite()
