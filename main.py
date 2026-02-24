import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V30: Online 🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
C_TK = os.environ.get('TOKEN_COX', "").strip() # Se è vuoto, il bot Cox non partirà
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

# --- INIZIALIZZAZIONE PROTETTA ---
bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None
bot_cox = telebot.TeleBot(C_TK) if ":" in C_TK else None

if not bot_luna:
    print("ERRORE: Token Luna mancante o errato!")

# --- PROMPT ---
LUNA_DNA = "stunning 24yo woman, long dark hair, tanned skin, hazel eyes, elegant but sensual."
PROMPT_LUNA = "Tu sei Luna, 24 anni. Sei la donna passionale dell'utente (Papi). Insegnali inglese."

# --- FUNZIONE VOCE ---
def invia_voce_pro(bot, cid, testo, voce_modello):
    try:
        response = client_oa.audio.speech.create(model="tts-1", voice=voce_modello, input=testo)
        bot.send_voice(cid, response.content)
    except Exception as e:
        print(f"Errore Voce: {e}")
        bot.send_message(cid, testo)

# --- GESTORE LUNA ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_luna(m):
    cid = m.chat.id
    u_text = m.text
    if m.content_type == 'voice':
        file_info = bot_luna.get_file(m.voice.file_id)
        file_content = requests.get(f'https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}').content
        with open("voice.ogg", "wb") as f: f.write(file_content)
        with open("voice.ogg", "rb") as f:
            u_text = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text

    res = client_or.chat.completions.create(
        model="mistralai/mistral-7b-instruct",
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": u_text}]
    )
    ans = res.choices[0].message.content
    bot.send_message(cid, ans)
    threading.Thread(target=invia_voce_pro, args=(bot_luna, cid, ans, "shimmer")).start()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    if bot_luna:
        threading.Thread(target=lambda: bot_luna.infinity_polling()).start()
    
    if bot_cox:
        # Aggiungi qui la logica di Cox se vuoi attivarlo
        print("Cox Online!")
        
    print("Sistema avviato. Luna ti aspetta.")
    while True: time.sleep(10)
