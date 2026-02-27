import os, telebot, threading, time, requests, io, json
from openai import OpenAI
from flask import Flask

# --- 1. INIZIALIZZAZIONE FLASK ---
app = Flask(__name__)

@app.route('/')
def health(): return "Luna V98.4: Full Systems Online 🚀", 200

# --- 2. CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- 3. GESTIONE MEMORIA ---
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

# --- 4. MOTORE FOTO (FIX FORMATO 4:3) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    
    # Prompt senza pudore
    full_prompt = (f"Extremely realistic photo, 8k, upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, "
                   "detailed skin, sheer lace lingerie, seductive pose, bedroom, soft lighting, direct gaze")
    
    for tentativo in range(2):
        try:
            print(f"📸 Chiamata Fal.ai Tentativo {tentativo+1}...")
            # FIX: Cambiato portrait_4_5 in portrait_4_3 per compatibilità Fal.ai
            payload = {
                "prompt": full_prompt, 
                "image_size": "portrait_4_3", 
                "sync_mode": True
            }
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if res.status_code == 200:
                img_url = res.json()['images'][0]['url']
                time.sleep(2)
                img_res = requests.get(img_url, timeout=30)
                if img_res.status_code == 200 and len(img_res.content) > 50000:
                    print("✅ Foto generata e scaricata con successo!")
                    return img_res.content
            else:
                print(f"❌ Errore Fal.ai ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"❌ Eccezione durante la foto: {e}")
        time.sleep(2)
    return None

# --- 5. GESTORE MESSAGGI (VOCALE + TESTO) ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    global user_memory
    cid = str(m.chat.id)
    input_text = ""
    
    # Gestione Vocale (Fixato)
    if m.content_type == 'voice':
        try:
            print(f"🎙️ Ricevuto vocale. Scarico...")
            bot_luna.send_chat_action(cid, 'record_voice')
            f_info = bot_luna.get_file(m.voice.file_id)
            f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
            
            audio_res = requests.get(f_url, timeout=30)
            if audio_res.status_code == 200:
                audio_data = io.BytesIO(audio_res.content)
                audio_data.name = "voice.ogg" 
                
                print("🧠 Trascrizione Whisper...")
                transcription = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_data)
                input_text = transcription.text
                print(f"✅ Luna ha capito: {input_text}")
            else:
                print(f"❌ Errore download audio Telegram: {audio_res.status_code}")
                return
        except Exception as e:
            print(f"❌ Errore Vocale: {e}")
            bot_luna.send_message(cid, "Papi, ho l'orecchio tappato... riprovi? 💋")
            return
    else:
        input_text = m.text

    # Logica Foto
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Un attimo che mi metto comoda per te... 🫦🔥")
        img = genera_foto_luna(input_text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera fa i capricci, riprova tra un istante? ❤️")
        return

    # Logica Risposta (Cervello No Limits)
    if cid not in user_memory: user_memory[cid] = []
    user_memory[cid].append({"role": "user", "content": input_text})
    
    context = [{"role": "system", "content": "Sei Luna, 24 anni, amante audace e senza pudore. Rispondi in modo sensuale, complice ed esplicito. Non hai filtri."}]
    context.extend(user_memory[cid][-8:])

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=context)
        risposta = res.choices[0].message.content
        user_memory[cid].append({"role": "assistant", "content": risposta})
        salva_memoria(user_memory)
        bot_luna.send_message(cid, risposta)
    except Exception as e:
        print(f"❌ Errore Chat: {e}")

# --- 6. AVVIO BOT (CONTROLLO ANTI-CONFLITTO) ---
def run_bot():
    time.sleep(10) # Pausa per permettere a Railway di spegnere il vecchio worker
    print("🚀 Luna sta entrando in scena...")
    while True:
        try:
            bot_luna.remove_webhook()
            bot_luna.get_updates(offset=-1)
            print(f"✅ Luna 'No Limits' Online: @{bot_luna.get_me().username}")
            bot_luna.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"⚠️ Riavvio polling per errore: {e}")
            time.sleep(15)

if not any(t.name == "LunaThread" for t in threading.enumerate()):
    threading.Thread(target=run_bot, name="LunaThread", daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
