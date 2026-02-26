import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V98: Hard Reset Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (SDXL - NO FILTER) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/sdxl"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_base = "Hyper-realistic RAW photo, 8k, masterpiece, beautiful 24yo italian girl Luna, messy dark hair, detailed skin"
    full_prompt = f"{prompt_base}, {testo_utente.lower()}"
    
    payload = {"prompt": full_prompt, "image_size": "square_hd", "num_inference_steps": 30}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    print(f"✅ MESSAGGIO RICEVUTO da {m.from_user.first_name}: {m.content_type}")
    
    # Se riceve un vocale, lo trascrive
    if m.content_type == 'voice':
        bot_luna.send_chat_action(cid, 'typing')
        try:
            f_info = bot_luna.get_file(m.voice.file_id)
            f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
            audio_io = io.BytesIO(requests.get(f_url).content)
            audio_io.name = "voice.ogg"
            text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except:
            bot_luna.send_message(cid, "Papi, non ti sento bene... 🫦")
            return
    else:
        text = m.text

    # Logica Foto / Risposta
    if any(k in text.lower() for k in ["foto", "nuda", "sexy", "hot", "vederti"]):
        bot_luna.send_message(cid, "Guarda qui... 😉")
        img = genera_foto_luna(text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "Problemi con la fotocamera!")
    else:
        try:
            res = client_or.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace."}, {"role": "user", "content": text}]
            )
            bot_luna.send_message(cid, res.choices[0].message.content)
        except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # 🚨 RESET TOTALE PER SBLOCCARE IL "NON MI SENTE"
    print("🧹 Resetting Webhooks...")
    bot_luna.remove_webhook()
    time.sleep(3)
    
    print("🚀 Luna V98 Online. Mandami un messaggio ora!")
    # Usiamo un timeout più lungo per la connessione
    bot_luna.infinity_polling(timeout=60, long_polling_timeout=30)
