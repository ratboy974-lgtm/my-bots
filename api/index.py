import os
from flask import Flask, request
import telebot
from openai import OpenAI

app = Flask(__name__)

# Configurazione Token e API Key
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8796013866:AAHUeQeTetLR5SjhuiA47v_LgPIrauUW1Fw")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Chat ID autorizzato
ALLOWED_CHAT_ID = "5118007220"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    print(f"Chat ID rilevato: {cid}")
    
    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
        print(f"Accesso negato per ID: {cid}")
        return

    user_text = ""
    if m.content_type == 'text':
        user_text = m.text
    elif m.content_type == 'voice':
        user_text = "[Messaggio vocale ricevuto]"

    if not user_text:
        return

    # Controlla se la chiave API è stata caricata da Vercel
    if not OPENROUTER_API_KEY:
        bot.reply_to(m, "⚠️ Manca la variabile d'ambiente OPENROUTER_API_KEY su Vercel!")
        return

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Sei Luna, un'assistente IA amichevole, precisa ed empatica. Rispondi sempre in modo chiaro e utile."
                },
                {"role": "user", "content": user_text}
            ]
        )
        reply = response.choices[0].message.content
        bot.reply_to(m, reply)
    except Exception as e:
        print(f"Errore generazione/invio: {e}")
        # Invia l'errore reale direttamente su Telegram per il debug
        bot.reply_to(m, f"⚠️ Errore API:\n{str(e)}")

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def handle_webhook(path=""):
    if request.method == 'POST':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Errore webhook Luna: {e}")
        return "!", 200
    return "Luna V100 is Active! 🚀", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
