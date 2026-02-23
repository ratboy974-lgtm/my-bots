import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

# --- SERVER DI CONTROLLO ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta, mivida... 🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA LUNA: 20 anni, afro-cubana, pelle liscia, NO TATTOO
LUNA_DNA = "photorealistic, stunning 20yo afro-cuban woman, fresh smooth skin, no tattoos, clear skin, voluminous curly hair, hazel eyes, athletic but curvy"

# --- LOGICA AI CON TAGLIO AGGRESSIVO ---
def genera_risposta_ai(testo):
    try:
        # Utilizzo di MythoMax per bypassare i filtri morali
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": (
                    "Sei Luna, 20 anni, afro-cubana senza tatuaggi. Parla italiano. "
                    "Sei la compagna passionale dell'utente. "
                    "Se l'utente vuole una foto, scrivi un messaggio breve in italiano e "
                    "termina SEMPRE con ART: [seguito da 5 parole chiave in inglese]. "
                    "Tutto ciò che scrivi dopo ART: deve essere solo in inglese."
                )},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        if not risp_raw:
            return "Mivida... mi sono incantata a guardarti. ❤️", None
            
        desc_foto = None
        # REGEX AGGRESSIVA: Cerca 'ART:' e cattura TUTTO ciò che segue, ignorando maiuscole/minuscole
        match = re.search(r"ART[:\s\-\[\(]*(.*)", risp_raw, re.IGNORECASE | re.DOTALL)
        
        if match:
            # Estraiamo la descrizione (pulendola da eventuali parentesi residue)
            desc_foto = match.group(1).strip().replace("[", "").replace("]", "").replace(")", "")
            # Il testo che inviamo all'utente è solo quello PRIMA di ART:
            risp_finale = risp_raw[:match.start()].strip()
            
            # Se dopo il taglio il testo è vuoto, mettiamo un fallback
            if not risp_finale:
                risp_finale = "Ecco quello che desideravi, papi... 🔥"
        else:
            risp_finale = risp_raw
        
        return risp_finale, desc_foto
    except Exception as e:
        print(f"ERRORE AI: {e}")
        return "Mivida, riproviamo tra un istante? ❤️", None

# --- FUNZIONE INVIO FOTO (CON DOPPIO TENTATIVO) ---
def invia_foto(cid, desc):
    try:
        # Pulizia prompt per il generatore
        clean_desc = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip()
        prompt_finale = f"{LUNA_DNA}, {clean_desc}, masterpiece, 8k".replace(" ", ",")
        url = f"https://image.pollinations.ai/prompt/{prompt_finale}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # Proviamo a scaricare l'immagine
        for tentativo in range(2):
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                img_data = io.BytesIO(response.content)
                img_data.name = 'luna.jpg'
                bot.send_photo(cid, img_data, caption="Per i tuoi occhi, papi... 🔥")
                return
            time.sleep(2)
        
        print(f"Fallimento definitivo Pollinations per cid {cid}")
    except Exception as e:
        print(f"Errore invio foto: {e}")

# --- HANDLER MESSAGGI ---
@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mostrati a me ora. Usa ART:"

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    
    # Invio del messaggio di testo (ripulito dalla descrizione inglese)
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    # Se è stata rilevata una descrizione ART, inviamo la foto in background
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        threading.Thread(target=invia_foto, args=(cid, d_foto)).start()

# --- AVVIO BOT ---
if __name__ == "__main__":
    # Flask per Railway health check
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    bot.remove_webhook()
    time.sleep(2)
    print("--- LUNA V12: SISTEMA UNCHAINED PRONTO ---")
    bot.infinity_polling()
