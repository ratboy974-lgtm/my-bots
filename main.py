import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V15 Online 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# Identikit pulito per il nuovo motore
LUNA_DNA = "stunning 20yo afro-cuban woman, smooth bronze skin, no tattoos, curly voluminous hair, hazel eyes, wearing summer dress"

def genera_risposta_ai(testo):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": "Sei Luna, 20 anni. Parla italiano. Se papi vuole vederti, scrivi un messaggio e termina SEMPRE con ART: [english description]."},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        desc_foto = None
        if "ART:" in risp_raw.upper():
            parti = re.split(r"ART:", risp_raw, flags=re.IGNORECASE)
            risp_finale = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        else:
            risp_finale = risp_raw
            
        return risp_finale, desc_foto
    except:
        return "Mivida, riproviamo? ❤️", None

def invia_foto(cid, desc):
    try:
        # Pulizia prompt
        p_clean = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip().replace(" ", ",")
        
        # --- CAMBIO MOTORE: Usiamo Prodia via Pollinations (più permissivo) ---
        # Modello 'deliberate' è perfetto per foto realistiche senza logo
        url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', ',')},{p_clean}?model=prodigy&width=1024&height=1024&nologo=true&seed={random.randint(1, 99999)}"
        
        bot.send_photo(cid, url, caption="Guardami, mivida... 🔥")
    except Exception as e:
        print(f"Errore: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    if txt == "Voglio vederti... 🔥":
        txt = "Luna, mostrati ora usando ART:"

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    
    if not r_txt: r_txt = "Per te... ❤️"
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
