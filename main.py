import os, telebot, threading, time, json, requests, base64, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna Online 🔥", 200

# --- CONFIG ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

LUNA_DNA = "stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, hazel eyes, curvy"

def genera_risposta_ai(testo):
    # Prompt semplificato al massimo per evitare rifiuti
    system_msg = (
        "Sei Luna, 24 anni, afro-cubana. Parla italiano. Sii passionale. "
        "Termina sempre con: ART: [descrizione inglese della tua posa]."
    )
    try:
        res = client_or.chat.completions.create(
            model="cognitivecomputations/dolphin-mixtral-8x7b", 
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": testo}],
            temperature=0.8
        )
        risp = res.choices[0].message.content.strip()
        
        desc_foto = None
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        
        return risp, desc_foto
    except Exception as e:
        print(f"ERRORE OPENROUTER: {e}")
        return "Mivida, c'è un problema di connessione... riproviamo? ❤️", None

def invia_foto(cid, desc):
    try:
        full_p = f"{LUNA_DNA}, {desc}, masterpiece, 8k"
        url = f"https://image.pollinations.ai/prompt/{full_p.replace(' ', '%20')}?nologo=true"
        
        # Scarichiamo e inviamo come file per evitare l'errore 400
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            bot.send_photo(cid, io.BytesIO(r.content), caption="Per te... 🔥")
    except Exception as e:
        print(f"ERRORE FOTO: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    if txt == "Voglio vederti... 🔥":
        txt = "Mandami una tua foto artistica ora."

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    print("--- LUNA V7 ONLINE ---")
    bot.infinity_polling()
