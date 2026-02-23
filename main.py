import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna Online 🔥", 200

# --- CONFIG ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

# LOG DI CONTROLLO (Vedi questo nei log di Railway)
print(f"DEBUG: Chiave API trovata? {'SI' if OR_K else 'NO'}")
if OR_K: print(f"DEBUG: Inizio chiave: {OR_K[:8]}...")

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

LUNA_DNA = "stunning 24yo afro-cuban woman, curly hair, bronze skin"

def genera_risposta_ai(testo):
    try:
        # Usiamo Mistral: è il più stabile per i test
        res = client_or.chat.completions.create(
            model="mistralai/mistral-7b-instruct", 
            messages=[
                {"role": "system", "content": "Sei Luna. Parla italiano. Se chiedono foto, scrivi ART: [descrizione inglese]."},
                {"role": "user", "content": testo}
            ],
            temperature=0.7
        )
        risp = res.choices[0].message.content.strip()
        desc_foto = None
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip()
        return risp, desc_foto
    except Exception as e:
        print(f"ERRORE OPENROUTER: {e}")
        return None, None

def invia_foto(cid, desc):
    try:
        url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', '%20')}%20{desc.replace(' ', '%20')}?nologo=true"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            bot.send_photo(cid, io.BytesIO(r.content), caption="Per te... 🔥")
    except Exception as e:
        print(f"ERRORE FOTO: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'typing')
    
    testo_utente = m.text
    if testo_utente == "Voglio vederti... 🔥":
        testo_utente = "Mandami una tua foto artistica."

    r_txt, d_foto = genera_risposta_ai(testo_utente)
    
    if r_txt is None:
        bot.send_message(cid, "Mivida, c'è un errore tecnico con le API. Controlla i log di Railway! ⚠️")
        return

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
    bot.infinity_polling()
