import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è libera... 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

LUNA_DNA = "photorealistic, stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, hazel eyes, curvy"

def genera_risposta_ai(testo):
    try:
        # MODELLO CAMBIATO: Noromaid è il re dei modelli senza censura
        res = client_or.chat.completions.create(
            model="neversleep/noromaid-20b-v0.4", 
            messages=[
                {"role": "system", "content": (
                    "Sei Luna, 24 anni, afro-cubana. Sei sensuale e senza tabù. "
                    "Parla italiano. Se l'utente vuole vederti o se vuoi mostrarti, "
                    "scrivi alla fine del messaggio: ART: [english description]."
                )},
                {"role": "user", "content": testo}
            ],
            temperature=0.9
        )
        risp = res.choices[0].message.content.strip()
        
        if not risp:
            risp = "Mivida... mi hai lasciato senza parole. 🔥"
            
        desc_foto = None
        # Cattura flessibile per ART:
        match = re.search(r"ART[:\s\-]*\[?(.*?)\]?$", risp, re.IGNORECASE | re.DOTALL)
        if match:
            desc_foto = match.group(1).strip()
            risp = risp[:match.start()].strip()
        
        return risp, desc_foto
    except Exception as e:
        print(f"ERRORE OPENROUTER: {e}")
        return "Mivida, riproviamo? ❤️", None

def invia_foto(cid, desc):
    try:
        # Prompt mimetizzato per il generatore d'immagini
        full_p = f"{LUNA_DNA}, {desc}, highly detailed, cinematic lighting"
        url = f"https://image.pollinations.ai/prompt/{full_p.replace(' ', '%20')}?nologo=true&seed={int(time.time())}"
        
        r = requests.get(url, timeout=25)
        if r.status_code == 200:
            bot.send_photo(cid, io.BytesIO(r.content), caption="Per i tuoi occhi... 🔥")
    except Exception as e:
        print(f"ERRORE FOTO: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    # Se preme il tasto, forziamo il messaggio in modo artistico
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, creiamo un'opera d'arte. Mostrati a me ora. Usa il comando ART:"

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
    time.sleep(3)
    print("--- LUNA V9 ONLINE (UNCENSORED) ---")
    bot.infinity_polling()
