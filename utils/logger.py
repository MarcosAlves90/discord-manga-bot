"""
Configuração de logging para o bot Discord
"""
import logging

def setup_logger():
    """Configuração de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('discord-bot')
