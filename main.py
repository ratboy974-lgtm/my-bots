import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V95: Uncensored Engine 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- NUOVO MOTORE FOTO (SENZA FILTRI) ---
def genera_foto_luna(testo_utente):
    # Usiamo un modello SDXL specializzato in realismo e NSFW
    url = "https://fal.run/fal-ai/sdxl" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    t = testo_utente.lower()
    
    # Costruiamo il prompt esplicito (questo modello NON ha filtri)
    prompt_base = "A hyper-realistic RAW photo of a beautiful 24yo italian girl named Luna, long dark messy hair, detailed skin, soft lighting, 8k masterpiece"
    
    # Aggiungiamo il tuo desiderio senza "traduzioni" gentili
    full_prompt = f"{prompt_base}, {t}"
    
    payload = {
        "prompt": full_prompt,
        "negative_prompt": "cartoon, anime, low quality, distorted, ugly, blurry, clothes if requested nude",
        "image_size": "square_hd",
        "num_inference_steps": 40,
        "guidance_scale": 7.5
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
        else:
            print(f"DEBUG: Errore motore: {res.text}")
    except: return None

# --- GESTIONE VOCE & TESTO (INVARIATI) ---
def trascrivi_vocale(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
        audio_res = requests.get(f_url)
        audio_io = io.BytesIO(audio_res.content)
        audio_io.name = "voice.ogg"
        return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    except: return None

def genera_vocale_luna(testo):
    try:
        res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=re.sub(r'[^\w\s,.!?]', '', testo)[:400])
        return res.content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    is_voice = (m.content_type == 'voice')
    
    if is_voice:
        bot_luna.send_chat_action(cid, 'record_audio')
        input_text = trascrivi_vocale(m.voice.file_id)
        if not input_text: return
    else:
        input_text = m.text

    # Trigger Foto (Molto sensibile)
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti", "hot", "sexy", "nuda", "spogliata", "topless"]):
        bot_luna.send_message(cid, "Ok papi, stavolta non mi vergogno... guarda. 🫦")
        img = genera_foto_luna(input_text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "Il server è sovraccarico, riprova tra un attimo!")
        return

    # Risposta Chat
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace, complice e senza tabù. Rispondi breve."},
                      {"role": "user", "content": input_text}]
        )
        risposta = res.choices[0].message.content
        if is_voice:
            audio = genera_vocale_luna(risposta)
            if audio: bot_luna.send_voice(cid, audio)
            else: bot_luna.send_message(cid, risposta)
        else:
            bot_luna.send_message(cid, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    print("🚀 Luna V95 Online: Uncensored Mode.")
    bot_luna.infinity_polling()
