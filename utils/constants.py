"""
Constantes utilizadas pelo bot Discord TTS
"""
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("ERRO: Variável de ambiente DISCORD_TOKEN não encontrada!")
    print("Crie um arquivo .env com DISCORD_TOKEN=seu_token_aqui")
    sys.exit(1)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERRO: Variável de ambiente DATABASE_URL não encontrada!")
    print("Crie um arquivo .env com DATABASE_URL=sua_url_do_postgresql")
    sys.exit(1)

API_BASE = os.getenv('JIKAN_API_BASE', "https://api.jikan.moe/v4")

MANGA_EXPIRATION_TIME = 30
PENDENTES_CLEANUP_TIME = 10800 
PENDENTES_CHECK_INTERVAL = 1800

LIMITE_MANGA_POR_HORA = 10
LIMITE_MANGA_RESET = 3600

# Configurações para pegar mangás (separado do comando /rl)
LIMITE_PEGAR_MANGA = 1
LIMITE_PEGAR_RESET = 18000  # 5 horas

def calcular_criptogenes(popularidade, score):
    """
    Calcula o valor em Criptogenes baseado na popularidade e score do mangá
    
    Args:
        popularidade: Valor de popularidade do mangá (menor = mais popular)
        score: Pontuação do mangá (0-10)
    
    Returns:
        float: Valor em Criptogenes (entre 10-500) com duas casas decimais
    """

    if popularidade <= 0:
        pop_valor = 200
    else:
        import math
        pop_normalizado = max(1, min(popularidade, 50000)) / 50000
        pop_log = -math.log(pop_normalizado, 10)
        pop_valor = 20 + (pop_log * 65)
        
    score_bonus = 0
    if score and score > 0:
        import random
        score_base = (score / 10) * 80
        variacao = random.uniform(0.85, 1.15)
        score_bonus = score_base * variacao
        
    valor = pop_valor + score_bonus
    
    import random
    valor += random.uniform(-5, 5)
    
    valor = round(valor, 2)
    
    return max(10, min(500, valor))