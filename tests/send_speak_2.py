import requests

# Start playback on track "alerts"
resp = requests.post("http://127.0.0.1:8000/speak", json={
    "profile": "track1",
    "text": """
🤸💋👠🪮
In mathematics, a monomial is, roughly speaking, a polynomial which has only 
one term. Two definitions of a monomial may be encountered:
    """
})