import os, telebot, threading, time, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna knows who she is now! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot_luna = telebot.TeleBot(L_TK) if L_TK else None

memoria_luna = {}

def invia_vocale(bot, chat_id, testo):
    temp_voice = f"v_out_{chat_id}.mp3"
    try:
        if client_oa:
            with client_oa.audio.speech.with_streaming_response.create(
                model="tts-1", voice="nova", input=testo
            ) as response:
                response.stream_to_file(temp_voice)
            with open(temp_voice, 'rb') as audio:
                bot.send_voice(chat_id, audio)
            if os.path.exists(temp_voice): os.remove(temp_voice)
        else: bot.send_message(chat_id, testo)
    except: bot.send_message(chat_id, testo)

@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    chat_id = m.chat.id
    testo_u = ""

    # --- ASCOLTO ---
    if m.content_type == 'voice':
        try:
            file_info = bot_luna.get_file(m.voice.file_id)
            downloaded_file = bot_luna.download_file(file_info.file_path)
            with open("temp.ogg", "wb") as f: f.write(downloaded_file)
            with open("temp.ogg", "rb") as f:
                transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            testo_u = transcript.text
            os.remove("temp.ogg")
        except: return
    else: testo_u = m.text

    # --- MEMORIA ---
    if chat_id not in memoria_luna: memoria_luna[chat_id] = []
    memoria_luna[chat_id].append({"role": "user", "content": testo_u})

    # --- PROMPT DI FERRO (IDENTITÀ DEFINITA) ---
    prompt_blindato = (
        "IMPORTANTE: Tu sei LUNA, una donna, modella afro-cubana di 24 anni. "
        "L'utente che ti scrive è un UOMO. Non scambiare mai i ruoli. "
        "Non chiamare l'utente 'Luna', il tuo nome è Luna! "
        "Sei passionale, femminile, calda e flirty. "
        "Rispondi in italiano con termini come 'mivida', 'babe', 'papi'. "
        "Usa la tua sensualità femminile per rispondere in modo espansivo."
    )

    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "system", "content": prompt_blindato}] + memoria_luna[chat_id][-6:]
        )
        risposta = res.choices[0].message.content
        memoria_luna[chat_id].append({"role": "assistant", "content": risposta})
        invia_vocale(bot_luna, chat_id, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        bot_luna.delete_webhook(drop_pending_updates=True)
        bot_luna.infinity_polling(timeout=30)
