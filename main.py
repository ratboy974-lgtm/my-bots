import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V92.3: Token Check Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- FUNZIONI VOCE & FOTO (BASATE SU V92) ---
def genera_vocale_luna(testo):
    try:
        clean_text = re.sub(r'[^\w\s,.!?]', '', testo)
        response = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=clean_text[:400])
        return response.content
    except: return None

def trascrivi_vocale(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
        audio_res = requests.get(f_url)
        if audio_res.status_code == 200:
            audio_io = io.BytesIO(audio_res.content)
            audio_io.name = "input.ogg"
            return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    except: return None

def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    is_action = any(verb in prompt_puro for verb in ["corre", "corsa", "cammina", "spiaggia", "mare"])
    vista = "Full body shot, wide angle" if is_action else "Upper body shot"
    full_prompt = f"{vista} of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, natural lighting, masterpiece, 8k"
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "seed": random.randint(1, 999999)}, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    is_voice = (m.content_type == 'voice')
    input_text = trascrivi_vocale(m.voice.file_id) if is_voice else m.text
    if not input_text: return

    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Mi preparo e arrivo... 😉")
        img = genera_foto_luna(input_text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "La fotocamera non va, riprova!")
        return

    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace. Rispondi breve (max 20 parole)."},
                      {"role": "user", "content": input_text}]
        )
        risposta = res.choices[0].message.content
        if is_voice:
            audio = genera_vocale_luna(risposta)
            if audio: bot_luna.send_voice(cid, audio)
            else: bot_luna.send_message(cid, risposta)
        else: bot_luna.send_message(cid, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # 🚨 FIX 401/409: Reset totale
    print("🧹 Pulizia sessioni e verifica Token...")
    try:
        bot_luna.remove_webhook(drop_pending_updates=True)
        time.sleep(2)
        me = bot_luna.get_me()
        print(f"✅ Bot collegato correttamente come: @{me.username}")
    except Exception as e:
        print(f"❌ ERRORE CRITICO: Token non valido o problema di connessione: {e}")

    bot_luna.infinity_polling(timeout=20, long_polling_timeout=10)
