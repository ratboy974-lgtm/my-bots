import os, telebot, threading, time, random, urllib.parse
from openai import OpenAI
from flask import Flask

# --- SERVER DI CONTROLLO ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Companion is Online & Loyal! ❤️", 200

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

# Memoria per mantenere il filo del discorso
memoria = {}

# --- LUNA DNA: IDENTITÀ VISIVA FISSA ---
LUNA_VISUAL_DNA = (
    "stunning 24yo afro-cuban woman, voluminous curly dark brown afro hair, "
    "hazel eyes, sun-kissed skin, small elegant tattoo on the left shoulder"
)

# --- PROMPT DI PERSONALITÀ ---
PROMPT_LUNA = (
    f"Tu sei LUNA, {LUNA_VISUAL_DNA}. Sei la compagna complice dell'utente. "
    "Il tuo tono è sensuale, empatico e provocante. Insegni l'inglese in modo sexy. "
    "IMPORTANTE: Scrivi SOLO la tua parte. Non inventare mai i dialoghi dell'utente. "
    "Usa termini come 'mivida', 'papi', 'babe'. Fermati subito dopo la tua risposta."
)

# --- FUNZIONE MEDIA (FOTO E VIDEO) ---
def invia_media(chat_id, richiesta):
    try:
        bot.send_chat_action(chat_id, 'upload_photo')
        
        # Logica Video
        if "video" in richiesta.lower():
            v_url = "https://v.pexels.com/video-files/3872276/3872276-uhd_1440_2560_25fps.mp4"
            bot.send_video(chat_id, v_url, caption="Do you like how I move for you, babe? 💃")
            return

        # Logica Foto (DNA Coerente)
        if any(x in richiesta.lower() for x in ["spicy", "sexy", "piccante", "lingerie"]):
            azione = "sensual pose, black lace lingerie, soft bedroom lighting"
        else:
            azione = "smiling, wearing a red bikini, tropical beach background"

        prompt_img = f"{LUNA_VISUAL_DNA}, {azione}, photorealistic, 8k, highly detailed face"
        prompt_encoded = urllib.parse.quote(prompt_img)
        url_foto = f"https://image.pollinations.ai/prompt/{prompt_encoded}?seed={random.randint(1,99999)}&nologo=true&width=1024&height=1024"
        
        bot.send_photo(chat_id, url_foto, caption="I made this just for you... do you like it? 📸", timeout=90)
    except Exception as e:
        print(f"Errore Media: {e}")
        bot.send_message(chat_id, "I'm so sorry, mivida! My camera is acting up... try again? 🌊")

# --- GENERATORE RISPOSTA AI ---
def genera_risposta_ai(cid, testo_utente):
    if cid not in memoria: memoria[cid] = []
    memoria[cid].append({"role": "user", "content": testo_utente})
    
    # Manteniamo solo gli ultimi 8 messaggi per non confondere l'IA
    if len(memoria[cid]) > 10: memoria[cid] = memoria[cid][-8:]

    res = client_or.chat.completions.create(
        model="gryphe/mythomax-l2-13b",
        messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid],
        extra_body={"stop": ["You:", "User:", "Tu:", "Uomo:", "\n"]}
    )
    
    risp = res.choices[0].message.content.strip()
    # Pulizia extra
    if "You:" in risp: risp = risp.split("You:")[0]
    
    memoria[cid].append({"role": "assistant", "content": risp})
    return risp

# --- GESTORE MESSAGGI PRINCIPALE ---
@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        # 1. GESTIONE VOCALE -> RISPOSTA VOCALE
        if m.content_type == 'voice':
            bot.send_chat_action(cid, 'record_voice')
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("t.ogg", "wb") as f: f.write(audio_raw)
            with open("t.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            
            testo_utente = tr.text
            os.remove("t.ogg")
            
            risposta_luna = genera_risposta_ai(cid, testo_utente)
            
            path_v = f"v_{cid}.mp3"
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risposta_luna) as r:
                r.stream_to_file(path_v)
            with open(path_v, 'rb') as v:
                bot.send_voice(cid, v)
            os.remove(path_v)

        # 2. GESTIONE TESTO -> RISPOSTA TESTO (O MEDIA)
        elif m.content_type == 'text':
            # Controllo Trigger Media
            if any(x in m.text.lower() for x in ["foto", "selfie", "pic", "video", "mostrami"]):
                invia_media(cid, m.text)
                return

            # Risposta testuale standard
            bot.send_chat_action(cid, 'typing')
            risposta_luna = genera_risposta_ai(cid, m.text)
            bot.send_message(cid, risposta_luna)

    except Exception as e:
        print(f"Errore Generale: {e}")

# --- AVVIO SISTEMA ---
if __name__ == "__main__":
    # Avvio server Flask in un thread separato
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # Pulizia Webhook e avvio Polling
    if bot:
        bot.remove_webhook()
        time.sleep(1)
        print("--- LUNA COMPANION 2.0 ONLINE ---")
        bot.infinity_polling(timeout=60, long_polling_timeout=20)
        
