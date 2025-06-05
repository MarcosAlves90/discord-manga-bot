"""
Ponto de entrada principal para o bot Discord TTS
"""
from bot.client import DiscordBot
from utils.constants import TOKEN
from utils.logger import setup_logger

logger = setup_logger()

def main():
    """Função principal para iniciar o bot"""
    bot = DiscordBot()
    try:
        logger.info("Iniciando o bot Discord...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot desligado pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")

if __name__ == "__main__":
    main()
