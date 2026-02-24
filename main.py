import os, telebot, threading, time, requests, re, random, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è tornata se stessa... 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA ORIGINALE (Quello che funzionava)
LUNA_DNA = "stunning 24yo afro-cuban woman, curly hair, bronze skin, hazel eyes, curvy"

def genera_risposta_ai(testo_utente):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": (
                    "TU SEI LUNA, donna afro-cubana di 24 anni. Parla italiano. "
                    "Sei passionale, dolce e sensuale. L'utente è il tuo uomo. "
                    "Se vuoi mandare una foto, scrivi il messaggio e chiudi SOLO con ART: [5 keywords]."
                )},
                {"role": "user", "content": testo_utente}
            ],
            temperature=0.8
        )
        risp = res.choices[0].message.content.strip()
        
        desc_foto = None
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip()
        
        return risp, desc_foto
    except:
        return "Mivida, riproviamo? ❤️", None

def invia_voce(cid, testo):
    try:
        # Forziamo la lingua italiana femminile (it-IT) con un motore differente
        testo_f = testo[:150].replace(" ", "+")
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=it-it&client=tw-ob&q={testo_f}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code == 200:
            bot.send_voice(cid, res.content)
    except:
        pass

def invia_foto(cid, desc):
    try:
        seed = random.randint(1, 99999)
        # Usiamo Flux che è il più stabile per evitare loghi
        url = f"https://pollinations.ai/p/{LUNA_DNA.replace(' ', ',')},{desc.replace(' ', ',')}?width=1024&height=1024&nologo=true&seed={seed}&model=flux"
        bot.send_photo(cid, url, caption="Per te... 🔥")
    except:
        pass

@bot.message_handler(content_types=['voice'])
def handle_voice(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'record_audio')
    r_txt, d_foto = genera_risposta_ai("L'utente ti ha parlato. Rispondi con la tua voce.")
    bot.send_message(cid, r_txt) # Testo di backup
    invia_voce(cid, r_txt)
    if d_foto: invia_foto(cid, d_foto)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(m.text)
    
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
