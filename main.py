import os, telebot, threading, time, requests
from openai import OpenAI
from flask import Flask

# --- CONFIGURAZIONE SERVER PER RENDER (Health Check) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Luna & Cox sono attivi e pronti! 🚀", 200

def run_flask():
    # Render assegna una porta dinamica tramite variabile d'ambiente
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 1. SETUP CHIAVI E CLIENTI ---
L_TK = os.environ.get('TOKEN_LUNA', "")
C_TK = os.environ.get('TOKEN_COX', "")
AI_K = os.environ.get('OPENAI_API_KEY', "")

client = OpenAI(api_key=AI_K)
bot_luna = telebot.TeleBot(L_TK) if L_TK else None
bot_cox = telebot.TeleBot(C_TK) if C_TK else None

# --- FIX PER ERRORE 409 (CONFLITTO) ---
if bot_luna:
    try:
        bot_luna.remove_webhook()
        bot_luna.delete_webhook(drop_pending_updates=True)
    except: pass

if bot_cox:
    try:
        bot_cox.remove_webhook()
        bot_cox.delete_webhook(drop_pending_updates=True)
    except: pass

# --- 2. DATABASE MEMORIA ---
memoria_luna = {}
memoria_cox = {}

def aggiorna_memoria(database, chat_id, ruolo, testo):
    if chat_id not in database:
        database[chat_id] = []
    database[chat_id].append({"role": ruolo, "content": testo})
    if len(database[chat_id]) > 12:
        database[chat_id].pop(0)

# --- 3. FUNZIONI CORE (Audio & Immagini) ---

def trascrivi_vocale(bot, message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        audio_data = requests.get(file_url).content
        fname = f"v_{message.message_id}.ogg"
        with open(fname, "wb") as f: f.write(audio_data)
        with open(fname, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        os.remove(fname)
        return transcript.text if transcript and hasattr(transcript, 'text') else None
    except Exception as e:
        print(f"❌ Errore Whisper: {e}")
        return None

def genera_voce(testo, voce_scelta="nova"):
    try:
        fname = f"r_{int(time.time())}.mp3"
        res_audio = client.audio.speech.create(model="tts-1", voice=voce_scelta, input=testo)
        res_audio.stream_to_file(fname)
        return fname
    except Exception as e:
        print(f"❌ Errore TTS: {e}")
        return None

def genera_foto_luna(descrizione):
    try:
        prompt_f = (
            "A stunningly realistic photo of Luna, a beautiful woman in her 20s, "
            "long silky dark hair, deep brown eyes, warm skin. "
            "She has a seductive, mischievous but sweet expression. "
            "Intimate lighting, soft atmosphere."
        )
        res_image = client.images.generate(model="dall-e-3", prompt=prompt_f + f" Context: {descrizione}", n=1)
        if res_image and hasattr(res_image, 'data') and len(res_image.data) > 0:
            return res_image.data[0].url
        return None
    except Exception as e:
        print(f"⚠️ Errore DALL-E: {e}")
        return None

def chiedi_ai_con_memoria(database, chat_id, system_prompt, nuovo_testo):
    try:
        aggiorna_memoria(database, chat_id, "user", nuovo_testo)
        messages = [{"role": "system", "content": system_prompt}] + database[chat_id]
        res_chat = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        if res_chat and res_chat.choices:
            risposta = res_chat.choices[0].message.content
            if risposta:
                aggiorna_memoria(database, chat_id, "assistant", risposta)
                return risposta
        return None
    except Exception as e:
        print(f"❌ Errore GPT: {e}")
        return None

# --- 4. LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def h_luna(m):
        testo_input = m.text if m.content_type == 'text' else trascrivi_vocale(bot_luna, m)
        if not testo_input: return
        msg_low = testo_input.lower()
        parole_foto = ["foto", "immagine", "selfie", "mostrati", "sexy", "vederti"]
        if any(p in msg_low for p in parole_foto):
            bot_luna.send_message(m.chat.id, "Wait, let me get ready... (Aspetta, fammi preparare...)")
            url = genera_foto_luna(testo_input)
            if url:
                bot_luna.send_photo(m.chat.id, url, caption="Do you like it? (Ti piace?)")
            else:
                bot_luna.reply_to(m, "I'm feeling a bit shy right now! (Mi sento un po' timida ora!)")
            return
        p = ("Sei Luna, solare e flirtante. Insegni inglese (traduzione tra parentesi).")
        risposta_ai = chiedi_ai_con_memoria(memoria_luna, m.chat.id, p, testo_input)
        if risposta_ai:
            if m.content_type == 'voice':
                path = genera_voce(risposta_ai, "nova")
                if path:
                    with open(path, 'rb') as audio: bot_luna.send_voice(m.chat.id, audio)
                    os.remove(path)
            else:
                bot_luna.reply_to(m, risposta_ai)

# --- 5. LOGICA COX ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text', 'voice'])
    def h_cox(m):
        testo_input = m.text if m.content_type == 'text' else trascrivi_vocale(bot_cox, m)
        if not testo_input: return
        risposta_ai = chiedi_ai_con_memoria(memoria_cox, m.chat.id, "Sei il Dr. Cox di Scrubs, acido.", testo_input)
        if risposta_ai:
            if m.content_type == 'voice':
                path = genera_voce(risposta_ai, "onyx")
                if path:
                    with open(path, 'rb') as audio: bot_cox.send_voice(m.chat.id, audio)
                    os.remove(path)
            else:
                bot_cox.reply_to(m, risposta_ai)

# --- 6. AVVIO ---
if __name__ == "__main__":
    print("--- 🚀 LUNA & COX IN PARTENZA SU RENDER ---")
    
    # Avviamo il server Flask per Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Avviamo i bot (Corretto l'invio dei parametri via kwargs)
    if bot_luna: 
        threading.Thread(
            target=bot_luna.infinity_polling, 
            daemon=True, 
            kwargs={'timeout': 20, 'long_polling_timeout': 10}
        ).start()
        
    if bot_cox: 
        threading.Thread(
            target=bot_cox.infinity_polling, 
            daemon=True, 
            kwargs={'timeout': 20, 'long_polling_timeout': 10}
        ).start()
    
    # Loop infinito per tenere acceso il processo
    while True:
        time.sleep(1)
