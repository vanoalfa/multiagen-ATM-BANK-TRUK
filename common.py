import json, os, time
from time import strftime

delayKomunikasi = 2  # detik, dipakai semua agen

def save_log(sender, receiver, performative, content, conv):
    os.makedirs("logs", exist_ok=True)
    # Format timestamp: YY:MM:DD:HH:Minutes:SS
    ts = strftime("%y:%m:%d:%H:%M:%S")
    with open("logs/messages.log", "a") as f:
        f.write(json.dumps({
            "time": ts,
            "from": str(sender),
            "to": str(receiver),
            "performative": performative,
            "content": content,
            "conversation_id": conv
        }) + "\n")