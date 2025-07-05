def call_ai(ia_type: str, ia_key: str, modele: str, prompt: str) -> str:
    if ia_type == "openai":
        import openai
        openai.api_key = ia_key
        response = openai.ChatCompletion.create(
            model=modele,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message["content"]

    elif ia_type == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=ia_key)
        model = genai.GenerativeModel(model_name=modele)
        response = model.generate_content(prompt)
        return response.text

    elif ia_type == "groq":
        import groq
        groq.api_key = ia_key
        response = groq.ChatCompletion.create(
            model=modele,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message["content"]

    else:
        raise ValueError(f"Type d’IA non supporté : {ia_type}")