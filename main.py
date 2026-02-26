import os, telebot, threading, time, requests, io, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V86: Voice & Context Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- MOTORE FOTO (CONTESTUALIZZATO) ---
def genera_foto_luna(descrizione_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    # Puliamo il prompt: togliamo parole inutili come "mandami una foto"
    clean_prompt = descrizione_utente.lower().replace("mandami", "").replace("una foto", "").replace("luna", "").strip()
    full_prompt = f"Extreme realism, high quality photo of Luna, a beautiful 24yo italian girl, natural skin, messy hair, {clean_prompt}"
    
    payload = {"prompt": full_prompt, "image_size": "square", "sync_mode": True}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            img_data = requests.get(img_url).content
            return img_data
    except Exception as e:
        print(f"Errore FAL: {e}")
    return None

# --- GESTIONE AUDIO (WHISPER & TTS) ---
def gestisci_audio(file_id):
    try:
        # Scarica l'audio
        f_info = bot_luna.get_file(file_id)
        f_data = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
        
        # Trascrizione con Whisper
        audio_file = io.BytesIO(f_data)
        audio_file.name = "audio.ogg"
        transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_file).text
        return transcript
    except: return None

def genera_vocale(testo):
    try:
        # Pulizia testo per TTS (rimuove emoji o scritte strane)
        clean_text = re.sub(r'[^\w\s,.!?]', '', testo)[:300]
        res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=clean_text)
        return res.content
    except: return None

# --- LOGICA LLM ---
def chiedi_luna(testo):
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni. Rispondi in modo audace e complice, massimo 25 parole."},
                      {"role": "user", "content": testo}]
        )
        return res.choices[0].message.content
    except: return "Sono qui papi!"

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_all(m):
        cid = m.chat.id
        
        # 1. GESTIONE VOCALI
        if m.content_type == 'voice':
            testo_trascritto = gestisci_audio(m.voice.file_id)
            if testo_trascritto:
                risposta = chiedi_luna(testo_trascritto)
                audio_risposta = genera_vocale(risposta)
                if audio_risposta:
                    bot_luna.send_voice(cid, audio_risposta)
                else:
                    bot_luna.send_message(cid, risposta)
            return

        # 2. GESTIONE TESTO
        text = m.text.lower()
        
        # Foto contestualizzata
        if any(k in text for k in ["foto", "selfie", "vederti"]):
            bot_luna.send_message(cid, "Mi preparo un attimo... 😉")
            img = genera_foto_luna(m.text)
            if img:
                bot_luna.send_photo(cid, img)
            else:
                bot_luna.send_message(cid, "Problemi con la fotocamera, riprova!")
        
        # Messaggio normale
        else:
            bot_luna.send_message(cid, chiedi_luna(m.text))

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        print("🚀 Luna V86 Online: Voce e Contesto pronti.")
        bot_luna.infinity_polling(timeout=20)
