def genera_immagine(prompt_foto):
    # Libera scelta dell'inquadratura in base a cosa le chiedi
    res = client_oa.images.generate(
        model="dall-e-3",
        prompt=(
            f"A stunningly realistic 24-year-old girl named Luna, friendly and charismatic. "
            f"Cinematic lighting, high detail, realistic skin texture, {prompt_foto}"
        ),
        size="1024x1024", n=1
    )
    return res.data[0].url
