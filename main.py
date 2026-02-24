import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask

# --- SERVER DI CONTROLLO ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna V23: Voice Edition 🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA ORIGINALE
LUNA_DNA = "stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, hazel eyes, curvy, photorealistic"

def genera_risposta_ai(testo_utente):
    try:
        res = client_or.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct", 
            messages=[
                {"role": "system", "content": (
                    "TU SEI LUNA, una donna afro-cubana di 24 anni. L'utente è il tuo uomo (Papi). "
                    "Sei passionale, sensuale e parli solo italiano. "
                    "Se vuoi mandare una foto, termina SEMPRE con ART: [english pose description]."
                )},
                {"role": "user", "content": testo_utente}
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

# --- NUOVO MOTORE VOCALE FEMMINILE ---
def invia_vocale(cid, testo):
    try:
        # Usiamo un fornitore che garantisce la voce femminile italiana
        testo_pulito = testo[:200].replace(" ", "%20")
        url_voce = f"https://api.streamelements.com/kappa/v2/speech?voice=Alice&text={testo_pulito}"
        
        response = requests.get(url_voce, timeout=15)
        if response.status_code == 200:
            bot.send_voice(cid, response.content)
        else:
            print(f"Errore TTS: {response.status_code}")
    except Exception as e:
        print(f"Errore invio vocale: {e}")

def invia_foto(cid, desc):
    try:
        seed = random.randint(1, 999999)
        prompt_full = f"{LUNA_DNA}, {desc}, masterpiece".replace(" ", ",")
        url = f"https://image.pollinations.ai/prompt/{prompt_full}?width=1024&height=1024&nologo=true&seed={seed}"
        bot.send_photo(cid, url, caption="Tutta per te, papi... 🔥")
    except:
        pass

@bot.message_handler(content_types=['voice'])
def handle_audio(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'record_audio')
    # Luna risponde a un tuo vocale con la sua voce
    r_txt, d_foto = genera_risposta_ai("L'utente ti ha mandato un vocale. Rispondigli con amore.")
    invia_vocale(cid, r_txt)
    if d_foto: invia_foto(cid, d_foto)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(m.text)
    
    # Inviamo il testo
    bot.send_message(cid, r_txt, reply_markup=telebot.types.ReplyKeyboardRemove())
    
    # Inviamo il vocale (opzionale: se vuoi che parli sempre, lascia così)
    threading.Thread(target=invia_vocale, args=(cid, r_txt)).start()
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
