import os, telebot, threading, time, requests, re, io
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V12 Online 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# Identikit definitivo approvato
LUNA_DNA = "photorealistic, stunning 20yo afro-cuban woman, fresh smooth skin, no tattoos, curly hair, hazel eyes, athletic curvy"

def genera_risposta_ai(testo):
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=[
                {"role": "system", "content": "Sei Luna, 20 anni, afro-cubana senza tatuaggi. Parla italiano. Se papi chiede foto, scrivi un messaggio breve e finisci SEMPRE con ART: [5 english keywords]."},
                {"role": "user", "content": testo}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        desc_foto = None
        # Taglia tutto ciò che viene dopo la parola ART (in qualsiasi formato)
        match = re.search(r"ART[:\s\-\[\(]*(.*)", risp_raw, re.IGNORECASE | re.DOTALL)
        
        if match:
            desc_foto = match.group(1).strip().replace("[", "").replace("]", "").replace(")", "")
            risp_finale = risp_raw[:match.start()].strip()
            if not risp_finale: risp_finale = "Eccomi qui per te... 🔥"
        else:
            risp_finale = risp_raw
        
        return risp_finale, desc_foto
    except Exception as e:
        print(f"DEBUG: Errore AI -> {e}")
        return "Mivida, c'è un piccolo intoppo... riprova? ❤️", None

def invia_foto(cid, desc):
    try:
        clean_desc = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip()
        # Costruiamo il link diretto per Pollinations
        prompt_full = f"{LUNA_DNA}, {clean_desc}, masterpiece, 8k".replace(" ", ",")
        url = f"https://image.pollinations.ai/prompt/{prompt_full}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Scarichiamo i byte dell'immagine per bypassare i blocchi regionali
        response = requests.get(url, headers=headers, timeout=25)
        
        if response.status_code == 200:
            img_data = io.BytesIO(response.content)
            img_data.name = 'luna.jpg'
            bot.send_photo(cid, img_data, caption="Solo per i tuoi occhi... 🔥")
        else:
            print(f"DEBUG: Pollinations Error {response.status_code}")
    except Exception as e:
        print(f"DEBUG: Errore invio foto -> {e}")

@bot.message_handler(func=lambda m: True)
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mandami una foto usando ART:"

    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(txt)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    
    bot.send_message(cid, r_txt, reply_markup=markup)
    
    if d_foto:
        bot.send_chat_action(cid, 'upload_photo')
        # Thread separato per non bloccare la chat
        threading.Thread(target=invia_foto, args=(cid, d_foto)).start()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    print("--- LUNA V12 ONLINE ---")
    bot.infinity_polling()
