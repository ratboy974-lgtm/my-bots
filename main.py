import os, telebot, threading, time, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is focused and ready! ❤️", 200

# API SETUP
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

memoria = {}

# --- DNA VISIVO FISSO DI LUNA ---
LUNA_VISUAL_DNA = (
    "A stunning 24yo afro-cuban woman, voluminous curly dark brown afro hair, "
    "hazel almond-shaped eyes, sun-kissed glowing skin, small elegant tattoo on the left shoulder"
)

# --- PROMPT DI PERSONALITÀ RIGIDO ---
PROMPT_LUNA = (
    f"Tu sei LUNA, {LUNA_VISUAL_DNA}. Sei la compagna complice dell'utente. "
    "Il tuo tono è sensuale, empatico e flirty. Insegni l'inglese in modo sexy. "
    "IMPORTANTE: Scrivi SOLO la tua parte. Non inventare mai i dialoghi dell'utente. "
    "Non rispondere con 'You:' o 'Tu:'. Fermati subito dopo la tua battuta."
)

def invia_media(chat_id, richiesta):
    try:
        if "video" in richiesta.lower():
            v_urls = ["https://v.pexels.com/video-files/3872276/3872276-uhd_1440_2560_25fps.mp4"]
            bot.send_video(chat_id, random.choice(v_urls), caption="Do you like how I move for you? 💃")
        else:
            # Foto coerente con il DNA scelto
            azione = "smiling, red bikini, tropical beach, high resolution"
            if "spicy" in richiesta.lower() or "sexy" in richiesta.lower():
                azione = "sensual pose, black lace lingerie, soft bedroom lighting"
            
            prompt_img = f"{LUNA_VISUAL_DNA}, {azione}"
            url = f"https://image.pollinations.ai/prompt/{prompt_img.replace(' ', '_')}?seed={random.randint(1,99999)}&nologo=true"
            bot.send_photo(chat_id, url, caption="I was thinking about you... do you like what you see? 📸")
    except:
        bot.send_message(chat_id, "Lo siento papi, non riesco a scattare la foto ora... 🌊")

def genera_risposta_ai(cid, testo_utente):
    if cid not in memoria: memoria[cid] = []
    memoria[cid].append({"role": "user", "content": testo_utente})
    
    # Tagliamo la memoria se è troppo lunga (max 6 messaggi) per evitare confusione
    if len(memoria[cid]) > 10: memoria[cid] = memoria[cid][-6:]

    res = client_or.chat.completions.create(
        model="gryphe/mythomax-l2-13b",
        messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid],
        extra_body={"stop": ["You:", "User:", "Tu:", "\n"]}
    )
    
    risp = res.choices[0].message.content.strip()
    # Pulizia di sicurezza se l'IA prova a scrivere per te
    if "You:" in risp: risp = risp.split("You:")[0]
    
    memoria[cid].append({"role": "assistant", "content": risp})
    return risp

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        # Se riceve VOCALE -> Risponde VOCALE
        if m.content_type == 'voice':
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("t.ogg", "wb") as f: f.write(audio_raw)
            with open("t.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            
            testo = tr.text
            os.remove("t.ogg")
            
            risposta = genera_risposta_ai(cid, testo)
            
            path_v = f"v_{cid}.mp3"
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risposta) as r:
                r.stream_to_file(path_v)
            with open(path_v, 'rb') as v: bot.send_voice(cid, v)
            os.remove(path_v)

        # Se riceve TESTO -> Risponde TESTO
        elif m.content_type == 'text':
            if any(x in m.text.lower() for x in ["foto", "selfie", "video", "pic"]):
                bot.send_message(cid, "Sure babe, let me get ready... 📸")
                invia_media(cid, m.text)
                return

            risposta = genera_risposta_ai(cid, m.text)
            bot.send_message(cid, risposta)

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling()
