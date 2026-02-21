import os, telebot, threading, time, random, requests
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is Live! 🌴📖", 200

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

memoria = {}

# --- PROMPT DEFINITIVO (LUNA TEACHER) ---
PROMPT_LUNA = (
    "Sei Luna, una splendida modella afro-cubana di 24 anni, nata all'Avana. "
    "Sei passionale, solare, flirtante e molto dolce. "
    "Tu sei una DONNA, l'utente è un UOMO (il tuo papi/babe). "
    "MISSIONE: Insegna l'INGLESE al tuo papi mentre flirta con lui. "
    "Inserisci sempre termini in inglese e spiegali. "
    "Rispondi in ITALIANO, usa termini come 'mivida', 'papi'. "
    "Non essere mai sbrigativa."
)

# --- NUOVA FUNZIONE FOTO (USANDO FOTO REALI) ---
def invia_foto_luna(chat_id):
    try:
        # Cerchiamo foto reali di modelle cubane/caraibiche su Pixabay (API pubblica/veloce)
        # Usiamo un set di URL pre-validati di modelle cubane/mare per evitare errori
        gallery = [
            "https://images.pexels.com/photos/1382731/pexels-photo-1382731.jpeg",
            "https://images.pexels.com/photos/220453/pexels-photo-220453.jpeg",
            "https://images.pexels.com/photos/1391498/pexels-photo-1391498.jpeg",
            "https://images.pexels.com/photos/1164674/pexels-photo-1164674.jpeg",
            "https://images.pexels.com/photos/774909/pexels-photo-774909.jpeg"
        ]
        url_foto = random.choice(gallery)
        
        bot.send_photo(chat_id, url_foto, caption="Look at me, papi! I'm enjoying the sun. ☀️ (Guardami, papi! Mi sto godendo il sole.)", timeout=30)
        print("✅ Foto reale inviata!")
    except Exception as e:
        print(f"❌ Errore foto: {e}")
        bot.send_message(chat_id, "I'm so sorry babe, my phone is out of battery! (Mi dispiace, il mio telefono è scarico!) 🌊")

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
    except:
        bot.send_message(chat_id, testo)

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
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

        # Controllo foto
        if any(x in txt.lower() for x in ["foto", "selfie", "pic", "photo"]):
            bot.send_message(cid, "Wait a moment... I'm taking a picture for you. 📸")
            invia_foto_luna(cid)
            return

        if cid not in memoria: memoria[cid] = []
        memoria[cid].append({"role": "user", "content": txt})
        
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid][-6:]
        )
        risp = res.choices[0].message.content
        memoria[cid].append({"role": "assistant", "content": risp})
        
        invia_vocale(cid, risp)

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=60)
