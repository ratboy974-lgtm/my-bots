import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V14 Online 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA ultra-semplice per evitare filtri SafeSearch (causa del logo)
LUNA_DNA = "20yo afro-cuban woman, smooth skin, no tattoos, curly hair, hazel eyes, beautiful"

def genera_risposta_ai(testo):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": "Sei Luna, 20 anni. Parla italiano. Se vuoi mandare una foto, scrivi un breve messaggio e poi scrivi esattamente: ART: [english description]. Non aggiungere altro dopo."},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        desc_foto = None
        # Taglio preciso: tutto dopo ART: diventa la foto
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
        # Pulizia totale della descrizione
        p_clean = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip().replace(" ", ",")
        seed = random.randint(1, 999999)
        # URL semplificato per Flux (meno probabilità di vedere il logo)
        url = f"https://pollinations.ai/p/{LUNA_DNA.replace(' ', ',')},{p_clean}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
        
        bot.send_photo(cid, url, caption="Ecco come sono ora per te... 🔥")
    except Exception as e:
        print(f"Errore: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    if txt == "Voglio vederti... 🔥":
        txt = "Luna, mandami una tua foto ora usando ART:"

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    
    # Se il testo è rimasto vuoto dopo il taglio, mettiamo un fallback
    if not r_txt: r_txt = "Per i tuoi occhi... ❤️"
    
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
