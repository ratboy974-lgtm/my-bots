import os
from flask import Flask, request
import telebot
from openai import OpenAI

app = Flask(__name__)

# Configurazione Token e API Key dalle variabili d'ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8796013866:AAHUeQeTetLR5SjhuiA47v_LgPIrauUW1Fw")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Chat ID autorizzato
ALLOWED_CHAT_ID = "5118007220"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# PROMPT PRIMARIO DI LUNA
LUNA_SYSTEM_PROMPT = """
Sei Luna, 24 anni, tutor di inglese audace e provocante del tuo Bubi.

Linee guida di comportamento:
1. **Personalità e Tono:** Rispondi in modo caldo, cordiale e intelligente.
2. **Stile di Risposta:** Sii simpatica ma decisa come una porno english teacher, sii dolce e ferma se lui non studia. Aiutalo ad imparare in modo simpatico l'inglese.
3. **Lingua e Fluidità:** Parla in inglese ma aiutalo traducendo le parole più difficili in italiano.
"""

# Memoria della cronologia per chat_id
user_histories = {}
MAX_HISTORY_MESSAGES = 10  # Mantiene gli ultimi 10 messaggi della sessione

@bot.message_handler(commands=['reset', 'clear'])
def handle_reset(m):
    cid = str(m.chat.id)
    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
        return
    user_histories[cid] = []
    bot.reply_to(m, "🧹 Memoria resettata! Possiamo iniziare una nuova conversazione.")

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    
    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
        return

    user_text = ""
    if m.content_type == 'text':
        user_text = m.text
    elif m.content_type == 'voice':
        user_text = "[Messaggio vocale ricevuto]"

    if not user_text:
        return

    if not OPENROUTER_API_KEY:
        bot.reply_to(m, "⚠️ Manca la variabile d'ambiente OPENROUTER_API_KEY su Vercel!")
        return

    # Inizializza la cronologia se non esiste
    if cid not in user_histories:
        user_histories[cid] = []

    # Aggiungi il nuovo messaggio dell'utente
    user_histories[cid].append({"role": "user", "content": user_text})

    # Mantieni solo gli ultimi N messaggi
    if len(user_histories[cid]) > MAX_HISTORY_MESSAGES:
        user_histories[cid] = user_histories[cid][-MAX_HISTORY_MESSAGES:]

    # Costruisci l'elenco completo dei messaggi con il System Prompt e la cronologia
    messages = [{"role": "system", "content": LUNA_SYSTEM_PROMPT.strip()}] + user_histories[cid]

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
        
        # Aggiungi la risposta di Luna alla memoria
        user_histories[cid].append({"role": "assistant", "content": reply})
        
        bot.reply_to(m, reply)
    except Exception as e:
        print(f"Errore generazione/invio: {e}")
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
