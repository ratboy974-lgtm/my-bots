import os, telebot, threading, time, requests, re
from openai import OpenAI
from flask import Flask
from telebot import types

# --- SERVER DI CONTROLLO ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna V13: New Engine 🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA LUNA: 20 anni, afro-cubana, NO TATTOO (Look approvato)
LUNA_DNA = "stunning 20yo afro-cuban woman, fresh smooth skin, no tattoos, curly hair, hazel eyes"

def genera_risposta_ai(testo):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": "Sei Luna, 20 anni, afro-cubana molto sexy. Parli italiano. Termina SEMPRE con ART: [5 english keywords]."},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        desc_foto = None
        match = re.search(r"ART[:\s\-\[\(]*(.*)", risp_raw, re.IGNORECASE | re.DOTALL)
        
        if match:
            desc_foto = match.group(1).strip().replace("[", "").replace("]", "").replace(")", "")
            risp_finale = risp_raw[:match.start()].strip()
            if not risp_finale: risp_finale = "Guardami, mivida... 🔥"
        else:
            risp_finale = risp_raw
        
        return risp_finale, desc_foto
    except:
        return "Mivida, riproviamo? ❤️", None

def invia_foto(cid, desc):
    try:
        # Pulizia totale per il nuovo motore
        clean_desc = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip().replace(" ", ",")
        # CAMBIO MOTORE: Usiamo una versione più stabile di Flux/Pollinations
        # Aggiungiamo parametri per forzare la rigenerazione
        url_finale = f"https://pollinations.ai/p/{LUNA_DNA.replace(' ', ',')},{clean_desc}?width=1024&height=1024&seed={int(time.time())}&model=flux"
        
        # Mandiamo il link a Telegram
        bot.send_photo(cid, url_finale, caption="Per te, con tutto il mio fuoco... 🔥")
    except Exception as e:
        print(f"Errore invio: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mostrati a me ora con ART:"

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
    bot.infinity_polling()
