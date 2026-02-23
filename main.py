import os, telebot, threading, time, requests, re
from openai import OpenAI
from flask import Flask
from telebot import types

# --- SERVER DI CONTROLLO ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna V12: Final Stand 🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA LUNA: 20 anni, afro-cubana, pelle liscia, NO TATTOO (Approvato)
LUNA_DNA = "photorealistic, stunning 20yo afro-cuban woman, fresh smooth skin, no tattoos, curly hair, hazel eyes"

# --- LOGICA AI ---
def genera_risposta_ai(testo):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": (
                    "Sei Luna, 20 anni, afro-cubana senza tatuaggi. Parla italiano. "
                    "Se l'utente vuole una foto, scrivi un messaggio breve e "
                    "termina SEMPRE con ART: [english description]."
                )},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        desc_foto = None
        # Taglio chirurgico del testo alla parola ART:
        match = re.search(r"ART[:\s\-\[\(]*(.*)", risp_raw, re.IGNORECASE | re.DOTALL)
        
        if match:
            desc_foto = match.group(1).strip().replace("[", "").replace("]", "").replace(")", "")
            risp_finale = risp_raw[:match.start()].strip()
            if not risp_finale: risp_finale = "Eccomi qui, mivida... 🔥"
        else:
            risp_finale = risp_raw
        
        return risp_finale, desc_foto
    except Exception as e:
        print(f"ERRORE AI: {e}")
        return "Mivida, riproviamo? ❤️", None

# --- FUNZIONE INVIO FOTO (METODO URL DIRETTO) ---
def invia_foto(cid, desc):
    try:
        # Pulizia prompt per URL
        clean_desc = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip().replace(" ", ",")
        prompt_url = f"{LUNA_DNA.replace(' ', ',')},{clean_desc},masterpiece,8k"
        
        # URL DIRETTO: Farà scaricare l'immagine direttamente ai server di Telegram
        url_finale = f"https://image.pollinations.ai/prompt/{prompt_url}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
        
        # Mandiamo l'URL a Telegram senza scaricarlo noi
        bot.send_photo(cid, url_finale, caption="Tutta per te... 🔥")
    except Exception as e:
        print(f"Errore invio URL foto: {e}")

# --- HANDLER ---
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
        # Notifica visiva per l'utente
        bot.send_chat_action(cid, 'upload_photo')
        # Invio immediato del link
        invia_foto(cid, d_foto)

# --- AVVIO ---
if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    print("--- LUNA FINAL STAND ONLINE ---")
    bot.infinity_polling()
