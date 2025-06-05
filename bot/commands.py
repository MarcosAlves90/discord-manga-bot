"""
Comandos do bot Discord
"""
import discord
import asyncio
import random
from datetime import datetime, timedelta
from utils.constants import (
    LIMITE_MANGA_POR_HORA, LIMITE_MANGA_RESET,
    LIMITE_PEGAR_MANGA, LIMITE_PEGAR_RESET,
    MANGA_EXPIRATION_TIME
)
from utils.logger import setup_logger
from utils.metrics import metrics

logger = setup_logger()

class Commands:
    """Classe para gerenciar comandos do bot"""
    
    def __init__(self, client):
        """
        Inicializa os comandos do bot
        
        Args:
            client: Instância da classe DiscordBot
        """
        self.client = client
    
    async def setup_commands(self):
        """Configura todos os comandos slash"""
        
        @self.client.tree.command(name="rl", description="Receba um mangá aleatório! Reaja para pegá-lo!")
        async def manga_aleatorio(interaction: discord.Interaction):
            metrics.log_command("rl", user_id=interaction.user.id, guild_id=interaction.guild_id if interaction.guild else None)
            await self._cmd_manga_aleatorio(interaction)
            
        @self.client.tree.command(name="meusmangas", description="Veja a lista de mangás que você já recebeu!")
        async def meus_mangas(interaction: discord.Interaction):
            metrics.log_command("meusmangas", user_id=interaction.user.id, guild_id=interaction.guild_id if interaction.guild else None)
            await self._cmd_meus_mangas(interaction)
                
        @self.client.tree.command(name="ranking", description="Veja quem pegou mais mangás no servidor!")
        async def ranking_mangas(interaction: discord.Interaction):
            metrics.log_command("ranking", user_id=interaction.user.id, guild_id=interaction.guild_id if interaction.guild else None)
            await self._cmd_ranking(interaction)
                
        @self.client.tree.command(name="ajuda", description="Exibe a ajuda detalhada sobre o bot e seus comandos")
        async def ajuda(interaction: discord.Interaction):
            metrics.log_command("ajuda", user_id=interaction.user.id, guild_id=interaction.guild_id if interaction.guild else None)
            await self._cmd_ajuda(interaction)
                
        @self.client.tree.command(name="estatisticas", description="Exibe estatísticas de uso do bot")
        async def estatisticas(interaction: discord.Interaction):
            metrics.log_command("estatisticas", user_id=interaction.user.id, guild_id=interaction.guild_id if interaction.guild else None)
            await self._cmd_estatisticas(interaction)
    
    async def _cmd_manga_aleatorio(self, interaction: discord.Interaction):
        """Implementação do comando /rl"""
        if not interaction.guild:
            await interaction.response.send_message(
                "Este comando só pode ser usado em servidores, não em mensagens privadas.",
                ephemeral=True
            )
            return

        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if not (permissions.send_messages and permissions.embed_links):
            await interaction.response.send_message(
                "Não tenho permissões suficientes neste canal. Preciso poder enviar mensagens e embeds.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        try:
            user_id = interaction.user.id
            pode_pegar, mangas_restantes, registros = self.client.verificar_limite_rl(user_id)
            
            if not pode_pegar:
                agora = datetime.now()
                primeiro_registro = min(registros)
                tempo_restante = primeiro_registro + timedelta(seconds=LIMITE_MANGA_RESET) - agora
                minutos = int(tempo_restante.total_seconds() // 60)
                segundos = int(tempo_restante.total_seconds() % 60)
                
                embed = discord.Embed(
                    title="Limite de Mangás Atingido",
                    description=f"Você já recebeu {LIMITE_MANGA_POR_HORA} mangás na última hora!\nTente novamente em {minutos} minutos e {segundos} segundos.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    manga = await self.client.jikan.obter_manga_aleatorio()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Falha ao obter mangá após {max_retries} tentativas: {e}")
                        await interaction.followup.send(
                            "Desculpe, não foi possível obter um mangá aleatório neste momento. Tente novamente mais tarde.",
                            ephemeral=True
                        )
                        return
                    await asyncio.sleep(1)
            
            manga_id, titulo = manga.get("mal_id"), manga.get("title")
            if not manga_id or not titulo:
                await interaction.followup.send(
                    "Recebi dados inválidos da API de mangás. Por favor, tente novamente.",
                    ephemeral=True
                )
                metrics.log_error("invalid_manga_data")
                return
            
            titulo = discord.utils.escape_markdown(titulo)
            titulo = titulo[:256]
            
            imagens = manga.get("images", {}).get("jpg", {})
            imagem = imagens.get("large_image_url") or imagens.get("image_url")
            
            sinopse = manga.get("synopsis") or "Sem sinopse disponível."
            sinopse = discord.utils.escape_markdown(sinopse)
            sinopse = sinopse[:4000]
            
            url_manga = manga.get("url") or ""
            if url_manga and not url_manga.startswith("https://myanimelist.net/"):
                url_manga = f"https://myanimelist.net/manga/{manga_id}"
            from utils.constants import calcular_criptogenes
            popularidade = manga.get("popularity", 0)
            score = manga.get("score", 0)
            members = manga.get("members", 0)
            favorites = manga.get("favorites", 0)
            status = manga.get("status", "")
            criptogenes = calcular_criptogenes(
                popularidade=popularidade,
                score=score, 
                members=members,
                favorites=favorites,
                status=status
            )
            
            embed = discord.Embed(
                title=titulo, 
                description=f"{sinopse}\n\n🧬 **Criptogenes:** {criptogenes}",
                color=discord.Color.green()
            )
            if url_manga:
                embed.url = url_manga
            if imagem:
                embed.set_image(url=imagem)
            
            footer_text = "Reaja com qualquer emoji para pegar este mangá!"
            if mangas_restantes <= 2:
                footer_text = f"ATENÇÃO! Este é um dos seus últimos {mangas_restantes} mangás disponíveis na próxima hora! " + footer_text
            
            embed.set_footer(text=footer_text)
            
            message = await interaction.followup.send(embed=embed)
            
            self.client.mangas_pendentes[message.id] = {
                "manga_id": manga_id,
                "title": titulo,
                "timestamp": datetime.now().isoformat(),
                "expirado": False
            }
            
            user_id_str = str(user_id)
            if user_id_str not in self.client.rl_comandos_por_usuario:
                self.client.rl_comandos_por_usuario[user_id_str] = []
            self.client.rl_comandos_por_usuario[user_id_str].append(datetime.now())
            
            emojis_sugestao = ["👍", "❤️", "😂", "🔥", "🥰", "👀", "🎮", "📚", "🎯", "✨"]
            emoji_sugerido = random.choice(emojis_sugestao)
            await message.add_reaction(emoji_sugerido)
            
            self.client.loop.create_task(self.client.expirar_manga(message.id, interaction.channel_id))
            
        except Exception as e:
            logger.error(f"Erro ao buscar mangá aleatório: {e}")
            await interaction.followup.send(f"Erro ao buscar mangá: {e}")
            
    async def _cmd_meus_mangas(self, interaction: discord.Interaction):
        """Implementação do comando /meusmangas"""
        await interaction.response.defer()
        try:
            usuario_id = str(interaction.user.id)
            manga_ids = await self.client.db.obter_mangas_usuario(usuario_id)
            
            if not manga_ids:
                await interaction.followup.send("Você ainda não recebeu nenhum mangá! Use /rl para pegar um aleatório.")
                return
            
            mangas = []
            for manga_id in manga_ids:
                info = await self.client.jikan.fetch_manga_info(manga_id, return_full_data=True)
                mangas.append(info)
            
            from views.pagination import MangaPaginationView
            view = MangaPaginationView(mangas, interaction.user.display_name)
            embed = await view.generate_embed()            
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Erro ao buscar mangás do usuário: {e}")
            await interaction.followup.send(f"Erro ao buscar seus mangás: {e}")
    
    async def _cmd_ranking(self, interaction: discord.Interaction):
        """Implementação do comando /ranking"""
        await interaction.response.defer()
        try:
            resultados = await self.client.db.obter_ranking()
            
            if not resultados:
                await interaction.followup.send("Ainda não há usuários no ranking de mangás!")
                return
            
            embed = discord.Embed(
                title="🏆 Ranking de Colecionadores de Mangá",
                description="Os usuários que mais pegaram mangás diferentes!",
                color=discord.Color.gold()
            )
            
            medalhas = ["🥇", "🥈", "🥉"]
            for i, (usuario_id, total) in enumerate(resultados):
                try:
                    usuario = await self.client.fetch_user(int(usuario_id))
                    nome = usuario.display_name
                except:
                    nome = f"Usuário ID {usuario_id}"
                
                emoji = medalhas[i] if i < 3 else "🏅"
                
                embed.add_field(
                    name=f"{emoji} {i+1}º Lugar",
                    value=f"**{nome}** - {total} mangás",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Erro ao buscar ranking: {e}")
            await interaction.followup.send(f"Erro ao buscar o ranking: {e}")
    
    async def _cmd_ajuda(self, interaction: discord.Interaction):
        """Implementação do comando /ajuda"""
        embed = discord.Embed(
            title="📚 Ajuda do Bot de Mangás",
            description="Este bot permite descobrir e coletar mangás aleatórios! Abaixo estão os comandos disponíveis e como usá-los:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📖 `/rl`", 
            value="Gera um mangá aleatório para você ou outros usuários.\n"
                f"**Limite de rolagem:** {LIMITE_MANGA_POR_HORA} mangás por hora.\n"
                f"**Limite para pegar:** {LIMITE_PEGAR_MANGA} mangá a cada {LIMITE_PEGAR_RESET//3600} horas.\n"
                f"**Tempo de expiração:** {MANGA_EXPIRATION_TIME} segundos para reagir e coletar.", 
            inline=False
        )
        
        embed.add_field(
            name="📑 `/meusmangas`", 
            value="Exibe uma lista paginada de todos os mangás que você já coletou, com links para suas páginas no MyAnimeList.",
            inline=False
        )
        
        embed.add_field(
            name="🏆 `/ranking`", 
            value="Mostra o ranking dos usuários que mais coletaram mangás únicos no servidor.",
            inline=False
        )
        
        embed.add_field(
            name="📊 `/estatisticas`", 
            value="Exibe estatísticas sobre o uso do bot, como tempo online, mangás distribuídos, etc.",
            inline=False
        )        
        embed.add_field(
            name="🧬 Sistema de Criptogenes Lendário:",
            value="Cada mangá possui um valor baseado em múltiplos fatores:\n"
                "- **Score**: Pontuação do manga (0-10)\n"
                "- **Popularidade**: Ranking no MyAnimeList (quanto menor, melhor)\n" 
                "- **Membros**: Quantos usuários adicionaram o manga\n"
                "- **Favoritos**: Quantos usuários favoritaram\n"
                "- **Status**: Se está sendo publicado, completo, etc.\n\n"
                "💎 **Raridade Extrema**: Apenas mangás LEGENDÁRIOS se aproximam de 1000 Criptogenes\n"
                "🏆 **Top 10**: ~800-950 Criptogenes\n"
                "⭐ **Top 100**: ~400-700 Criptogenes\n"
                "🎯 **Populares**: ~200-500 Criptogenes\n"
                "📚 **Comuns**: ~50-200 Criptogenes",
            inline=False
        )
        
        embed.add_field(
            name="💡 Dicas:",
            value="- Você pode clicar nos títulos dos mangás para ver sua página no MyAnimeList.\n"
                "- Você pode rolar mangás até atingir o limite por hora.\n"
                "- Para pegar mangás há um limite separado (1 a cada 5 horas).\n"
                "- Você pode pegar mangás que outros usuários rolaram, mesmo se atingiu seu limite de rolagem.\n"
                "- As reações precisam ser feitas rapidamente antes do mangá expirar.\n"
                "- Tente coletar mangás com alto valor de Criptogenes!",
            inline=False
        )
        
        embed.set_footer(text="Bot criado com a API Jikan (MyAnimeList) | Dados de mangás fornecidos pelo MyAnimeList.net")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _cmd_estatisticas(self, interaction: discord.Interaction):
        """Implementação do comando /estatisticas"""
        stats = metrics.get_stats_summary()
        
        embed = discord.Embed(
            title="📊 Estatísticas do Bot",
            description="Informações sobre o desempenho e uso do bot:",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="⏱️ Tempo online", value=stats["uptime"], inline=True)
        embed.add_field(name="🔢 Total de comandos", value=str(stats["total_commands"]), inline=True)
        embed.add_field(name="🖥️ Servidores ativos", value=str(stats["active_guilds"]), inline=True)
        
        top_cmds = stats["top_commands"]
        if top_cmds:
            cmd_text = "\n".join([f"{cmd}: {count}" for cmd, count in top_cmds])
            embed.add_field(name="📈 Comandos mais usados", value=cmd_text, inline=False)
        
        embed.add_field(name="⚡ Tempo médio de resposta API", value=stats["avg_api_response_time"], inline=True)
        embed.add_field(name="💾 Taxa de acerto do cache", value=stats["cache_hit_rate"], inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)