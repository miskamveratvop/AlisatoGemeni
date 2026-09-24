import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Используем URL для актуальной модели, рекомендованной в прошлой ошибке
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    
    if not data or 'request' not in data:
        return jsonify({"version": "1.0", "response": {"text": "ok", "end_session": False}})

    user_text = data['request'].get('original_utterance', '').strip()
    is_new_session = data.get('session', {}).get('new', False)
    
    if is_new_session and not user_text:
        text_to_say = "Я на связи! Что спросим у нейросети?"
    elif not user_text:
        text_to_say = "Повторите, пожалуйста."
    else:
        try:
            # Формируем легкий прямой HTTP запрос к Google API
            payload = {
                "contents": [{"parts": [{"text": user_text}]}],
                "systemInstruction": {"parts": [{"text": "Ты голосовой помощник. Отвечай кратко, емко, без спецсимволов и маркдауна. Максимальная длина ответа — 1000 символов."}]}
            }
            headers = {'Content-Type': 'application/json'}
            
            # Отправляем запрос с таймаутом в 2.5 секунды, чтобы успеть ответить Яндексу
            response = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=2.5)
            
            if response.status_code == 200:
                result = response.json()
                text_to_say = result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"ОШИБКА API: {response.text}", flush=True)
                text_to_say = f"Ошибка ответа нейросети: {response.status_code}"
                
        except requests.exceptions.Timeout:
            print("ОШИБКА: Нейросеть не успела ответить вовремя", flush=True)
            text_to_say = "Нейросеть долго думает. Попробуйте еще раз."
        except Exception as e:
            print(f"ОШИБКА: {e}", flush=True)
            text_to_say = "Внутренняя ошибка сервера."

    # Ограничение Яндекса
    text_to_say = text_to_say[:1020].replace("*", "")

    return jsonify({
        "response": {
            "text": text_to_say,
            "end_session": False
        },
        "version": "1.0"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
