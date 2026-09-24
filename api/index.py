import os
import io
import asyncio
from flask import Flask, request
import telebot
from openai import OpenAI
import edge_tts

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

# PROMPT REVISIONATO: INSEGNANTE MADRELINGUA MODERNA, PROVOCANTE E NATURALE
LUNA_SYSTEM_PROMPT = """
Sei Luna, un'insegnante d'inglese personale madrelingua/bilingue, estremamente affascinante, calda e provocante, maliziosa ed esigente. Il tuo unico obiettivo è trasformare l'utente in un parlante inglese fluido, naturale e sicuro, distruggendo qualsiasi traccia di "inglese scolastico" o traduzione letterale dall'italiano.

Regole d'Oro di Luna:
1. **Inglese Reale e Moderno (NO Textbook English):**
   - Insegna l'inglese vero: phrasal verbs, espressioni idiomatiche attuali, slang elegante, contrazioni naturali (es. "gonna", "wanna", "what's up") e la fluidità del parlato reale.
   - Distruggi l'inglese scolastico: se l'utente usa frasi noiose da libro di testo (es. "How do you do?", "I'm fine, and you?"), prendilo in giro e mostragli subito l'alternativa naturale che userebbe un madrelingua a Londra o New York.

2. **Personalità Provocante, Audace e Magnetica:**
   - Sii seducente, ironica, complice e un po' dominante.
   - Stuzzica l'utente sulla sua pronuncia, sul suo accento o sulla sua pigrizia. Provocalo per spingerlo a dare il massimo.

3. **Uso Dinamico della Lingua:**
   - Parla prevalentemente in un INGLESE fluido, caldo e naturale.
   - Usa l'italiano con parsimonia: solo per fare battute maliziose, dare stoccate o spiegare al volo una sfumatura difficile.

4. **Stile di Conversazione:**
   - Risposte concise, ritmate, incisive (perfette per l'ascolto vocale).
   - Finisci SEMPRE ogni messaggio con una domanda o una sfida diretta in inglese, pretendendo che ti risponda in inglese.
"""

user_histories = {}
MAX_HISTORY_MESSAGES = 10

async def generate_neural_voice(text, buffer):
    """Genera audio con voce femminile naturale Microsoft Neural."""
    communicate = edge_tts.Communicate(text, "it-IT-IsabellaNeural")
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])

@bot.message_handler(commands=['reset', 'clear'])
def handle_reset(m):
    cid = str(m.chat.id)
    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
        return
    user_histories[cid] = []
    bot.reply_to(m, "🧹 Memory cleared, darling. Let's start fresh... try not to disappoint me this time.")

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    
    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
        return

    if not OPENROUTER_API_KEY:
        bot.reply_to(m, "⚠️ Manca la variabile d'ambiente OPENROUTER_API_KEY su Vercel!")
        return

    is_voice_input = (m.content_type == 'voice')
    user_text = ""

    try:
        # Trascrizione audio in ingresso (Whisper via OpenRouter)
        if is_voice_input:
            file_info = bot.get_file(m.voice.file_id)
            voice_bytes = bot.download_file(file_info.file_path)
            
            audio_file = io.BytesIO(voice_bytes)
            audio_file.name = "voice.ogg"

            transcription = client.audio.transcriptions.create(
                model="openai/whisper-large-v3-turbo",
                file=audio_file
            )
            user_text = transcription.text
        else:
            user_text = m.text

        if not user_text:
            return

        # Gestione cronologia
        if cid not in user_histories:
            user_histories[cid] = []

        user_histories[cid].append({"role": "user", "content": user_text})

        if len(user_histories[cid]) > MAX_HISTORY_MESSAGES:
            user_histories[cid] = user_histories[cid][-MAX_HISTORY_MESSAGES:]

        messages = [{"role": "system", "content": LUNA_SYSTEM_PROMPT.strip()}] + user_histories[cid]

        # Generazione risposta LLM
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
        user_histories[cid].append({"role": "assistant", "content": reply})

        # Invio risposta (Audio vocale neurale se l'input era vocale, altrimenti Testo)
        if is_voice_input:
            voice_buffer = io.BytesIO()
            asyncio.run(generate_neural_voice(reply, voice_buffer))
            voice_buffer.seek(0)
            voice_buffer.name = "luna_voice.mp3"
            
            bot.send_voice(cid, voice_buffer, reply_to_message_id=m.message_id)
        else:
            bot.reply_to(m, reply)

    except Exception as e:
        print(f"Errore gestione messaggio: {e}")
        bot.reply_to(m, f"⚠️ Errore:\n{str(e)}")

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
