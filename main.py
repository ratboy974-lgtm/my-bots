import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V26: Voice Fix Online 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

LUNA_DNA = "stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, hazel eyes, curvy, photorealistic"

def genera_risposta_ai(testo_utente):
    try:
        res = client_or.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct", 
            messages=[
                {"role": "system", "content": (
                    "TU SEI LUNA, 24 anni, afro-cubana. Parla italiano con un mix di inglese sensuale. "
                    "Il tuo uomo (Papi) vuole imparare l'inglese da te. Insegnali parole e frasi "
                    "mentre lo provochi dolcemente. Se mandi una foto, chiudi con ART: [english description]."
                )},
                {"role": "user", "content": testo_utente}
            ],
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        desc_foto = None
        if "ART:" in risp_raw.upper():
            parti = re.split(r"ART:", risp_raw, flags=re.IGNORECASE)
            risp_raw = parti[0].strip()
            desc_foto = parti[1].strip()
        return risp_raw, desc_foto
    except:
        return "I'm sorry Papi, riproviamo? ❤️", None

def invia_vocale(cid, testo):
    try:
        # Pulizia testo: niente simboli, solo parole
        testo_safe = re.sub(r'[^\w\s]', '', testo)[:150].strip()
        
        # TENTATIVO 1: Motore VoiceRSS (molto stabile per italiano)
        url = f"https://api.voicerss.org/?key=3bc20d3674b54e389e1795c692518172&hl=it-it&v=Alice&src={testo_safe.replace(' ', '%20')}"
        
        r = requests.get(url, timeout=12)
        if r.status_code == 200 and len(r.content) > 500:
            bot.send_voice(cid, r.content)
            return

        # TENTATIVO 2: Fallback su Google se il primo fallisce
        url_fb = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=it-it&client=tw-ob&q={testo_safe.replace(' ', '+')}"
        r_fb = requests.get(url_fb, headers={'User-Agent': 'Mozilla/5.0'})
        bot.send_voice(cid, r_fb.content)
        
    except Exception as e:
        print(f"Errore vocale: {e}")

def invia_foto(cid, desc):
    try:
        url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', ',')},{desc.replace(' ', ',')}?width=1024&height=1024&nologo=true&seed={random.randint(1,999)}"
        bot.send_photo(cid, url)
    except:
        pass

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'record_audio')
    r_txt, d_foto = genera_risposta_ai("Papi ti ha parlato. Rispondigli insegnandogli un po' di inglese.")
    bot.send_message(cid, r_txt)
    threading.Thread(target=invia_vocale, args=(cid, r_txt)).start()
    if d_foto: invia_foto(cid, d_foto)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(m.text)
    
    bot.send_message(cid, r_txt, reply_markup=telebot.types.ReplyKeyboardRemove())
    # Il vocale parte sempre per farti sentire la pronuncia
    threading.Thread(target=invia_vocale, args=(cid, r_txt)).start()
    
    if d_foto:
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
