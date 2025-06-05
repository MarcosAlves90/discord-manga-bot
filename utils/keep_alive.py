"""
Sistema de Keep-Alive para manter o bot online no Render
Cria um servidor web interno que recebe pings para evitar que o serviço seja suspenso
"""
import asyncio
import aiohttp
from aiohttp import web
import os
import logging
from datetime import datetime
from discord.ext import tasks

logger = logging.getLogger(__name__)

class KeepAliveServer:
    """Servidor web para receber pings e manter o serviço ativo"""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.app = None
        self.runner = None
        self.site = None
        self.start_time = datetime.now()
        self.ping_count = 0
        
    async def handle_root(self, request):
        """Endpoint raiz com informações básicas"""
        uptime = datetime.now() - self.start_time
        bot_status = "Online" if self.bot and not self.bot.is_closed() else "Offline"
        
        response_text = f"""
        🤖 Discord Manga Bot está rodando!
        ⏰ Uptime: {uptime}
        📊 Status do Bot: {bot_status}
        🔄 Pings recebidos: {self.ping_count}
        🌐 Serviço ativo desde: {self.start_time.strftime('%d/%m/%Y %H:%M:%S')}
        """.strip()
        
        return web.Response(text=response_text, status=200)
    
    async def handle_ping(self, request):
        """Endpoint de ping para keep-alive"""
        self.ping_count += 1
        logger.info(f"✅ Ping recebido #{self.ping_count}")
        
        bot_guilds = len(self.bot.guilds) if self.bot and hasattr(self.bot, 'guilds') else 0
        
        return web.Response(
            text=f"Bot está vivo! 🤖 (Servidores: {bot_guilds})", 
            status=200
        )
    
    async def handle_health(self, request):
        """Endpoint de health check"""
        if self.bot and not self.bot.is_closed():
            return web.Response(text="OK", status=200)
        else:
            return web.Response(text="Bot Offline", status=503)
    
    async def handle_stats(self, request):
        """Endpoint com estatísticas do bot"""
        if not self.bot:
            return web.Response(text="Bot não disponível", status=503)
        
        uptime = datetime.now() - self.start_time
        bot_guilds = len(self.bot.guilds) if hasattr(self.bot, 'guilds') else 0
        bot_users = len(self.bot.users) if hasattr(self.bot, 'users') else 0
        
        stats = {
            "status": "online" if not self.bot.is_closed() else "offline",
            "uptime_seconds": int(uptime.total_seconds()),
            "guilds": bot_guilds,
            "users": bot_users,
            "ping_count": self.ping_count,
            "start_time": self.start_time.isoformat()
        }
        
        return web.json_response(stats)
    
    async def start_server(self):
        """Inicia o servidor web"""
        try:
            self.app = web.Application()
            
            # Rotas
            self.app.router.add_get('/', self.handle_root)
            self.app.router.add_get('/ping', self.handle_ping)
            self.app.router.add_get('/health', self.handle_health)
            self.app.router.add_get('/stats', self.handle_stats)
            
            # Configuração da porta
            port = int(os.environ.get('PORT', 8000))
            
            # Inicia o servidor
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, '0.0.0.0', port)
            await self.site.start()
            
            logger.info(f"🌐 Servidor keep-alive iniciado na porta {port}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar servidor keep-alive: {e}")
            return False
    
    async def stop_server(self):
        """Para o servidor web"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            logger.info("🛑 Servidor keep-alive parado")
        except Exception as e:
            logger.error(f"❌ Erro ao parar servidor: {e}")


class AutoPing:
    """Sistema de auto-ping para manter o serviço ativo"""
    
    def __init__(self):
        self.ping_task = None
        self.ping_url = self._get_ping_url()
        
    def _get_ping_url(self):
        """Obtém a URL para fazer ping"""
        # Tenta pegar a URL do Render primeiro
        base_url = os.environ.get('RENDER_EXTERNAL_URL')
        
        if not base_url:
            # Se não tiver, usa URL local
            port = os.environ.get('PORT', '8000')
            base_url = f"http://localhost:{port}"
        
        return f"{base_url}/ping"
    
    @tasks.loop(minutes=13)  # Ping a cada 13 minutos (Render desativa após 15 min)
    async def keep_alive_ping(self):
        """Faz ping no próprio serviço para mantê-lo ativo"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.ping_url) as response:
                    if response.status == 200:
                        text = await response.text()
                        logger.info(f"✅ Keep-alive ping bem-sucedido: {response.status}")
                    else:
                        logger.warning(f"⚠️ Keep-alive ping com status: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.warning("⏰ Timeout no keep-alive ping")
        except aiohttp.ClientError as e:
            logger.warning(f"🌐 Erro de conexão no keep-alive ping: {e}")
        except Exception as e:
            logger.error(f"❌ Erro inesperado no keep-alive ping: {e}")
    
    @keep_alive_ping.error
    async def keep_alive_error(self, error):
        """Trata erros da task de keep-alive"""
        logger.error(f"❌ Erro na task keep-alive: {error}")
        
        # Tenta reiniciar a task após 5 minutos
        await asyncio.sleep(300)
        if not self.keep_alive_ping.is_running():
            try:
                self.keep_alive_ping.restart()
                logger.info("🔄 Task keep-alive reiniciada")
            except Exception as e:
                logger.error(f"❌ Erro ao reiniciar keep-alive: {e}")
    
    def start_ping(self):
        """Inicia o sistema de auto-ping"""
        if not self.keep_alive_ping.is_running():
            self.keep_alive_ping.start()
            logger.info("🔄 Sistema de keep-alive iniciado")
    
    def stop_ping(self):
        """Para o sistema de auto-ping"""
        if self.keep_alive_ping.is_running():
            self.keep_alive_ping.cancel()
            logger.info("🛑 Sistema de keep-alive parado")
