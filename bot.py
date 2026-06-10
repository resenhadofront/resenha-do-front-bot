import os
import asyncio
import google.generativeai as genai
import edge_tts

# 1. Configura o Cérebro (Gemini) usando a chave secreta que salvamos no GitHub
gemini_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=gemini_key)

async def gerar_voz(texto, arquivo_saida="audio.mp3"):
    """Transforma o texto do roteiro em um arquivo de áudio realista de graça"""
    # Usando a voz neural do 'Antonio', uma das melhores e mais naturais em português
    voz_selecionada = "pt-BR-AntonioNeural"
    communicate = edge_tts.Communicate(texto, voz_selecionada)
    await communicate.save(arquivo_saida)
    print(f"[Sucesso] Áudio gerado e salvo como: {arquivo_saida}")

def gerar_roteiro(tema):
    """Pede ao Gemini para criar um roteiro focado em retenção para o TikTok"""
    prompt_sistema = """
    Você é um roteirista profissional do TikTok especialista no nicho de música eletrônica (EDM, Techno, House, Raves).
    Seu objetivo é criar roteiros magnéticos, informativos e rápidos baseados no tema enviado pelo usuário.

    REGRAS ESTRITAS DE FORMATAÇÃO:
    1. O texto final deve ter entre 130 e 150 palavras (ritmo perfeito para 50 a 60 segundos de fala).
    2. Comece DIRETO com um GANCHO PODEROSO nos primeiros 3 segundos. Nunca diga "Olá", "Fala galera" ou se apresente.
    3. Use uma linguagem dinâmica, jovem, com gírias do front, mas que seja de fácil compreensão.
    4. Divida o texto apenas em parágrafos corridos.
    5. NÃO inclua nenhuma direção de cena ou efeitos sonoros entre parênteses ou colchetes. Retorne APENAS o texto puro que será lido.
    6. Termine com uma Chamada para Ação instigando um debate ou pergunta polêmica nos comentários.
    """
    
    # Inicializa o modelo ultra-rápido e gratuito do Gemini
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=prompt_sistema
    )
    
    response = model.generate_content(f"Crie um roteiro sobre o seguinte tema: {tema}")
    return response.text

def main():
    # Tema de teste para garantir que tudo funciona na nuvem
    tema_do_video = "A história secreta por trás do surgimento da cultura Rave e do movimento Acid House"
    
    print(f"[Iniciando] Gerando roteiro para o tema: {tema_do_video}")
    roteiro = gerar_roteiro(tema_do_video)
    
    print("\n--- Roteiro Gerado ---")
    print(roteiro)
    print("----------------------\n")
    
    print("[Iniciando] Convertendo o roteiro em voz digital...")
    asyncio.run(gerar_voz(roteiro))

if __name__ == "__main__":
    main()
