# tests/tts_cli.py

import requests
import argparse
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", type=str)
    parser.add_argument("--volume", type=float)
    parser.add_argument("--voice", type=str)
    parser.add_argument("--engine", default="online")
    parser.add_argument("--stop", action="store_true", help="Stop current playback") # Added stop flag
    args = parser.parse_args()

    base_url = "http://127.0.0.1:8000"

    try:
        # Handle Stop Request (Priority)
        if args.stop:
            requests.post(f"{base_url}/stop", timeout=2)
            print("Stop command sent.")
            if not args.text: return # Exit if only stopping

        # Handle Volume Change
        if args.volume is not None and args.text is None:
            requests.post(f"{base_url}/volume", json={"volume": args.volume}, timeout=2)
            print(f"Volume set to {args.volume}")
        
        # Handle Speak Request
        elif args.text:
            payload = {
                "text": args.text,
                "engine": args.engine,
            }
            if args.voice:
                payload["voice"] = args.voice
            
            requests.post(f"{base_url}/speak", json=payload, timeout=5)
            print(f"Speaking: {args.text[:30]}...")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
