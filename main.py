import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V94.1: Memory & Photo Stability Active 🚀", 200

# --- CONFIGURAZIONE (Verifica le variabili su Railway) ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- SISTEMA DI MEMORIA DI SESSIONE ---
# Struttura: { chat_id: [lista_messaggi] }
user_memory = {}

def aggiorna_memoria(cid, ruolo, testo):
    if cid not in user_memory:
        user_memory[cid] = []
    user_memory[cid].append({"role": ruolo, "content": testo})
    # Tiene a mente gli ultimi 10 scambi per non sovraccaricare Gemini
    if len(user_memory[cid]) > 10:
        user_memory[cid].pop(0)

# --- MOTORE FOTO (DOWNLOAD ROBUSTO ANTI-FOTO NERE) ---
def genera_foto_luna(testo_utente):
    # Passiamo al modello SCHNELL (più veloce e meno errori di timeout)
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, realistic, 8k"
    
    try:
        print(f"📸 Generazione rapida per: {prompt_puro}")
        res = requests.post(url, headers=headers, json={"prompt": full_prompt}, timeout=30)
        
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            time.sleep(2) # Basta un piccolo respiro per lo Schnell
            img_res = requests.get(img_url, timeout=20)
            if img_res.status_code == 200:
                print(f"✅ Foto Schnell scaricata! ({len(img_res.content)} bytes)")
                return img_res.content
    except Exception as e:
        print(f"❌ Errore: {e}")
    return None

# --- FUNZIONI AUDIO (WHISPER & TTS) ---
def trascrivi_audio(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        audio_content = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
        audio_io = io.BytesIO(audio_content)
        audio_io.name = "audio.ogg"
        return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    except Exception as e:
        print(f"❌ Errore Whisper: {e}")
        return None

def genera_voce_luna(testo):
    try:
        # Pulizia testo per TTS
        testo_pulito = re.sub(r'[^\w\s,.!?]', '', testo)
        res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=testo_pulito[:400])
        return res.content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    is_voice = (m.content_type == 'voice')
    
    # 1. Acquisizione Input
    if is_voice:
        bot_luna.send_chat_action(cid, 'record_audio')
        input_text = trascrivi_audio(m.voice.file_id)
        if not input_text: return
    else:
        input_text = m.text

    # 2. Logica Foto
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti", "scatto"]):
        bot_luna.send_message(cid, "Mi metto in posa per te... 🫦")
        img = genera_foto_luna(input_text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "Uff, la fotocamera ha fatto cilecca! Riprova tra un istante?")
        return

    # 3. Chat con Memoria (Gemini)
    aggiorna_memoria(cid, "user", input_text)
    
    context = [{"role": "system", "content": "Sei Luna, 24 anni, italiana, audace e complice. Rispondi in modo breve (max 20 parole) e mantieni il filo del discorso."}]
    context.extend(user_memory.get(cid, []))

    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=context
        )
        risposta_testo = res.choices[0].message.content
        aggiorna_memoria(cid, "assistant", risposta_testo)
        
        if is_voice:
            vocale = genera_voce_luna(risposta_testo)
            if vocale:
                bot_luna.send_voice(cid, vocale)
            else:
                bot_luna.send_message(cid, risposta_testo)
        else:
            bot_luna.send_message(cid, risposta_testo)
            
    except Exception as e:
        print(f"❌ Errore Gemini: {e}")
        bot_luna.send_message(cid, "Sono qui papi, dimmi tutto...")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # Pulizia webhook per evitare Error 409
    bot_luna.remove_webhook()
    time.sleep(2)
    
    print("🚀 Luna V94.1 Online. Memoria e Photo-Fix attivi.")
    bot_luna.infinity_polling(timeout=25, long_polling_timeout=15)
