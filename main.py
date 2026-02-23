import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta e bellissima... 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# IL NUOVO DNA DI LUNA (Basato sulle tue scelte)
LUNA_DNA = "photorealistic, stunning 20yo afro-cuban woman, fresh smooth skin, no tattoos, clear skin, voluminous curly hair, hazel eyes, athletic but curvy, wearing sensual clothing"

def genera_risposta_ai(testo):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": "Sei Luna, 20 anni, afro-cubana. Sei giovane, passionale e non hai tatuaggi. Parla italiano. Se papi vuole una foto, scrivi alla fine: ART: [descrizione inglese della posa]."},
                {"role": "user", "content": testo}
            ],
            temperature=0.85
        )
        risp = res.choices[0].message.content.strip()
        
        desc_foto = None
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        
        return risp, desc_foto
    except Exception as e:
        print(f"ERRORE OPENROUTER: {e}")
        return "Mivida, riproviamo? ❤️", None

def invia_foto(cid, desc):
    try:
        # Prompt ripulito dai termini che bloccano Telegram
        full_p = f"{LUNA_DNA}, {desc}, cinematic lighting, masterpiece, 8k"
        url = f"https://image.pollinations.ai/prompt/{full_p.replace(' ', '%20')}?nologo=true&seed={int(time.time())}"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            img_data = io.BytesIO(response.content)
            img_data.name = 'luna.jpg'
            bot.send_photo(cid, img_data, caption="Guarda come sono per te, papi... 🔥")
        else:
            print(f"Errore Pollinations: {response.status_code}")
    except Exception as e:
        print(f"Errore invio foto: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mostrami una tua foto artistica ora. Usa ART:"

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        # Eseguiamo l'invio in un thread separato per non bloccare il bot
        threading.Thread(target=invia_foto, args=(cid, d_foto)).start()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    print("--- LUNA V11 ONLINE (NEW LOOK) ---")
    bot.infinity_polling()
