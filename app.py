import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)

# Инициализация Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Используем самую новую модель gemini-3.6-flash, как требует API Google
model = genai.GenerativeModel(
    'gemini-3.6-flash',
    system_instruction="Ты голосовой помощник. Отвечай кратко, емко, без спецсимволов и маркдауна (без звездочек и решеток). Максимальная длина ответа — 1000 символов."
)

@app.route('/', methods=['POST'])
def webhook():
    # Получаем данные от Яндекса
    data = request.json
    
    # Извлекаем текст, который сказал пользователь
    user_text = data.get('request', {}).get('original_utterance', '').strip()
    is_new_session = data.get('session', {}).get('new', False)
    
    # 1. Если навык только запустили
    if is_new_session and not user_text:
        text_to_say = "Я на связи! Что спросим у нейросети?"
        
    # 2. Если текста нет (Алиса не расслышала)
    elif not user_text:
        text_to_say = "Я не расслышала, повторите пожалуйста."
        
    # 3. Если есть вопрос — отправляем в Gemini
    else:
        try:
            response = model.generate_content(user_text)
            text_to_say = response.text
        except Exception as e:
            # Выводим ошибку в консоль Render
            print(f"ОШИБКА GEMINI: {e}", flush=True)
            text_to_say = "Произошла ошибка связи с нейросетью."

    # Алиса падает с ошибкой, если текст больше 1024 символов. Подстрахуемся.
    text_to_say = text_to_say[:1020]

    # Формируем JSON в том формате, который понимает Алиса
    return jsonify({
        "response": {
            "text": text_to_say,
            "end_session": False
        },
        "version": "1.0"
    })

# Запуск сервера
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
