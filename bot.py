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

def limpar_roteiro_ia(texto_bruto):
    """Remove marcações estruturais e tags que a IA teima em colocar no texto"""
    texto_sem_markdown = texto_bruto.replace("**", "").replace("*", "").replace("#", "")
    
    linhas = texto_sem_markdown.split("\n")
    linhas_limpas = []
    
    tags_proibidas = ["gancho", "chamada", "introdução", "parágrafo", "roteiro", "narrador", "cena", "texto", "cta"]
    
    for linha in linhas:
        linha_limpa = linha.strip()
        linha_min = linha_limpa.lower()
        
        # Ignora linhas que sirvam apenas de títulos de blocos ou metatags
        if any(tag in linha_min for tag in tags_proibidas) and (len(linha_limpa) < 30 or ":" in linha_limpa):
            continue
            
        # Remove eventuais textos entre colchetes ou parênteses (direções de cena)
        if linha_limpa.startswith("[") or linha_limpa.startswith("("):
            continue
            
        if linha_limpa:
            linhas_limpas.append(linha_limpa)
            
    return " ".join(linhas_limpas)

async def gerar_voz(texto, arquivo_saida="audio.mp3"):
    """Transforma o texto limpo em voz digital de alta qualidade"""
    voz_selecionada = "pt-BR-AntonioNeural"
    communicate = edge_tts.Communicate(texto, voz_selecionada)
    await communicate.save(arquivo_saida)
    print(f"[Sucesso] Áudio gerado e salvo como: {arquivo_saida}")

def gerar_roteiro(tema):
    """Gera um roteiro magnético focado em retenção usando o Llama 3"""
    prompt_sistema = """
    Você é um roteirista de elite do TikTok focado no nicho de música eletrônica underground.
    Seu trabalho é transformar fatos históricos, curiosidades de DJs e segredos do front em vídeos virais magnéticos.

    ESTRUTURA DA NARRATIVA:
    1. GANCHO DE RETENÇÃO (0-5s): Comece com uma afirmação chocante, uma pergunta intrigante ou uma quebra de padrão direta. Proibido saudações (nada de 'Olá galera', 'Sejam bem-vindos').
    2. CONTEXTO RÍTMICO (5-45s): Escreva em frases curtas e diretas. Use termos do front (pista, linha de baixo, sintetizador, cabine, rave) de forma orgânica. Crie tensão e curiosidade.
    3. CHAMADA PARA AÇÃO DE ALTO ATRITO (45-60s): Termine com uma pergunta instigante ou polêmica que force o espectador a comentar e debater na publicação.

    REGRAS ESTRITAS DE FORMATO:
    - Retorne APENAS o texto corrido a ser lido.
    - É terminantemente proibido usar títulos como 'Gancho:', 'Narrador:', ou usar marcas de cena como '(fundo musical)'.
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
    Você é um diretor de arte de vídeos curtos. Analise o roteiro em português fornecido e crie exatamente 4 termos de busca diferentes em inglês para encontrar vídeos verticais de cobertura (b-roll) no Pexels.
    Os termos devem ser puramente visuais, focados em música eletrônica, raves, DJs e estética de luzes.

    FORMATO DA RESPOSTA:
    Retorne APENAS os 4 termos separados por vírgula em uma única linha. Não inclua números, explicações ou introduções.
    Exemplo de retorno esperado: berlin techno club, dj mixing vinyl, rave strobe lights, crowd dancing portrait
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
        # Fallback caso a IA não obedeça o formato de lista por vírgula
        if len(lista_termos) < 2:
            return ["underground rave crowd", "techno dj lighting", "electronic music festival", "dancing club portrait"]
        return lista_termos[:4]
    except Exception:
        return ["underground rave crowd", "techno dj lighting", "electronic music festival", "dancing club portrait"]

def baixar_videos_pexels_dinamico(queries):
    """Baixa um clipe vertical do Pexels para cada um dos termos dinâmicos gerados pela IA"""
    print(
