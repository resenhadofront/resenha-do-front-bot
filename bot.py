import os
import subprocess
from groq import Groq
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

# 1. Configurações das chaves secretas vindas do GitHub Secrets
groq_key = os.environ.get("GROQ_API_KEY")
pexels_key = os.environ.get("PEXELS_API_KEY")

client = Groq(api_key=groq_key)

def limpar_roteiro_ia(texto_bruto):
    """Remove marcações estruturais e tags que a IA teima em colocar no texto"""
    texto_sem_markdown = texto_bruto.replace("**", "").replace("*", "").replace("#", "")
    linhas = texto_sem_markdown.split("\n")
    linhas_limpas = []
    
    tags_proibidas = ["gancho", "chamada", "introdução", "parágrafo", "roteiro", "narrador", "cena", "texto", "cta"]
    
    for linha in linhas:
        linha_limpa = linha.strip()
        linha_min = linha_limpa.lower()
        
        if any(tag in linha_min for tag in tags_proibidas) and (len(linha_limpa) < 30 or ":" in linha_limpa):
            continue
        if linha_limpa.startswith("[") or linha_limpa.startswith("("):
            continue
        if linha_limpa:
            linhas_limpas.append(linha_limpa)
            
    return " ".join(linhas_limpas)

def gerar_voz_e_legenda(texto, audio_path="audio.mp3", sub_path="legenda.srt"):
    """Gera o arquivo de áudio e extrai a legenda SRT perfeitamente sincronizada"""
    print("[Iniciando] Solicitando narração e sincronismo de legenda ao Edge-TTS...")
    cmd = [
        "edge-tts",
        "--voice", "pt-BR-AntonioNeural",
        "--text", texto,
        "--write-media", audio_path,
        "--write-subtitles", sub_path
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"[Sucesso] Áudio e Legendas SRT gerados!")
        return True
    except Exception as e:
        print(f"[Erro no Voice] Falha ao rodar o gerador de voz/legenda: {e}")
        return False

def gerar_roteiro(tema):
    """Gera um roteiro magnético focado em retenção usando o Llama 3"""
    prompt_sistema = """
    Você é um roteirista de elite do TikTok focado no nicho de música eletrônica underground.
    Seu trabalho é transformar fatos históricos, curiosidades de DJs e segredos do front em vídeos virais magnéticos.

    ESTRUTURA DA NARRATIVA:
    1. GANCHO DE RETENÇÃO (0-5s): Comece com uma afirmação chocante ou uma pergunta intrigante. Proibido saudações (nada de 'Olá galera').
    2. CONTEXTO RÍTMICO (5-45s): Escreva em frases curtas e diretas. Use termos do front de forma orgânica. Crie tensão e curiosidade.
    3. CHAMADA PARA AÇÃO (45-60s): Termine com uma pergunta polêmica que force o espectador a comentar e debater.

    REGRAS ESTRITAS DE FORMATO:
    - Retorne APENAS o texto corrido a ser lido.
    - É proibido usar títulos como 'Gancho:', 'Narrador:', ou marcas de cena.
    - Não use nenhuma formatação em Markdown (como asteriscos).
    - O tamanho total deve ficar entre 125 e 145 palavras.
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": f"Escreva a narração para o TikTok sobre o tema: {tema}"}
            ],
            temperature=0.75,
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise Exception(f"Falha ao gerar roteiro na Groq: {e}")

def gerar_termos_busca_visuais(roteiro):
    """Pede à IA para analisar o roteiro e criar 4 termos de busca visuais em inglês para o Pexels"""
    prompt_sistema = """
    Você é um diretor de arte de vídeos curtos. Analise o roteiro fornecido e crie exatamente 4 termos de busca diferentes em inglês para encontrar vídeos verticais no Pexels. Foco em música eletrônica, raves e DJs.
    Retorne APENAS os 4 termos separados por vírgula em uma única linha. Não inclua números ou explicações.
    Exemplo: berlin techno club, dj mixing vinyl, rave strobe lights, crowd dancing portrait
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": f"Roteiro: {roteiro}"}
            ],
            temperature=0.5,
        )
        termos = completion.choices[0].message.content.strip()
        lista_termos = [t.strip() for t in termos.split(",") if t.strip()]
        if len(lista_termos) < 2:
            return ["underground rave crowd", "techno dj lighting", "electronic music festival", "dancing club portrait"]
        return lista_termos[:4]
    except Exception:
        return ["underground rave crowd", "techno dj lighting", "electronic music festival", "dancing club portrait"]

