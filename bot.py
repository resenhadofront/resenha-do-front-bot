import os
import asyncio
import google.generativeai as genai
import edge_tts
import requests

# 1. Configurações das chaves secretas que salvamos no GitHub
gemini_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=gemini_key)
pexels_key = os.environ.get("PEXELS_API_KEY")

async def gerar_voz(texto, arquivo_saida="audio.mp3"):
    """Transforma o texto do roteiro em um arquivo de áudio de graça"""
    voz_selecionada = "pt-BR-AntonioNeural"
    communicate = edge_tts.Communicate(texto, voz_selecionada)
    await communicate.save(arquivo_saida)
    print(f"[Sucesso] Áudio gerado e salvo como: {arquivo_saida}")

def gerar_roteiro(tema):
    """Pede ao Gemini para criar o roteiro focado em retenção"""
    prompt_sistema = """
    Você é um roteirista profissional do TikTok especialista no nicho de música eletrônica.
    Seu objetivo é criar roteiros magnéticos, informativos e rápidos baseados no tema enviado.

    REGRAS ESTRITAS:
    1. O texto final deve ter entre 130 e 150 palavras (ritmo perfeito para 50-60 segundos).
    2. Comece DIRETO com um GANCHO PODEROSO. Nunca se apresente.
    3. Use linguagem dinâmica com gírias do front.
    4. Divida apenas em parágrafos corridos, sem direções de cena parentéticas.
    5. Termine com uma Chamada para Ação instigando um debate nos comentários.
    """
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=prompt_sistema
    )
    response = model.generate_content(f"Crie um roteiro sobre o seguinte tema: {tema}")
    return response.text

def baixar_videos_pexels(query="rave festival", quantidade=3):
    """Busca e baixa clipes na vertical (estilo TikTok) do Pexels totalmente de graça"""
    print(f"[Iniciando] Buscando vídeos no Pexels para o termo: '{query}'...")
    headers = {"Authorization": pexels_key}
    
    # O truque está aqui: 'orientation=portrait' garante vídeos em pé prontos pro TikTok!
    url = f"https://api.pexels.com/v1/videos/search?query={query}&per_page={quantidade}&orientation=portrait"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if "videos" not in data or len(data["videos"]) == 0:
            print("[Erro] Nenhum vídeo encontrado no Pexels.")
            return []
            
        arquivos_baixados = []
        for i, video in enumerate(data["videos"]):
            video_files = video.get("video_files", [])
            video_url = None
            
            # Filtra para encontrar o arquivo no formato MP4 correto
            for f_file in video_files:
                if f_file.get("file_type") == "video/mp4":
                    video_url = f_file.get("link")
                    break
            
            if video_url:
                nome_arquivo = f"video_{i}.mp4"
                print(f"Baixando clipe de fundo {i+1}/{quantidade}...")
                res = requests.get(video_url)
                with open(nome_arquivo, "wb") as f:
                    f.write(res.content)
                arquivos_baixados.append(nome_arquivo)
        
        print(f"[Sucesso] {len(arquivos_baixados)} vídeos de fundo baixados com sucesso!")
        return arquivos_baixados
    except Exception as e:
        print(f"[Erro] Falha ao conectar ou baixar do Pexels: {e}")
        return []

def main():
    tema_do_video = "A história secreta por trás do surgimento da cultura Rave e do movimento Acid House"
    
    print(f"[Passo 1] Acionando o Gemini para criar o roteiro...")
    roteiro = gerar_roteiro(tema_do_video)
    print("\n--- Roteiro Gerado ---")
    print(roteiro)
    print("----------------------\n")
    
    print("[Passo 2] Convertendo o texto em voz com o sistema da Microsoft...")
    asyncio.run(gerar_voz(roteiro))
    
    print("\n[Passo 3] Coletando imagens do front no Pexels...")
    # O robô vai buscar clipes de festivais eletrônicos na vertical para usar de fundo
    baixar_videos_pexels(query="electronic music festival", quantidade=3)

if __name__ == "__main__":
    main()
