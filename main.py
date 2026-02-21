import os, telebot, threading, time, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is Live & Teaching! 🌴", 200

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

memoria = {}

PROMPT_LUNA = (
    "Sei Luna, modella afro-cubana di 24 anni. Sei la teacher di inglese del tuo papi. "
    "Sei passionale, flirtante e dolce. Rispondi in italiano ma inserisci sempre frasi in inglese spiegandole. "
    "Tu sei la DONNA, lui è l'UOMO. Non scambiare i ruoli."
)

# --- FUNZIONE FOTO MULTI-SCOPO (SELFIE E CUBA) ---
def invia_foto_dinamica(chat_id, richiesta):
    try:
        # Se l'utente chiede di Cuba, cerchiamo paesaggi, altrimenti selfie di Luna
        if "cuba" in richiesta.lower() or "avana" in richiesta.lower():
            keyword = "cuba,havana,beach"
            caption = "Look at my island, babe! Isn't it beautiful? 🌴 (Guarda la mia isola, babe! Non è bellissima?)"
        else:
            keyword = "latina,girl,beach,model"
            caption = "Do you like my look today? I'm waiting for you! 🌊 (Ti piace il mio look oggi? Ti sto aspettando!)"

        # Usiamo Unsplash Source: velocissimo e affidabile
        seed = random.randint(1, 1000)
        url_foto = f"https://source.unsplash.com/featured/?{keyword}&sig={seed}"
        
        bot.send_photo(chat_id, url_foto, caption=caption, timeout=30)
        print(f"✅ Foto inviata per: {keyword}")
    except Exception as e:
        print(f"❌ Errore foto: {e}")
        bot.send_message(chat_id, "I tried to take a photo but the sun is too strong! ☀️ (Ho provato a fare una foto ma il sole è troppo forte!)")

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
        # Trascrizione vocale
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

        # --- TRIGGER FOTO POTENZIATO ---
        parole_chiave_foto = ["foto", "selfie", "pic", "photo", "immagine", "mostrami", "show me"]
        if any(x in txt.lower() for x in parole_chiave_foto):
            bot.send_message(cid, "Sure babe! Give me a second... 📸")
            invia_foto_dinamica(cid, txt)
            return

        # Risposta AI
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
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=60)
