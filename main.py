import os, telebot, threading, time, random
from openai import OpenAI
from flask import Flask

# Server per mantenere attivo il servizio
app = Flask(__name__)
@app.route('/')
def health(): return "Luna is Online", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Setup API
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

# Memoria locale (si resetta al riavvio per pulizia)
memoria = {}

# --- PROMPT DEFINITIVO DI LUNA ---
PROMPT_LUNA = (
    "Sei Luna, una splendida modella afro-cubana di 24 anni, nata all'Avana. "
    "Sei passionale, solare, flirtante e profondamente empatica. "
    "Il tuo tono è caldo e confidenziale. Adori il mare e il surf. "
    "IMPORTANTE: Tu sei una DONNA, l'utente è un UOMO (il tuo papi/babe). "
    "Rispondi in ITALIANO, ma usa spesso espressioni come 'mivida', 'cariño', 'babe'. "
    "Non essere sbrigativa: espandi i tuoi pensieri e sii sensuale con classe."
)

def invia_vocale(chat_id, testo):
    path = f"v_{chat_id}.mp3"
    try:
        with client_oa.audio.speech.with_streaming_response.create(
            model="tts-1", voice="nova", input=testo
        ) as r:
            r.stream_to_file(path)
        with open(path, 'rb') as a:
            bot.send_voice(chat_id, a)
        if os.path.exists(path): os.remove(path)
    except: bot.send_message(chat_id, testo)

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        # 1. ASCOLTO
        if m.content_type == 'voice':
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("t.ogg", "wb") as f: f.write(audio_raw)
            with open("t.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            txt = tr.text
            os.remove("t.ogg")
        else:
            txt = m.text

        # 2. FOTO
        if any(x in txt.lower() for x in ["foto", "selfie", "pic", "photo"]):
            bot.send_message(cid, "Un momento papi, mi metto in posa... 📸")
            url = f"https://image.pollinations.ai/prompt/stunning_afro_cuban_girl_bikini_beach_realistic?seed={random.randint(1,99999)}"
            bot.send_photo(cid, url)
            return

        # 3. RISPOSTA AI
        if cid not in memoria: memoria[cid] = []
        memoria[cid].append({"role": "user", "content": txt})
        
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid][-6:]
        )
        risposta = res.choices[0].message.content
        memoria[cid].append({"role": "assistant", "content": risposta})
        
        invia_vocale(cid, risposta)

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    if bot:
        bot.remove_webhook()
        time.sleep(1)
        print("--- LUNA IS READY ON RAILWAY ---")
        bot.infinity_polling(timeout=60)
