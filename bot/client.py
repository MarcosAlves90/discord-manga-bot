"""
Cliente Discord principal com comandos e gerenciamento de estado
"""
import discord
import asyncio
from discord import app_commands
from datetime import datetime, timedelta
from database.manga_db import MangaDatabase
from api.jikan_api import JikanAPI
from bot.commands import Commands
from utils.constants import (
    LIMITE_MANGA_POR_HORA, LIMITE_MANGA_RESET,
    LIMITE_PEGAR_MANGA, LIMITE_PEGAR_RESET,
    MANGA_EXPIRATION_TIME, PENDENTES_CLEANUP_TIME, 
    PENDENTES_CHECK_INTERVAL
)
from utils.logger import setup_logger

logger = setup_logger()

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

class DiscordBot(discord.Client):
    """Cliente Discord principal com comandos e gerenciamento de estado"""
    
    def __init__(self):
        super().__init__(intents=intents)
        
        self.db = MangaDatabase()
        self.jikan = JikanAPI()
        
        self.mangas_pendentes = {} 
        self.rl_comandos_por_usuario = {}
        self.pegar_comandos_por_usuario = {}
        self.tree = app_commands.CommandTree(self)
        
        self.commands = Commands(self)
        self._keep_alive_server = None
    
    async def setup_hook(self):
        """Configuração inicial ao iniciar o bot"""
        await self.db.init_db()
        
        self.bg_task = self.loop.create_task(self.limpar_mangas_pendentes())
        self.rl_cleanup_task = self.loop.create_task(self.limpar_registros_comando_rl())
        self.pegar_cleanup_task = self.loop.create_task(self.limpar_registros_pegar_manga())
        await self.commands.setup_commands()
        await self.tree.sync()
    
    def verificar_limite_rl(self, user_id):
        """Verifica se o usuário atingiu o limite de mangás por hora"""
        user_id_str = str(user_id)
        agora = datetime.now()
        
        registros = self.rl_comandos_por_usuario.get(user_id_str, [])
        
        hora_atras = agora - timedelta(seconds=LIMITE_MANGA_RESET)
        registros_recentes = [ts for ts in registros if ts > hora_atras]
        
        self.rl_comandos_por_usuario[user_id_str] = registros_recentes
        
        if len(registros_recentes) >= LIMITE_MANGA_POR_HORA:
            return False, 0, registros_recentes
        
        mangas_restantes = LIMITE_MANGA_POR_HORA - len(registros_recentes)
        return True, mangas_restantes, registros_recentes
    
    def verificar_limite_pegar(self, user_id):
        """Verifica se o usuário pode pegar um mangá (limite de 1 a cada 5 horas)"""
        user_id_str = str(user_id)
        agora = datetime.now()
        
        registros = self.pegar_comandos_por_usuario.get(user_id_str, [])
        
        cinco_horas_atras = agora - timedelta(seconds=LIMITE_PEGAR_RESET)
        registros_recentes = [ts for ts in registros if ts > cinco_horas_atras]
        
        self.pegar_comandos_por_usuario[user_id_str] = registros_recentes
        
        if len(registros_recentes) >= LIMITE_PEGAR_MANGA:
            return False, registros_recentes
        
        return True, registros_recentes
    
    async def limpar_registros_comando_rl(self):
        """Limpa registros antigos do comando RL"""
        while not self.is_closed():
            try:
                agora = datetime.now()
                hora_atras = agora - timedelta(seconds=LIMITE_MANGA_RESET)
                
                for user_id in list(self.rl_comandos_por_usuario.keys()):
                    registros = self.rl_comandos_por_usuario[user_id]
                    registros_recentes = [ts for ts in registros if ts > hora_atras]
                    
                    if not registros_recentes:
                        del self.rl_comandos_por_usuario[user_id]
                    else:
                        self.rl_comandos_por_usuario[user_id] = registros_recentes
                
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Erro na limpeza de registros de comando RL: {e}")
                await asyncio.sleep(300)
    
    async def limpar_registros_pegar_manga(self):
        """Limpa registros antigos de pegar mangás"""
        while not self.is_closed():
            try:
                agora = datetime.now()
                cinco_horas_atras = agora - timedelta(seconds=LIMITE_PEGAR_RESET)
                
                for user_id in list(self.pegar_comandos_por_usuario.keys()):
                    registros = self.pegar_comandos_por_usuario[user_id]
                    registros_recentes = [ts for ts in registros if ts > cinco_horas_atras]
                    
                    if not registros_recentes:
                        del self.pegar_comandos_por_usuario[user_id]
                    else:
                        self.pegar_comandos_por_usuario[user_id] = registros_recentes
                
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Erro na limpeza de registros de pegar mangás: {e}")
                await asyncio.sleep(300)
    
    async def expirar_manga(self, message_id, channel_id):
        """Marca um mangá como expirado após o tempo definido"""
        await asyncio.sleep(MANGA_EXPIRATION_TIME)
        
        if message_id in self.mangas_pendentes:
            try:
                channel = self.get_channel(channel_id)
                if not channel:
                    return
                    
                message = await channel.fetch_message(message_id)
                if not message or not message.embeds:
                    return
                    
                embed = message.embeds[0]
                if embed.color and embed.color.value == discord.Color.green().value:
                    embed.color = discord.Color.light_grey()
                    embed.set_footer(text="Tempo esgotado")
                    await message.edit(embed=embed)
                    
                self.mangas_pendentes[message_id]["expirado"] = True
            except Exception as e:
                logger.error(f"Erro ao expirar mangá: {e}")
    
    async def limpar_mangas_pendentes(self):
        """Tarefa em background para limpar mangás pendentes antigos"""
        while not self.is_closed():
            try:
                agora = datetime.now()
                manga_ids_para_remover = []
                
                for message_id, manga_data in self.mangas_pendentes.items():
                    data_manga = datetime.fromisoformat(manga_data["timestamp"])
                    if (agora - data_manga).total_seconds() > PENDENTES_CLEANUP_TIME:
                        manga_ids_para_remover.append(message_id)
                
                for message_id in manga_ids_para_remover:
                    del self.mangas_pendentes[message_id]
                
                if len(self.mangas_pendentes) > 1000:
                    logger.warning(f"Limite de mangas pendentes atingido ({len(self.mangas_pendentes)}). Removendo os mais antigos.")
                    
                    sorted_mangas = sorted(
                        self.mangas_pendentes.items(),
                        key=lambda x: datetime.fromisoformat(x[1]["timestamp"])
                    )
                    
                    for message_id, _ in sorted_mangas[:200]:
                        del self.mangas_pendentes[message_id]
                    
                    logger.info(f"Remoção concluída. Tamanho atual: {len(self.mangas_pendentes)}")
                
                if manga_ids_para_remover:
                    logger.info(f"Removidos {len(manga_ids_para_remover)} mangás pendentes antigos")
                
                await asyncio.sleep(PENDENTES_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Erro na limpeza de mangás pendentes: {e}")
                await asyncio.sleep(300)
    
    async def on_raw_reaction_add(self, payload):
        """Handler para reações adicionadas nas mensagens"""
        if payload.user_id == self.user.id:
            return
                
        if payload.message_id in self.mangas_pendentes:
            manga_data = self.mangas_pendentes[payload.message_id]
            channel = self.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = self.get_user(payload.user_id) or await self.fetch_user(payload.user_id)
            
            if message.embeds and message.embeds[0].color:
                is_expired = (message.embeds[0].color.value == discord.Color.light_grey().value or
                            message.embeds[0].color.value == discord.Color.red().value or
                            manga_data.get("expirado", False))
                
                if is_expired:
                    try:
                        await message.remove_reaction(payload.emoji, user)
                    except:
                        pass
                    return
                    
            pode_pegar, registros_pegar = self.verificar_limite_pegar(payload.user_id)
            
            if not pode_pegar:
                try:
                    await message.remove_reaction(payload.emoji, user)
                    
                    agora = datetime.now()
                    ultimo_registro = max(registros_pegar)
                    tempo_restante = ultimo_registro + timedelta(seconds=LIMITE_PEGAR_RESET) - agora
                    horas = int(tempo_restante.total_seconds() // 3600)
                    minutos = int((tempo_restante.total_seconds() % 3600) // 60)
                    
                    await channel.send(
                        f"{user.mention}, você já pegou um mangá nas últimas 5 horas! "
                        f"Tente novamente em {horas} horas e {minutos} minutos.",
                        delete_after=10
                    )
                except:
                    pass
                return
                
            try:
                await self.db.registrar_manga(payload.user_id, manga_data["manga_id"])
                
                user_id_str = str(payload.user_id)
                if user_id_str not in self.pegar_comandos_por_usuario:
                    self.pegar_comandos_por_usuario[user_id_str] = []
                self.pegar_comandos_por_usuario[user_id_str].append(datetime.now())
                
                embed = message.embeds[0]
                embed.color = discord.Color.red()
                embed.set_footer(text=f"Mangá pego por {user.display_name} com {payload.emoji}")
                
                await message.edit(embed=embed)
                
                del self.mangas_pendentes[payload.message_id]
                
                await channel.send(f"🎉 {user.mention} pegou o mangá **{manga_data['title']}** com {payload.emoji}!")
            except Exception as e:
                logger.error(f"Erro ao processar reação: {e}")
    
    async def on_ready(self):
        """Evento disparado quando o bot está pronto"""
        logger.info(f'Bot conectado como {self.user}')
    
    async def close(self):
        """Sobrescrevendo método close para limpar recursos"""
        await self.jikan.close()
        await super().close()
