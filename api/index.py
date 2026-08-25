import os
from flask import Flask, request
import telebot
from openai import OpenAI

app = Flask(__name__)

# Configurazione Token e API Key dalle variabili d'ambiente di Vercel
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8796013866:AAHUeQeTetLR5SjhuiA47v_LgPIrauUW1Fw")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Chat ID autorizzato
ALLOWED_CHAT_ID = "5118007220"

# Disabilita il multithreading per l'ambiente Serverless di Vercel
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

# Inizializzazione del client OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    print(f"Chat ID rilevato: {cid}")
    
    # Controllo di sicurezza sull'ID utente
    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
        print(f"Accesso negato per ID: {cid}")
        return

    # Estrazione del contenuto del messaggio
    user_text = ""
    if m.content_type == 'text':
        user_text = m.text
    elif m.content_type == 'voice':
        user_text = "[Messaggio vocale ricevuto]"

    if not user_text:
        return

    try:
        response = client.chat.completions.create(
            model="google/gemini-flash-1.5",  # Modello corretto e compatibile
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
        bot.reply_to(m, "Ops! Ho riscontrato un piccolo problema nella generazione della risposta.")

# Rotte Webhook universali per catturare ogni richiesta inoltrata da Vercel
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
