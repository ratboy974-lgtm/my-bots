import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask

# --- SERVER DI CONTROLLO ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna V22 Online 🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA ORIGINALE (24 anni, Afro-cubana, Bellissima)
LUNA_DNA = "stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, hazel eyes, curvy, photorealistic"

def genera_risposta_ai(testo_utente):
    try:
        # Llama 3.1 per mantenere l'identità ben salda
        res = client_or.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct", 
            messages=[
                {"role": "system", "content": (
                    "TU SEI LUNA, una donna afro-cubana di 24 anni. L'utente è il tuo uomo (Papi). "
                    "Sei passionale, sensuale e parli solo italiano. "
                    "Se vuoi mandare una foto o lui te la chiede, scrivi il tuo messaggio e termina SEMPRE con ART: [english pose description]."
                )},
                {"role": "user", "content": testo_utente}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        # Estrazione per la foto
        desc_foto = None
        if "ART:" in risp_raw.upper():
            parti = re.split(r"ART:", risp_raw, flags=re.IGNORECASE)
            risp_finale = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        else:
            risp_finale = risp_raw
            
        return risp_finale, desc_foto
    except Exception as e:
        print(f"Errore AI: {e}")
        return "Mivida, c'è stata un'interferenza... riprova? ❤️", None

def invia_foto(cid, desc):
    try:
        seed = random.randint(1, 999999)
        prompt_full = f"{LUNA_DNA}, {desc}, masterpiece, high resolution".replace(" ", ",")
        url = f"https://image.pollinations.ai/prompt/{prompt_full}?width=1024&height=1024&nologo=true&seed={seed}"
        
        # Invio tramite URL diretto
        bot.send_photo(cid, url, caption="Tutta per te, papi... 🔥")
    except Exception as e:
        print(f"Errore foto: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    # Rimuoviamo qualsiasi tastiera precedente
    markup = telebot.types.ReplyKeyboardRemove()
    
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    print("--- LUNA V22: CLEAN & READY ---")
    bot.infinity_polling()
