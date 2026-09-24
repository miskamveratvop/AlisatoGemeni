import os
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"

# Временная память сервера: запоминает ответы для каждого пользователя
user_answers = {}

def fetch_gemini_answer(user_id, text):
    """Фоновая функция: запрашивает ответ у Gemini и сохраняет его в память"""
    try:
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "systemInstruction": {"parts": [{"text": "Ты голосовой помощник. Отвечай кратко, емко, без спецсимволов и маркдауна. Максимальная длина ответа — 1000 символов."}]}
        }
        headers = {'Content-Type': 'application/json'}
        
        # Здесь мы можем дать нейросети целых 20 секунд на раздумья, Алису это уже не волнует
        response = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['candidates'][0]['content']['parts'][0]['text']
            user_answers[user_id] = answer[:1020].replace("*", "")
        else:
            user_answers[user_id] = f"Ошибка API Google: код {response.status_code}"
            
    except Exception as e:
        user_answers[user_id] = "Произошла внутренняя ошибка при запросе к нейросети."

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    
    # Защита от пустых пингов Яндекса
    if not data or 'request' not in data:
        return jsonify({"version": "1.0", "response": {"text": "ok", "end_session": False}})

    user_text = data['request'].get('original_utterance', '').strip()
    user_text_lower = user_text.lower()
    is_new_session = data.get('session', {}).get('new', False)
    
    # Получаем уникальный ID пользователя, чтобы не перепутать ответы, если навыком пользуются двое
    user_id = data.get('session', {}).get('user_id', 'default_user')
    
    # 1. Запуск навыка
    if is_new_session and not user_text:
        text_to_say = "Я на связи! Задайте вопрос, а потом скажите 'Переспрашиваю', чтобы узнать ответ."
        
    # 2. Проверка кодового слова (если пользователь хочет забрать ответ)
    elif "переспрашив" in user_text_lower or "что там" in user_text_lower or "ответ" in user_text_lower:
        status = user_answers.get(user_id)
        
        if status == "PROCESSING":
            text_to_say = "Еще думаю. Дайте мне еще немного времени."
        elif status:
            text_to_say = status
            # Удаляем ответ из памяти после того, как озвучили его
            user_answers.pop(user_id, None)
        else:
            text_to_say = "Я пока ничего не искала. Задайте мне вопрос."
            
    # 3. Пустой запрос
    elif not user_text:
        text_to_say = "Повторите, пожалуйста."
        
    # 4. Пользователь задает новый вопрос
    else:
        # Ставим статус "В процессе"
        user_answers[user_id] = "PROCESSING"
        
        # Запускаем общение с Gemini в параллельном невидимом потоке
        thread = threading.Thread(target=fetch_gemini_answer, args=(user_id, user_text))
        thread.start()
        
        # Моментально отвечаем Алисе, укладываясь в 3 секунды
        text_to_say = "Я подумаю, переспросите через пару минут."

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
