import os, telebot, threading, time, requests, io, json
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V96.5: All Systems Go 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MEMORIA JSON ---
MEM_FILE = "memoria_luna.json"

def carica_memoria():
    if os.path.exists(MEM_FILE):
        try:
            with open(MEM_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except: return {}
    return {}

def salva_memoria(mem):
    try:
        with open(MEM_FILE, 'w') as f:
            json.dump(mem, f)
    except: pass

user_memory = carica_memoria()

# --- MOTORE FOTO (ANTI-NERO) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"RAW photo, upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, high quality, 8k"
    
    for tentativo in range(2):
        try:
            payload = {"prompt": full_prompt, "image_size": "portrait_4_5", "num_inference_steps": 4, "sync_mode": True}
            res = requests.post(url, headers=headers, json=payload, timeout=45)
            if res.status_code == 200:
                img_url = res.json()['images'][0]['url']
                time.sleep(2)
                img_res = requests.get(img_url, timeout=30)
                if img_res.status_code == 200 and len(img_res.content) > 50000:
                    return img_res.content
            print(f"⚠️ Tentativo {tentativo+1} fallito (Size: {len(res.content) if res else 0})")
        except: pass
        time.sleep(2)
    return None

# --- GESTORE MESSAGGI (VOCALE + TESTO) ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    global user_memory
    cid = str(m.chat.id)
    input_text = ""
    
    # Gestione Vocale
    if m.content_type == 'voice':
        try:
            bot_luna.send_chat_action(cid, 'record_voice')
            f_info = bot_luna.get_file(m.voice.file_id)
            audio_res = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}", timeout=20)
            if audio_res.status_code == 200:
                audio_io = io.BytesIO(audio_res.content)
                audio_io.name = "audio.ogg"
                input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
            else: raise Exception("Download audio fallito")
        except Exception as e:
            bot_luna.send_message(cid, "Non ti ho sentito bene, papi... riprovi? 💋")
            return
    else:
        input_text = m.text

    # Logica Foto
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Un attimo che mi sistemo... 🫦")
        img = genera_foto_luna(input_text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera fa i capricci, riprova tra un istante? ❤️")
        return

    # Logica Risposta
    if cid not in user_memory: user_memory[cid] = []
    user_memory[cid].append({"role": "user", "content": input_text})
    context = [{"role": "system", "content": "Sei Luna, 24 anni, audace. Ricorda tutto dell'utente."}]
    context.extend(user_memory[cid][-8:])

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=context)
        risposta = res.choices[0].message.content
        user_memory[cid].append({"role": "assistant", "content": risposta})
        salva_memoria(user_memory)
        bot_luna.send_message(cid, risposta)
    except: pass

# --- AVVIO POLLING ---
def start_polling():
    print("⏳ Pulizia sessioni e avvio Bot...")
    try:
        bot_luna.remove_webhook()
        time.sleep(2)
        print(f"✅ Luna Online: @{bot_luna.get_me().username}")
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception as e:
        print(f"❌ Errore: {e}")
        time.sleep(5)

threading.Thread(target=start_polling, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
