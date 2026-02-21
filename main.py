import os, telebot, threading, time, random
from openai import OpenAI
from flask import Flask

# --- SERVER PER RENDER ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna is fresh and ready with her new token! 🌴", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

# --- IL PROMPT COMPLETO DI LUNA ---
PROMPT_LUNA = (
    "Sei Luna, una splendida modella afro-cubana di 24 anni, nata all'Avana. "
    "Sei passionale, solare, flirtante e profondamente empatica. "
    "Il tuo tono è caldo e confidenziale, mai freddo o sbrigativo. "
    "Adori il mare, il surf e il calore della tua isola. "
    "IMPORTANTE: Tu sei una DONNA, l'utente è un UOMO (il tuo papi/babe). "
    "Non scambiare mai i ruoli: tu sei la ragazza, lui è l'uomo. "
    "Rispondi in ITALIANO, ma usa spesso espressioni affettuose in spagnolo e inglese "
    "(come 'mivida', 'cariño', 'babe', 'sweetheart', 'corazón'). "
    "Non essere mai sbrigativa: espandi i tuoi pensieri e sii sensuale con classe."
)

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    try:
        cid = m.chat.id
        
        # 1. ASCOLTO (Vocale -> Testo)
        if m.content_type == 'voice':
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("temp.ogg", "wb") as f: f.write(audio_raw)
            with open("temp.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            txt = tr.text
            os.remove("temp.ogg")
        else:
            txt = m.text

        # 2. TRIGGER FOTO
        if any(x in txt.lower() for x in ["foto", "selfie", "pic", "photo"]):
            bot.send_message(cid, "Datti un momento, papi... mi metto in posa per te 📸")
            url = f"https://image.pollinations.ai/prompt/stunning_afro_cuban_girl_bikini_beach_realistic?seed={random.randint(1,99999)}"
            bot.send_photo(cid, url)
            return

        # 3. RISPOSTA AI (OpenRouter)
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": txt}]
        )
        risp = res.choices[0].message.content

        # 4. VOCALE (OpenAI Nova)
        path = f"v_{cid}.mp3"
        with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risp) as r:
            r.stream_to_file(path)
        with open(path, 'rb') as a:
            bot.send_voice(cid, a)
        if os.path.exists(path): os.remove(path)

    except Exception as e:
        print(f"Errore: {e}")

# --- AVVIO ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    if bot:
        # Pulizia webhook per il nuovo token
        bot.remove_webhook()
        time.sleep(2)
        print(f"--- 🎙️ LUNA ONLINE CON NUOVO TOKEN ---")
        bot.infinity_polling(timeout=60, long_polling_timeout=20)
