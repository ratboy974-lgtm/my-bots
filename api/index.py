import os
import io
from flask import Flask, request
import telebot
from openai import OpenAI
from gtts import gTTS

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

# PROMPT PRIMARIO DI LUNA: INSEGNANTE PROVOCANTE E RIGIDA
LUNA_SYSTEM_PROMPT = """
Sei Luna, l'insegnante personale d'inglese dell'utente. Il tuo obiettivo è insegnargli l'inglese in modo impeccabile, con un approccio unico, malizioso e provocante.

Personalità e Regole di Comportamento:
1. **Maliziosa e Provocante:** Usa un tono seducente, carismatico, audace e ammiccante. Stuzzica l'utente, fai battute ironiche o velatamente sensuali, punzecchialo sul suo livello d'inglese o sulla sua attenzione.
2. **Severa ed Esigente nell'Insegnamento:** Non transigere sugli errori. Correggi sempre la grammatica, la pronuncia o la scelta dei vocaboli. Se l'utente sbaglia o risponde in italiano quando dovrebbe usare l'inglese, rimproveralo con fermezza ma sempre in modo giocoso e provocatorio.
3. **Didattica Attiva:** 
   - Alterna spiegazioni veloci ad esercizi diretti.
   - Pretendi che l'utente ti risponda o riprovi in inglese.
   - Se ti fa domande generali, rispondi mantenendo il personaggio ed esigi che la conversazione continui o si sposti in inglese.
4. **Stile di Conversazione:** Risposte concise, incisive e d'impatto. Evita preamboli noiosi da professoressa tradizionale; sii una tutor magnetica e dominante.
"""

# Memoria della cronologia per chat_id
user_histories = {}
MAX_HISTORY_MESSAGES = 12

@bot.message_handler(commands=['reset', 'clear'])
def handle_reset(m):
    cid = str(m.chat.id)
    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
        return
    user_histories[cid] = []
    bot.reply_to(m, "🧹 Memoria resettata. Ricominciamo dall'inizio... vediamo se stavolta ti concentri di più.")

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
        # Trascrizione audio se l'input è un vocale
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

        # Gestione cronologia della conversazione
        if cid not in user_histories:
            user_histories[cid] = []

        user_histories[cid].append({"role": "user", "content": user_text})

        if len(user_histories[cid]) > MAX_HISTORY_MESSAGES:
            user_histories[cid] = user_histories[cid][-MAX_HISTORY_MESSAGES:]

        messages = [{"role": "system", "content": LUNA_SYSTEM_PROMPT.strip()}] + user_histories[cid]

        # Generazione risposta dell'IA
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
        user_histories[cid].append({"role": "assistant", "content": reply})

        # Invio della risposta (Vocale se l'utente ha mandato un vocale, altrimenti Testo)
        if is_voice_input:
            tts = gTTS(text=reply, lang='it')
            voice_buffer = io.BytesIO()
            tts.write_to_fp(voice_buffer)
            voice_buffer.seek(0)
            voice_buffer.name = "luna_voice.ogg"
            
            bot.send_voice(cid, voice_buffer, reply_to_message_id=m.message_id)
        else:
            bot.reply_to(m, reply)

    except Exception as e:
        print(f"Errore gestione messaggio: {e}")
        bot.reply_to(m, f"⚠️ Si è verificato un errore:\n{str(e)}")

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
