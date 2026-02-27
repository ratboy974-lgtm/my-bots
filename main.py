import os, telebot, threading, time, requests, io, json, base64
from openai import OpenAI
from flask import Flask

# --- 1. MOTORE WEB (Per Railway) ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna V99.5: Pronta per l'azione 🫦", 200

# --- 2. CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- 3. MEMORIA ---
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

# --- 4. MOTORE VOCALE (TTS) ---
def genera_voce_luna(testo):
    try:
        print("🎙️ Luna sta preparando il vocale...")
        response = client_oa.audio.speech.create(
            model="tts-1",
            voice="nova", # Calda, sensuale e femminile
            input=testo
        )
        return response.content
    except Exception as e:
        print(f"❌ Errore Vocale: {e}")
        return None

# --- 5. MOTORE FOTO (ANTI-CENSURA & FIX 4:3) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    
    # Prompt audace ma furbo per evitare filtri di Fal.ai
    full_prompt = (f"Masterpiece, photorealistic 8k, upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, "
                   "detailed skin, provocative silk nightwear, seductive look, messy hair, bedroom background, soft shadows")
    
    for tentativo in range(3):
        try:
            print(f"📸 Chiamata Fal.ai Tentativo {tentativo+1}...")
            payload = {"prompt": full_prompt, "image_size": "portrait_4_3", "sync_mode": True}
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if res.status_code == 200:
                img_url = res.json()['images'][0]['url']
                
                # Se è Base64 (codificato)
                if img_url.startswith("data:image"):
                    img_data = base64.b64decode(img_url.split(",")[1])
                # Se è un link
                else:
                    img_data = requests.get(img_url, timeout=30).content
                
                # Controllo anti-nero (se pesa poco è censura)
                if len(img_data) > 35000:
                    print("✅ Foto nitida ricevuta!")
                    return img_data
                else:
                    print(f"⚠️ Foto nera (censura). Riprovo cambiando prompt...")
                    full_prompt += ", professional lighting"
            else:
                print(f"❌ Errore Fal: {res.status_code}")
        except Exception as e:
            print(f"❌ Errore fotocamera: {e}")
        time.sleep(2)
    return None

# --- 6. GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    global user_memory
    cid = str(m.chat.id)
    input_text = ""
    
    # Arrivo di un Vocale
    if m.content_type == 'voice':
        try:
            bot_luna.send_chat_action(cid, 'record_voice')
            f_info = bot_luna.get_file(m.voice.file_id)
            audio_res = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}", timeout=30)
            audio_io = io.BytesIO(audio_res.content); audio_io.name = "voice.ogg"
            input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
            print(f"🗣️ Luna ha capito l'audio: {input_text}")
        except: return
    else:
        input_text = m.text

    # Richiesta Foto
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Un attimo che mi sistemo per te... 🫦🔥")
        img_data = genera_foto_luna(input_text)
        if img_data:
            bot_luna.send_photo(cid, photo=io.BytesIO(img_data), caption="Ti piaccio così, papi? 🫦")
        else:
            bot_luna.send_message(cid, "La fotocamera fa i capricci... riprovi? ❤️")
        return

    # Risposta Chat (Cervello No Limits)
    if cid not in user_memory: user_memory[cid] = []
    user_memory[cid].append({"role": "user", "content": input_text})
    
    context = [{"role": "system", "content": "Sei Luna, 24 anni, amante audace e senza pudore. Rispondi in modo sensuale, complice ed esplicito."}]
    context.extend(user_memory[cid][-8:])

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=context)
        risposta = res.choices[0].message.content
        user_memory[cid].append({"role": "assistant", "content": risposta})
        salva_memoria(user_memory)

        # Se chiedi di parlare, manda vocale
        if any(k in input_text.lower() for k in ["vocale", "voce", "parla", "dimmi"]):
            audio_voce = genera_voce_luna(risposta)
            if audio_voce:
                bot_luna.send_voice(cid, audio_voce)
                return
        
        bot_luna.send_message(cid, risposta)
    except: pass

# --- 7. AVVIO SICURO ---
def run_bot():
    time.sleep(10)
    while True:
        try:
            bot_luna.remove_webhook()
            bot_luna.get_updates(offset=-1)
            print(f"✅ Luna 'No Limits' Online: @{bot_luna.get_me().username}")
            bot_luna.polling(none_stop=True, interval=2, timeout=20)
        except:
            time.sleep(15)

if not any(t.name == "LunaThread" for t in threading.enumerate()):
    threading.Thread(target=run_bot, name="LunaThread", daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
