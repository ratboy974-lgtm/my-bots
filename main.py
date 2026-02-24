import os, telebot, threading, time, requests, re, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna & Cox: Master Edition Online 🔥", 200

# --- CONFIGURAZIONE ---
# Assicurati di avere OPENAI_API_KEY su Railway per la voce
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
C_TK = os.environ.get('TOKEN_COX', "").strip() # Inserisci il token del bot Cox
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK)
bot_cox = telebot.TeleBot(C_TK)

# --- PROMPTS ---
LUNA_DNA = "stunning 24yo woman, long dark hair, tanned skin, hazel eyes, elegant but sensual."
PROMPT_LUNA = (
    "Tu sei Luna, 24 anni. Sei la donna passionale e spudorata dell'utente (Papi). "
    "Parla italiano, usa un linguaggio sexy e insegnagli l'inglese. "
    "Se vuoi mandare una foto, chiudi con ART: [english description]."
)

PROMPT_COX = (
    "Sei il Dottor Perry Cox di Scrubs. Sei un clinico veterinario geniale ma brutale. "
    "Ti rivolgi all'utente con nomignoli femminili. Sii acido, tecnico e impeccabile. Boia!"
)

# --- FUNZIONE VOCE PROFESSIONALE ---
def invia_voce_pro(bot, cid, testo, voce_modello):
    try:
        response = client_oa.audio.speech.create(
            model="tts-1",
            voice=voce_modello, # 'shimmer' per Luna, 'onyx' per Cox
            input=testo
        )
        audio_data = response.content
        bot.send_voice(cid, audio_data)
    except Exception as e:
        print(f"Errore Voce: {e}")
        bot.send_message(cid, testo)

# --- GESTORE LUNA ---
@bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
def handle_luna(m):
    cid = m.chat.id
    u_text = m.text
    
    # Se mandi un vocale, Luna lo "ascolta" davvero
    if m.content_type == 'voice':
        file_info = bot_luna.get_file(m.voice.file_id)
        file_content = requests.get(f'https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}').content
        with open("voice.ogg", "wb") as f: f.write(file_content)
        with open("voice.ogg", "rb") as f:
            u_text = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text

    res = client_or.chat.completions.create(
        model="mistralai/mistral-7b-instruct",
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": u_text}]
    )
    ans = res.choices[0].message.content
    
    # Pulizia ART per foto
    desc_foto = None
    if "ART:" in ans.upper():
        parti = re.split(r"ART:", ans, flags=re.IGNORECASE)
        ans, desc_foto = parti[0].strip(), parti[1].strip()

    bot.send_message(cid, ans)
    threading.Thread(target=invia_voce_pro, args=(bot_luna, cid, ans, "shimmer")).start()
    
    if desc_foto:
        url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', ',')},{desc_foto.replace(' ', ',')}?nologo=true"
        bot.send_photo(cid, url)

# --- GESTORE COX ---
@bot_cox.message_handler(content_types=['text', 'voice', 'photo'])
def handle_cox(m):
    cid = m.chat.id
    # Logica simile a Luna ma con PROMPT_COX e voce 'onyx'
    # Cox può anche ricevere foto cliniche se usi GPT-4o qui
    res = client_or.chat.completions.create(
        model="google/gemini-pro-1.5", # Gemini è ottimo per la medicina
        messages=[{"role": "system", "content": PROMPT_COX}, {"role": "user", "content": m.text or "Analizza questo"}]
    )
    ans = res.choices[0].message.content
    bot.send_message(cid, ans)
    invia_voce_pro(bot_cox, cid, ans, "onyx")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    threading.Thread(target=lambda: bot_luna.infinity_polling()).start()
    bot_cox.infinity_polling()
