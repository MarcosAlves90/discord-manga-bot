"""
Ponto de entrada principal para o bot Discord Manga
Inclui sistema de keep-alive para manter o bot online no Render
"""
import asyncio
import os
from bot.client import DiscordBot
from utils.constants import TOKEN
from utils.logger import setup_logger
from utils.keep_alive import KeepAliveServer, AutoPing

logger = setup_logger()

async def main():
    """Função principal assíncrona para iniciar o bot e servidor web"""
    bot = None
    keep_alive_server = None
    auto_ping = None
    
    try:        # Cria as instâncias
        bot = DiscordBot()
        keep_alive_server = KeepAliveServer(bot)
        auto_ping = AutoPing()
        
        # Define a referência do servidor no bot
        bot._keep_alive_server = keep_alive_server
        
        # Inicia o servidor web primeiro
        logger.info("🌐 Iniciando servidor keep-alive...")
        server_started = await keep_alive_server.start_server()
        
        if not server_started:
            logger.error("❌ Falha ao iniciar servidor keep-alive")
            return
        
        # Inicia o sistema de auto-ping
        logger.info("🔄 Iniciando sistema de auto-ping...")
        auto_ping.start_ping()
        
        # Inicia o bot Discord
        logger.info("🤖 Iniciando bot Discord...")
        await bot.start(TOKEN)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot desligado pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar o bot: {e}")
        raise
    finally:
        # Limpeza
        logger.info("🧹 Iniciando limpeza...")
        
        if auto_ping:
            auto_ping.stop_ping()
        
        if bot and not bot.is_closed():
            await bot.close()
        
        if keep_alive_server:
            await keep_alive_server.stop_server()
        
        logger.info("✅ Limpeza concluída")

def sync_main():
    """Função síncrona para compatibilidade"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Aplicação encerrada pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    sync_main()
