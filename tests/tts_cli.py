import requests
import argparse
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", type=str)
    parser.add_argument("--volume", type=float)
    parser.add_argument("--voice", type=str) # New voice argument
    parser.add_argument("--engine", default="online")
    args = parser.parse_args()

    base_url = "http://127.0.0.1:8000"

    try:
        # Handle Volume Change
        if args.volume is not None and args.text is None:
            requests.post(f"{base_url}/volume", json={"volume": args.volume}, timeout=2)
        
        # Handle Speak Request
        elif args.text:
            payload = {
                "text": args.text,
                "engine": args.engine,
                "volume": args.volume or 0.8
            }
            if args.voice:
                payload["voice"] = args.voice # Send specific voice to server
            
            requests.post(f"{base_url}/speak", json=payload, timeout=5)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
