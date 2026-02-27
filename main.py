# --- MOTORE FOTO V96.6 ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"RAW photo, upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, high quality, 8k"
    
    try:
        # Usiamo un payload più snello per Fal
        payload = {"prompt": full_prompt, "image_size": "portrait_4_5", "sync_mode": True}
        res = requests.post(url, headers=headers, json=payload, timeout=90) # Timeout alzato a 90s
        
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            time.sleep(2)
            img_res = requests.get(img_url, timeout=40)
            
            # Se la foto è < 50KB, Fal ci ha mandato un errore mascherato
            if img_res.status_code == 200 and len(img_res.content) > 50000:
                return img_res.content
            else:
                print(f"⚠️ Errore Fal: Immagine troppo piccola ({len(img_res.content)} bytes)")
    except Exception as e:
        print(f"❌ Errore fotocamera: {e}")
    return None

# --- GESTIONE VOCALE V96.6 ---
# Inseriscila nel blocco 'if m.content_type == 'voice':'
    if m.content_type == 'voice':
        try:
            bot_luna.send_chat_action(cid, 'upload_voice') # Notifica "Luna sta ascoltando..."
            f_info = bot_luna.get_file(m.voice.file_id)
            # Scarichiamo l'audio con timeout generoso
            audio_res = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}", timeout=30)
            
            if audio_res.status_code == 200:
                audio_io = io.BytesIO(audio_res.content)
                audio_io.name = "audio.ogg"
                # Whisper trascrive l'audio
                transcription = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io)
                input_text = transcription.text
                print(f"🎙️ Vocale capito: {input_text}")
            else:
                bot_luna.send_message(cid, "Papi, non sono riuscita a sentire bene l'audio. Riprovi? 💋")
                return
        except Exception as e:
            print(f"❌ Errore Whisper: {e}")
            bot_luna.send_message(cid, "Mi si è tappato l'orecchio... puoi ripetere? ❤️")
            return
