import os, telebot, threading, time, random, urllib.parse
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is ready for photos! 📸", 200

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

memoria = {}

# --- LUNA DNA FISSO ---
LUNA_DNA = "stunning 24yo afro-cuban woman, voluminous curly dark brown afro hair, hazel eyes, sun-kissed skin"

PROMPT_LUNA = (
    f"Tu sei LUNA, {LUNA_DNA}. Sei la compagna dell'utente. "
    "Scrivi SOLO la tua risposta. NON inventare dialoghi per l'utente. "
    "Insegna l'inglese in modo flirty."
)

# --- FUNZIONE FOTO (VERSIONE STABILE) ---
def invia_foto_luna(chat_id, richiesta_testo):
    try:
        bot.send_chat_action(chat_id, 'upload_photo')
        
        # Scegliamo l'azione in base alla richiesta
        if any(x in richiesta_testo.lower() for x in ["spicy", "sexy", "piccante", "lingerie"]):
            azione = "sensual pose, black lace lingerie, soft bedroom lighting"
        else:
            azione = "smiling, wearing a red bikini, tropical beach background"

        # COSTRUZIONE URL PULITO (Risolve il problema del mancato invio)
        prompt_completo = f"{LUNA_DNA}, {azione}, realistic 8k"
        prompt_pulito = urllib.parse.quote(prompt_completo) # Rende l'URL compatibile
        
        url_foto = f"https://image.pollinations.ai/prompt/{prompt_pulito}?seed={random.randint(1,99999)}&nologo=true"
        
        # Invio con timeout lungo (90 secondi)
        bot.send_photo(chat_id, url_foto, caption="I hope you like this, papi... 📸", timeout=90)
        print(f"✅ Foto inviata con successo!")
        
    except Exception as e:
        print(f"❌ Errore Invio Foto: {e}")
        bot.send_message(chat_id, "Lo siento mivida, la connessione è lenta qui a Cuba... riprova! 🌊")

def genera_risposta_ai(cid, testo_utente):
    if cid not in memoria: memoria[cid] = []
    memoria[cid].append({"role": "user", "content": testo_utente})
    if len(memoria[cid]) > 10: memoria[cid] = memoria[cid][-8:]

    res = client_or.chat.completions.create(
        model="gryphe/mythomax-l2-13b",
        messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid],
        extra_body={"stop": ["You:", "User:", "Tu:", "Uomo:"]}
    )
    risp = res.choices[0].message.content.strip()
    memoria[cid].append({"role": "assistant", "content": risp})
    return risp

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        # 1. GESTIONE TESTO
        if m.content_type == 'text':
            # Trigger Foto
            if any(x in m.text.lower() for x in ["foto", "selfie", "pic", "immagine"]):
                invia_foto_luna(cid, m.text)
                return

            risposta = genera_risposta_ai(cid, m.text)
            bot.send_message(cid, risposta)

        # 2. GESTIONE VOCALE
        elif m.content_type == 'voice':
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("t.ogg", "wb") as f: f.write(audio_raw)
            with open("t.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            
            risposta = genera_risposta_ai(cid, tr.text)
            os.remove("t.ogg")

            path_v = f"v_{cid}.mp3"
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risposta) as r:
                r.stream_to_file(path_v)
            with open(path_v, 'rb') as v: bot.send_voice(cid, v)
            os.remove(path_v)

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling()
