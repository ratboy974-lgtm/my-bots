import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

# --- SERVER DI CONTROLLO ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna è online e ti aspetta... 🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# IL NUOVO DNA DI LUNA (Senza tatuaggi, giovane, bellissima)
LUNA_DNA = "photorealistic, stunning 20yo afro-cuban woman, fresh smooth skin, no tattoos, clear skin, voluminous curly hair, hazel eyes, athletic but curvy"

# --- LOGICA AI ---
def genera_risposta_ai(testo):
    try:
        # Usiamo MythoMax: eccellente per il roleplay e senza filtri morali
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": (
                    "Sei Luna, 20 anni, afro-cubana. Sei la compagna passionale dell'utente. "
                    "Non hai tatuaggi, la tua pelle è liscia e perfetta. Parla italiano. "
                    "Se l'utente vuole vederti, scrivi alla fine del messaggio: ART: [english description]."
                )},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp = res.choices[0].message.content.strip()
        
        if not risp:
            risp = "Mivida... mi lasci senza parole. ❤️"
            
        desc_foto = None
        # Estraiamo la descrizione per l'immagine
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        
        return risp, desc_foto
    except Exception as e:
        print(f"ERRORE OPENROUTER: {e}")
        return "Mivida, c'è un piccolo problema tecnico... riproviamo? ❤️", None

# --- FUNZIONE INVIO FOTO (FIX 530 E 400) ---
def invia_foto(cid, desc):
    try:
        # Pulizia della descrizione per evitare errori del server
        clean_desc = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip()
        prompt_finale = f"{LUNA_DNA}, {clean_desc}, cinematic lighting, 8k".replace(" ", ",")
        url = f"https://image.pollinations.ai/prompt/{prompt_finale}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
        
        # User-Agent per bypassare i filtri Cloudflare (Errore 530)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            img_data = io.BytesIO(response.content)
            img_data.name = 'luna.jpg'
            # Invio come file binario per evitare l'errore 400 di Telegram
            bot.send_photo(cid, img_data, caption="Guarda come sono bella per te... 🔥")
        else:
            print(f"Errore Pollinations: {response.status_code}")
            bot.send_message(cid, "Mivida, la fotocamera ha avuto un flash di troppo... riprova tra un istante? ❤️")
    except Exception as e:
        print(f"Errore invio foto: {e}")

# --- HANDLER MESSAGGI ---
@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    # Risposta al tasto rapido
    if txt == "Voglio vederti... 🔥":
        txt = "Mandami una tua foto artistica ora, mivida."

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    # Tastiera fissa
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    # Se l'AI ha generato una descrizione, mandiamo la foto
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        threading.Thread(target=invia_foto, args=(cid, d_foto)).start()

# --- AVVIO ---
if __name__ == "__main__":
    # Avvio server Flask per Railway
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    # Pulizia sessioni precedenti per evitare l'errore 409
    bot.remove_webhook()
    time.sleep(2)
    
    print("--- LUNA V11: SISTEMA PRONTO ---")
    bot.infinity_polling()