def baixar_videos_pexels_dinamico(queries):
    """Baixa um clipe vertical do Pexels para cada um dos termos dinâmicos"""
    print("\n[Passo 3] Iniciando coleta de mídia dinâmica baseada no contexto...")
    headers = {"Authorization": pexels_key}
    arquivos_baixados = []
    
    for i, query in enumerate(queries):
        print(f"Buscando clipe {i+1}/4 para o conceito: '{query}'...")
        url = f"https://api.pexels.com/v1/videos/search?query={query}&per_page=1&orientation=portrait"
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            if "videos" in data and len(data["videos"]) > 0:
                video_files = data["videos"][0].get("video_files", [])
                video_url = None
                for f_file in video_files:
                    if f_file.get("file_type") == "video/mp4":
                        video_url = f_file.get("link")
                        break
                if video_url:
                    nome_arquivo = f"video_{i}.mp4"
                    res = requests.get(video_url)
                    with open(nome_arquivo, "wb") as f:
                        f.write(res.content)
                    arquivos_baixados.append(nome_arquivo)
                    print(f"-> Clipe '{nome_arquivo}' baixado com sucesso!")
            else:
                print(f"-> Sem resultados para '{query}'. Pulando...")
        except Exception as e:
            print(f"-> Erro ao buscar termo '{query}': {e}")
            
    return arquivos_baixados

def editar_video_base(videos, audio_path, output_path="video_cru.mp4"):
    """Une as mídias dinâmicas com o áudio"""
    print("\n[Passo 4] Realizando a colagem de mídias com o MoviePy...")
    try:
        audio_clip = AudioFileClip(audio_path)
        duracao_audio = audio_clip.duration

        clips_video = [VideoFileClip(v) for v in videos]
        video_concatenated = concatenate_videoclips(clips_video, method="compose")
        video_final = video_concatenated.set_audio(audio_clip)
        
        if video_final.duration > duracao_audio:
            video_final = video_final.subclip(0, duracao_audio)
            
        video_final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None
        )
        
        audio_clip.close()
        video_final.close()
        for c in clips_video:
            c.close()
            
        print(f"[Sucesso] Vídeo base estruturado!")
        return True
    except Exception as e:
        print(f"[Erro de Edição] Falha na montagem básica: {e}")
        return False

def aplicar_legendas_estilizadas(video_input, legenda_input, video_output="video_final.mp4"):
    """Renderiza a legenda estilizada estilo TikTok usando arquivo SRT de forma estável"""
    print("\n[Passo 5] Aplicando legendas dinâmicas estilo TikTok via FFmpeg...")
    
    # Estilo ASS/SRT estável: Fonte DejaVu Sans, amarela, borda preta grossa, centralizada
    estilo_tiktok = "Fontname=DejaVu Sans,FontSize=24,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.5,Alignment=5"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_input,
        "-vf", f"subtitles={legenda_input}:force_style='{estilo_tiktok}'",
        "-c:a", "copy",
        video_output
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"[Sucesso] Vídeo mobile definitivo pronto: {video_output}")
        return True
    except Exception as e:
        print(f"[Erro nas Legendas] Falha ao embutir texto no vídeo: {e}")
        return False

def main():
    tema_do_video = "A história secreta por trás do surgimento da cultura Rave e do movimento Acid House"
    print("[Passo 1] Solicitando roteiro otimizado para retenção...")
    try:
        roteiro_bruto = gerar_roteiro(tema_do_video)
        roteiro_limpo = limpar_roteiro_ia(roteiro_bruto)
        print("\n--- Roteiro Final Organizado ---")
        print(roteiro_limpo)
        print("--------------------------------\n")
        
        # Gera o áudio e a legenda SRT juntos
        if not gerar_voz_e_legenda(roteiro_limpo, "audio.mp3", "legenda.srt"):
            raise Exception("Erro ao gerar voz e legenda.")
        
        termos_visuais = gerar_termos_busca_visuais(roteiro_limpo)
        print(f"Conceitos visuais definidos pelo Bot: {termos_visuais}")
        
        videos_baixados = baixar_videos_pexels_dinamico(termos_visuais)
        
        if len(videos_baixados) >= 2:
            if not editar_video_base(videos_baixados, "audio.mp3", "video_cru.mp4"):
                raise Exception("Erro na criação do vídeo base.")
                
            if not aplicar_legendas_estilizadas("video_cru.mp4", "legenda.srt", "video_final.mp4"):
                raise Exception("Erro na aplicação das legendas.")
        else:
            raise Exception("Mídias insuficientes baixadas do Pexels.")
            
        print("\n[Fim] Script executado com sucesso completo!")
    except Exception as err:
        print(f"\n[Erro Geral Contido] {err}")
        exit(1) # Agora força o erro no GitHub se algo der errado de verdade!

if __name__ == "__main__":
    main()
