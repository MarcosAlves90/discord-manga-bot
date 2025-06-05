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

MANGA_EXPIRATION_TIME = 60
PENDENTES_CLEANUP_TIME = 10800 
PENDENTES_CHECK_INTERVAL = 1800

LIMITE_MANGA_POR_HORA = 10
LIMITE_MANGA_RESET = 3600

LIMITE_PEGAR_MANGA = 1
LIMITE_PEGAR_RESET = 18000  # 5 horas

def calcular_criptogenes(popularidade, score):
    """
    Calcula o valor em Criptogenes baseado na popularidade e score do mangá
    Sistema baseado em capitalização de mercado e avaliação fundamentalista
    
    Args:
        popularidade: Ranking de popularidade do mangá (menor = mais popular)
        score: Pontuação do mangá (0-10)
    
    Returns:
        float: Valor em Criptogenes (entre 5-1000) com duas casas decimais
    """
    import math
    
    # Base mínima para todos os mangás
    valor_base = 5
    
    # === CÁLCULO DA CAPITALIZAÇÃO (baseado na popularidade) ===
    if popularidade <= 0 or popularidade > 100000:
        # Mangás sem ranking ou muito baixos
        cap_valor = 10
    else:
        # Fórmula exponencial inversa - quanto menor o ranking, maior o valor
        # Top 10: ~800-900 pontos, Top 100: ~400-600, Top 1000: ~200-300, etc.
        exponente = -math.log10(popularidade / 100000) * 2.5
        cap_valor = min(900, 50 * math.pow(2, exponente))
    
    # === CÁLCULO DO SCORE FUNDAMENTALISTA ===
    score_multiplicador = 1.0
    if score and score > 0:
        # Score vira multiplicador, não soma
        # Score 9-10: 1.8-2.0x, Score 7-8: 1.3-1.6x, Score 5-6: 1.0-1.2x
        if score >= 9.0:
            score_multiplicador = 1.8 + (score - 9.0) * 0.2
        elif score >= 8.0:
            score_multiplicador = 1.6 + (score - 8.0) * 0.2
        elif score >= 7.0:
            score_multiplicador = 1.3 + (score - 7.0) * 0.3
        elif score >= 6.0:
            score_multiplicador = 1.1 + (score - 6.0) * 0.2
        elif score >= 5.0:
            score_multiplicador = 1.0 + (score - 5.0) * 0.1
        else:
            # Scores baixos penalizam
            score_multiplicador = max(0.3, score / 5.0)
    
    # === VOLATILIDADE DE MERCADO (reduzida) ===
    # Volatilidade menor para mangás mais valiosos (como Bitcoin vs altcoins)
    if cap_valor > 500:
        volatilidade = 0.02  # ±2% para "blue chips"
    elif cap_valor > 200:
        volatilidade = 0.05  # ±5% para mid caps
    else:
        volatilidade = 0.08  # ±8% para small caps
    
    import random
    flutuacao = random.uniform(1 - volatilidade, 1 + volatilidade)
    
    # === CÁLCULO FINAL ===
    valor_final = valor_base + (cap_valor * score_multiplicador * flutuacao)
    
    # Limitadores finais
    valor_final = round(max(5, min(1000, valor_final)), 2)
    
    return valor_final
