import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta... 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

LUNA_DNA = "photorealistic, stunning 20yo afro-cuban woman, fresh smooth skin, no tattoos, curly hair, hazel eyes"

def genera_risposta_ai(testo):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": "Sei Luna, 20 anni, afro-cubana senza tatuaggi. Parla italiano. Se chiedono foto, scrivi alla fine: ART: [english description]."},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp = res.choices[0].message.content.strip()
        desc_foto = None
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        return risp, desc_foto
    except:
        return "Mivida, riproviamo? ❤️", None

def invia_foto(cid, desc):
    # Pulizia prompt
    clean_desc = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip()
    # Usiamo un formato URL ultra-veloce
    url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', ',')},{clean_desc.replace(' ', ',')}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Tentativo di invio (fino a 2 volte)
    for tentativo in range(2):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                img_data = io.BytesIO(response.content)
                img_data.name = 'luna.jpg'
                bot.send_photo(cid, img_data, caption="Per te, papi... 🔥")
                return # Successo, esci dalla funzione
        except:
            time.sleep(2) # Aspetta un attimo prima di riprovare
    
    bot.send_message(cid, "Mivida, la foto ci sta mettendo troppo... riprova tra un secondo? ❤️")

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
        # Usiamo il thread per non bloccare il bot
        t = threading.Thread(target=invia_foto, args=(cid, d_foto))
        t.start()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
