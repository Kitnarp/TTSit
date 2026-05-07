import time
from core.TTSFactory import TTSFactory

def test_tts_system():
    # 1. Get the shared AudioManager to set global settings
    audio_manager = TTSFactory.get_audio_manager()
    audio_manager.set_volume(0.7)


    print("\n--- Testing Offline TTS (pyttsx3) ---")
    # This will use the same AudioManager instance
    offline_engine = TTSFactory.get_engine("offline")

    offline_engine.speak("whatahttahtatatat.", voice="male_en")
    time.sleep(5)
    offline_engine.speak("Switching to offline mode now. No internet required for this part.", voice="male_en")
    time.sleep(10)

if __name__ == "__main__":
    try:
        test_tts_system()
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
