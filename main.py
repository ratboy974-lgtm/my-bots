import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna: Equilibrium Restored 🔥", 200

# --- CONFIG ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA ORIGINALE (L'equilibrio che cercavi)
LUNA_DNA = "stunning 24yo woman, long dark hair, tanned skin, hazel eyes, elegant but sensual, photorealistic"

def genera_risposta_ai(testo_utente):
    try:
        # Torniamo al modello che non scambiava i ruoli
        res = client_or.chat.completions.create(
            model="mistralai/mistral-7b-instruct", 
            messages=[
                {"role": "system", "content": (
                    "Tu sei Luna, una donna di 24 anni, passionale e intelligente. L'utente è il tuo uomo. "
                    "Parla solo italiano. Insegnali un po' di inglese tra una frase e l'altra in modo sexy. "
                    "Se vuoi mandare una foto, termina il messaggio SOLO con ART: [english description]."
                )},
                {"role": "user", "content": testo_utente}
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
    except:
        return "Mivida, riproviamo? ❤️", None

def invia_vocale(cid, testo):
    try:
        # Motore vocale femminile forzato
        testo_url = re.sub(r'[^\w\s]', '', testo)[:150].replace(" ", "%20")
        url = f"https://api.voicerss.org/?key=3bc20d3674b54e389e1795c692518172&hl=it-it&v=Bria&src={testo_url}"
        
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            bot.send_voice(cid, r.content)
    except:
        pass

def invia_foto(cid, desc):
    try:
        seed = random.randint(1, 99999)
        url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', ',')},{desc.replace(' ', ',')}?width=1024&height=1024&nologo=true&seed={seed}"
        bot.send_photo(cid, url, caption="Per i tuoi occhi... 🔥")
    except:
        pass

# --- HANDLERS ---

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'record_audio')
    r_txt, d_foto = genera_risposta_ai("Papi ti ha mandato un vocale. Rispondi con la tua voce.")
    bot.send_message(cid, r_txt)
    threading.Thread(target=invia_vocale, args=(cid, r_txt)).start()
    if d_foto: invia_foto(cid, d_foto)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(m.text)
    
    # Messaggio di testo senza tasti che disturbano
    bot.send_message(cid, r_txt, reply_markup=telebot.types.ReplyKeyboardRemove())
    
    # Vocale femminile in background
    threading.Thread(target=invia_vocale, args=(cid, r_txt)).start()
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
