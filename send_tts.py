# send_tts.py
import sys
import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def speak(text, profile=None, engine=None, voice=None):
    payload = {
        "profile": profile,
        "text": text,
        "engine": engine,
        "voice": voice,
    }
    resp = requests.post(f"{BASE_URL}/speak", json=payload)
    print(resp.text)    

def speakfile(path, profile=None, engine=None, voice=None):
    if not os.path.exists(path):
        print(f"Error: file not found {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    speak(text, profile, engine, voice)

def stop(profile=None):
    payload = {"profile": profile}
    resp = requests.post(f"{BASE_URL}/stop", json=payload)
    print(resp.text)

def stop_all():
    resp = requests.post(f"{BASE_URL}/stop_all")
    print(resp.text)

def status():
    resp = requests.get(f"{BASE_URL}/status")
    print(resp.text)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python send_tts.py speak <text> [profile] [engine] [voice]")
        print("  python send_tts.py speakfile <path> [profile] [engine] [voice]")
        print("  python send_tts.py stop [profile]")
        print("  python send_tts.py stop_all")
        print("  python send_tts.py status")
        return

    command = sys.argv[1].lower()

    try:
        if command == "speak":
            if len(sys.argv) < 3:
                print("Error: speak requires <text>")
                return
            text = sys.argv[2]
            profile = sys.argv[3] if len(sys.argv) > 3 else None
            engine = sys.argv[4] if len(sys.argv) > 4 else None
            voice = sys.argv[5] if len(sys.argv) > 5 else None
            print (f"tts: {text}, {profile}, {engine}, {voice}")
            speak(text, profile, engine, voice)

        elif command == "speakfile":
            if len(sys.argv) < 3:
                print("Error: speakfile requires <path>")
                return
            path = sys.argv[2]
            profile = sys.argv[3] if len(sys.argv) > 3 else None
            engine = sys.argv[4] if len(sys.argv) > 4 else None
            voice = sys.argv[5] if len(sys.argv) > 5 else None
            speakfile(path, profile, engine, voice)

        elif command == "stop":
            profile = sys.argv[2] if len(sys.argv) > 2 else None
            stop(profile)

        elif command == "stop_all":
            stop_all()

        elif command == "status":
            status()

        else:
            print(f"Unknown command: {command}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()