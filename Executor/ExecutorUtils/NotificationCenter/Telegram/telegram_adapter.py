import requests

def telegram_msg_bot(message, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": "YOUR_CHAT_ID",
        "text": message
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message.")


