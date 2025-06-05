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

def calcular_criptogenes(popularidade=None, score=None, members=None, favorites=None, status=None, manga_data=None):
    """
    Sistema de Criptogenes "Lendário" - Extremamente difícil chegar a 1000
    
    Args:
        popularidade: Ranking de popularidade (menor = melhor)
        score: Pontuação 0-10
        members: Número de membros que adicionaram 
        favorites: Número de favoritos
        status: Status de publicação
        manga_data: Dados completos do manga (opcional, usado se parâmetros individuais não fornecidos)
    
    Returns:
        float: Valor em Criptogenes (1-1000, praticamente impossível chegar a 1000)
    """
    import math
    
    # Se manga_data for fornecido, extrair parâmetros
    if manga_data:
        popularidade = manga_data.get('popularity') if popularidade is None else popularidade
        score = manga_data.get('score') if score is None else score
        members = manga_data.get('members') if members is None else members
        favorites = manga_data.get('favorites') if favorites is None else favorites
        status = manga_data.get('status') if status is None else status
    
    # === VALOR BASE DO SCORE (0-100 pontos) ===
    if not score or score <= 0:
        valor_base = 10  # Mangás sem score ficam muito baixos
    else:
        valor_base = (score / 10.0) * 100
    
    # === MULTIPLICADOR DE POPULARIDADE (Sistema Lendário) ===
    mult_popularidade = 1.0
    if popularidade and popularidade > 0:
        if popularidade <= 10:
            mult_popularidade = 8.5  # Top 10 - Lendários
        elif popularidade <= 50:
            mult_popularidade = 6.0  # Top 50 - Épicos
        elif popularidade <= 100:
            mult_popularidade = 4.0  # Top 100 - Raros
        elif popularidade <= 500:
            mult_popularidade = 2.5  # Top 500 - Incomuns
        elif popularidade <= 1000:
            mult_popularidade = 1.8  # Top 1000 - Comuns+
        elif popularidade <= 5000:
            mult_popularidade = 1.3  # Top 5000 - Comuns
        else:
            mult_popularidade = 1.0  # Resto - Básicos
    
    # === BÔNUS DE MEMBROS (Logarítmico) ===
    bonus_membros = 0
    if members and members > 0:
        # Logarítmo para evitar valores explosivos
        # Max teórico: ~45 pontos (para 1M+ membros)
        bonus_membros = min(45, math.log10(max(1, members / 1000)) * 15)
        bonus_membros = max(0, bonus_membros)
    
    # === BÔNUS DE FAVORITOS (Logarítmico) ===
    bonus_favoritos = 0
    if favorites and favorites > 0:
        # Favoritos são mais raros, então valem mais
        # Max teórico: ~50 pontos (para 100K+ favoritos)
        bonus_favoritos = min(50, math.log10(max(1, favorites / 100)) * 20)
        bonus_favoritos = max(0, bonus_favoritos)
    
    # === MULTIPLICADOR DE STATUS ===
    mult_status = 1.0
    if status:
        status_lower = status.lower()
        if 'publishing' in status_lower or 'ongoing' in status_lower:
            mult_status = 1.1  # Mangás em publicação têm leve bônus
        elif 'finished' in status_lower or 'completed' in status_lower:
            mult_status = 1.0  # Mangás completos são neutros
        elif 'hiatus' in status_lower or 'discontinued' in status_lower:
            mult_status = 0.8  # Mangás pausados/cancelados são penalizados
    
    # === CÁLCULO INTERMEDIÁRIO ===
    valor_intermediario = (valor_base + bonus_membros + bonus_favoritos) * mult_popularidade * mult_status
    
    # === CURVA LOGARÍTMICA FINAL - O SEGREDO DO SISTEMA LENDÁRIO ===
    # Esta fórmula garante que é EXTREMAMENTE difícil chegar perto de 1000
    # Mesmo valores intermediários altíssimos resultam em valores finais menores
    valor_final = 1000 * (1 - math.exp(-valor_intermediario / 400))
    
    # Garantir limites absolutos
    valor_final = max(1, min(999.99, valor_final))
    
    return round(valor_final, 2)
