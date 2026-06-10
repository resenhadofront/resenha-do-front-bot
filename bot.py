import os
import asyncio
from groq import Groq
import edge_tts
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

# 1. Configurações das chaves secretas vindas do GitHub Secrets
groq_key = os.environ.get("GROQ_API_KEY")
pexels_key = os.environ.get("PEXELS_API_KEY")

# Inicializa o cliente da Groq
client = Groq(api_key=groq_key)

async def gerar_voz(texto, arquivo_saida="audio.mp3"):
    """Transforma o texto do roteiro num arquivo de áudio de forma gratuita"""
    voz_selecionada = "pt-BR-AntonioNeural"
    communicate = edge_tts.Communicate(texto, voz_selecionada)
    await communicate.save(arquivo_saida)
    print(f"[Sucesso] Áudio gerado e salvo como: {arquivo_saida}")

def gerar_roteiro(tema):
    """Pede ao Llama (via Groq) para criar o roteiro focado em retenção"""
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
    
    modelos_groq = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
    
    for modelo in modelos_groq:
        try:
            print(f"[Tentativa] Solicitando roteiro usando o modelo: {modelo}...")
            completion = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"Crie um roteiro sobre o seguinte tema: {tema}"}
                ],
                temperature=0.7,
            )
            print(f"[Sucesso] Roteiro gerado com o modelo {modelo}!")
            return completion.choices[0].message.content
        except Exception as e:
            print(f"[Aviso] O modelo {modelo} falhou. Tentando o próximo da lista...")
            
    raise Exception("Todos os modelos da Groq falharam.")

def baixar_videos_pexels(query="rave festival", quantidade=4):
    """Busca e baixa clipes na vertical (estilo TikTok) do Pexels totalmente de graça"""
    print(f"[Iniciando] Buscando vídeos no Pexels para o termo: '{query}'...")
    headers = {"Authorization": pexels_key}
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
        
        print(f"[Sucesso] {len(arquivos_baixados)} vídeos de fundo baixados!")
        return arquivos_baixados
    except Exception as e:
        print(f"[Erro] Falha ao conectar ou baixar do Pexels: {e}")
        return []

def editar_video_final(videos, audio_path, output_path="video_final.mp4"):
    """Junta os vídeos de fundo, insere o áudio e faz a renderização na nuvem"""
    print("\n[Passo 4] Iniciando a edição e montagem do vídeo com o MoviePy...")
    try:
        # Carrega o áudio gerado e verifica o seu tamanho
        audio_clip = AudioFileClip(audio_path)
        duracao_audio = audio_clip.duration
        print(f"Duração exata do áudio: {duracao_audio:.2f} segundos.")

        # Carrega todos os clipes de vídeo descarregados
        clips_video = [VideoFileClip(v) for v in videos]
        
        # Concatena os clipes um atrás do outro de forma suave
        video_concatenado = concatenate_videoclips(clips_video, method="compose")
        
        # Junta o áudio ao bloco de vídeo
        video_final = video_concatenado.set_audio(audio_clip)
        
        # Corta o excesso de vídeo para terminar exatamente junto com o áudio
        if video_final.duration > duracao_audio:
            video_final = video_final.subclip(0, duracao_audio)
            
        print("Renderizando o arquivo final 'video_final.mp4' na memória da nuvem...")
        # Executa a renderização otimizada para o ecossistema mobile
        video_final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None # Desativa logs extensos para poupar o console do GitHub
        )
        
        # Fecha os arquivos para libertar a memória RAM do servidor
        audio_clip.close()
        video_final.close()
        for c in clips_video:
            c.close()
            
        print(f"[Sucesso] Vídeo final editado e gerado: {output_path}")
        return True
    except Exception as e:
        print(f"[Erro na Edição] Falha ao montar o vídeo com o MoviePy: {e}")
        return False

def main():
    tema_do_video = "A história secreta por trás do surgimento da cultura Rave e do movimento Acid House"
    
    print(f"[Passo 1] Acionando a Groq para criar o roteiro...")
    try:
        roteiro = gerar_roteiro(tema_do_video)
        print("\n--- Roteiro Gerado ---")
        print(roteiro)
        print("----------------------\n")
        
        print("[Passo 2] Convertendo o texto em voz com o sistema da Microsoft...")
        asyncio.run(gerar_voz(roteiro))
        
        print("\n[Passo 3] Coletando imagens do front no Pexels...")
        # Aumentamos para 4 vídeos para garantir que cobrimos toda a duração do áudio
        videos_baixados = baixar_videos_pexels(query="electronic music festival", quantidade=4)
        
        if videos_baixados:
            # Junta tudo no editor robotizado
            editar_video_final(videos_baixados, "audio.mp3")
        else:
            print("[Erro] Falha no Passo 3. Interrompendo a montagem do vídeo.")
            
        print("\n[Fim] Script finalizado com sucesso na nuvem!")
        
    except Exception as err:
        print(f"\n[Erro Geral] {err}")
        exit(1)

if __name__ == "__main__":
    main()
