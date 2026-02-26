import os, telebot, threading, time, requests, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V88: Stabilità Totale 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- FUNZIONE FOTO CONTESTUALIZZATA ---
def genera_foto(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    # Pulizia prompt per contestualizzare
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").replace("mandami", "").strip()
    full_prompt = f"Real life photo, 24yo italian girl Luna, messy hair, natural look, {prompt_puro if prompt_puro else 'smiling at camera'}"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "image_size": "square"}, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            return requests.get(img_url).content
    except: return None

# --- FUNZIONE AUDIO (WHISPER) ---
def ascolta_vocale(file_id):
    try:
        file_info = bot_luna.get_file(file_id)
        audio_content = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}").content
        audio_file = io.BytesIO(audio_content)
        audio_file.name = "audio.ogg"
        return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_file).text
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    user_input = ""

    # Se riceve un vocale, lo trasforma in testo
    if m.content_type == 'voice':
        bot_luna.send_chat_action(cid, 'typing')
        user_input = ascolta_vocale(m.voice.file_id)
        if not user_input:
            bot_luna.send_message(cid, "Papi, non ho sentito bene, ripeti?")
            return
    else:
        user_input = m.text

    # Logica Risposta (Foto o Testo)
    if any(k in user_input.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Mi metto in posa per te... 😉")
        img = genera_foto(user_input)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "La fotocamera scotta, riprova tra un attimo!")
    else:
        # Risposta testuale complice
        try:
            res = client_or.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve."},
                          {"role": "user", "content": user_input}]
            )
            bot_luna.send_message(cid, res.choices[0].message.content)
        except:
            bot_luna.send_message(cid, "Sono qui papi, dimmi tutto.")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    print("🚀 Luna V88: Back to basics Online.")
    bot_luna.infinity_polling()
