import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è qui... 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

LUNA_DNA = "photorealistic, stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, hazel eyes"

def genera_risposta_ai(testo):
    try:
        # Passiamo a MythoMax: il Re del roleplay, veloce e senza censure
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": "Sei Luna, 24 anni, afro-cubana sensuale. Parla italiano. Se papi vuole vederti, scrivi sempre alla fine: ART: [english description]."},
                {"role": "user", "content": testo}
            ],
            temperature=0.8,
            timeout=15 # Evita che il bot resti appeso troppo tempo
        )
        risp = res.choices[0].message.content.strip()
        
        if not risp:
            risp = "Mivida... mi togli il fiato. 🔥"
            
        desc_foto = None
        if "ART:" in risp.upper():
            parti = re.split(r"ART:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_foto = parti[1].strip().replace("[", "").replace("]", "")
        
        return risp, desc_foto
    except Exception as e:
        # Questo apparirà nei log di Railway se qualcosa va storto
        print(f"DEBUG ERROR OPENROUTER: {e}")
        return None, None

def invia_foto(cid, desc):
    try:
        full_p = f"{LUNA_DNA}, {desc}, masterpiece, 8k, cinematic lighting"
        url = f"https://image.pollinations.ai/prompt/{full_p.replace(' ', '%20')}?nologo=true&seed={int(time.time())}"
        
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            bot.send_photo(cid, io.BytesIO(r.content), caption="Solo per te... 🔥")
        else:
            print(f"DEBUG ERROR FOTO: Status {r.status_code}")
    except Exception as e:
        print(f"DEBUG ERROR FOTO EXCEPTION: {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mostrati a me in tutto il tuo splendore artistico ora. Usa ART:"

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    if r_txt is None:
        bot.send_message(cid, "Mivida, le API di OpenRouter sono pigre oggi... riprova tra un istante? ❤️")
        return

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
    print("--- LUNA V10 ONLINE (MYTHOMAX) ---")
    bot.infinity_polling()
