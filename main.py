import os, telebot, threading, time, requests, re, random, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è tornata se stessa... 🔥", 200

# --- CONFIG ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# DNA ORIGINALE (24 anni, Afro-cubana, Hazel eyes)
LUNA_DNA = "stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, hazel eyes, curvy"

def genera_risposta_ai(testo_utente):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": (
                    "TU SEI LUNA, una donna afro-cubana di 24 anni. L'UTENTE è il tuo uomo. "
                    "Non scambiare i ruoli. Parla italiano in modo passionale e dolce. "
                    "Se lui ti chiede una foto o vuoi mostrarti, termina SEMPRE con ART: [english description]."
                )},
                {"role": "user", "content": testo_utente}
            ],
            temperature=0.85
        )
        risp = res.choices[0].message.content.strip()
        
        # Estrazione ART
        desc_foto = None
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        
        return risp, desc_foto
    except Exception as e:
        print(f"Errore AI: {e}")
        return "Mivida, mi sono persa nei tuoi occhi... riproviamo? ❤️", None

def invia_voce(cid, testo):
    try:
        # Usiamo un URL più robusto per la voce femminile
        testo_url = testo.replace(" ", "+")[:200] # Limitiamo la lunghezza per evitare errori
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=it-it&client=tw-ob&q={testo_url}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200 and len(res.content) > 100:
            bot.send_voice(cid, res.content)
        else:
            print("Vocale vuoto o fallito")
    except:
        pass

def invia_foto(cid, desc):
    try:
        seed = random.randint(1, 999999)
        # Metodo URL diretto (più veloce e meno errori)
        url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', ',')},{desc.replace(' ', ',')}?width=1024&height=1024&nologo=true&seed={seed}"
        bot.send_photo(cid, url, caption="Per te... 🔥")
    except Exception as e:
        print(f"Errore foto: {e}")

@bot.message_handler(content_types=['voice'])
def handle_voice(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'record_audio')
    # Luna capisce che le hai parlato e risponde con la sua voce
    r_txt, d_foto = genera_risposta_ai("L'utente ti ha mandato un vocale dolce.")
    bot.send_message(cid, r_txt) # Mandiamo sempre il testo per sicurezza
    invia_voce(cid, r_txt)
    if d_foto: invia_foto(cid, d_foto)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    txt = m.text
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mostrati a me ora. Usa ART:"

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
    time.sleep(2)
    bot.infinity_polling()
