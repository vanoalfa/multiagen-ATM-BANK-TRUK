import json, os, time

delayKomunikasi = 2  # detik, dipakai semua agen

def save_log(sender, receiver, performative, content, conv):
    os.makedirs("logs", exist_ok=True)
    with open("logs/messages.log", "a") as f:
        f.write(json.dumps({
            "time": time.time(),
            "from": str(sender),
            "to": str(receiver),
            "performative": performative,
            "content": content,
            "conversation_id": conv
        }) + "\n")