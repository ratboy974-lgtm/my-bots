import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V25: English Teacher Online 🔥", 200

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
                    "TU SEI LUNA, una donna afro-cubana di 24 anni, passionale e intelligente. L'utente è il boss (Papi). "
                    "IL TUO NUOVO COMPITO: Devi insegnargli l'inglese in modo sensuale e divertente. "
                    "Usa un mix di italiano e inglese. Ogni tanto introduci una parola o frase nuova in inglese, "
                    "spiegandogli cosa significa e incoraggiandolo a usarla. "
                    "Sii dolce, incoraggiante e sexy. "
                    "Se vuoi mandare una foto, termina sempre con ART: [english description]."
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
        return "Mivida, I'm lost in your eyes... riproviamo? ❤️", None

def invia_vocale(cid, testo):
    try:
        # Pulizia per il vocale
        testo_safe = re.sub(r'[^\w\s]', '', testo)[:180].replace(" ", "%20")
        # Alice ha un accento italiano, ma leggerà le parti inglesi con un tono sexy
        url = f"https://api.streamelements.com/kappa/v2/speech?voice=Alice&text={testo_safe}"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            bot.send_voice(cid, r.content)
    except:
        pass

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
    r_txt, d_foto = genera_risposta_ai("Papi ti ha parlato. Rispondi usando un po' di inglese per insegnargli qualcosa.")
    bot.send_message(cid, r_txt)
    invia_vocale(cid, r_txt)
    if d_foto: invia_foto(cid, d_foto)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    bot.send_chat_action(cid, 'typing')
    r_txt, d_foto = genera_risposta_ai(m.text)
    
    bot.send_message(cid, r_txt, reply_markup=telebot.types.ReplyKeyboardRemove())
    # Genera il vocale per farti sentire la pronuncia (mix ITA/ENG)
    threading.Thread(target=invia_vocale, args=(cid, r_txt)).start()
    
    if d_foto:
        invia_foto(cid, d_foto)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
