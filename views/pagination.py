"""
Views de paginação para o bot Discord
"""
import discord

class MangaPaginationView(discord.ui.View):
    """View para paginação da lista de mangás do usuário"""
    
    def __init__(self, manga_list, username, per_page=10):
        super().__init__(timeout=180)
        self.manga_list = manga_list
        self.username = username
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(manga_list) - 1) // per_page + 1
        
        self.update_buttons()
    
    def update_buttons(self):
        """Atualiza o estado dos botões de navegação"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    async def generate_embed(self):
        """Gera o embed para a página atual"""
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.manga_list))
        current_mangas = self.manga_list[start_idx:end_idx]
        
        mangas_formatados = []
        for manga in current_mangas:
            if isinstance(manga, dict) and 'title' in manga:
                from utils.constants import calcular_criptogenes
                titulo = manga.get('title', 'Sem título')
                url = manga.get('url', '')
                criptogenes = calcular_criptogenes(manga_data=manga)
                
                if url:
                    mangas_formatados.append(f"[{titulo}]({url}) - <a:gold_stud:1380069369580748840> **{criptogenes}** Pecinhas")
                else:
                    mangas_formatados.append(f"{titulo} - <a:gold_stud:1380069369580748840> **{criptogenes}** Pecinhas")
            else:
                mangas_formatados.append(f"{manga}")
        
        embed = discord.Embed(
            title=f"Mangás de {self.username}", 
            description="\n".join(mangas_formatados) or "Nenhum mangá encontrado."
        )
        embed.set_footer(text=f"Página {self.current_page + 1}/{self.total_pages}")
        return embed
    
    @discord.ui.button(label="Anterior", style=discord.ButtonStyle.gray, custom_id="previous_page")
    async def previous_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para página anterior"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = await self.generate_embed()
            await button_interaction.response.edit_message(embed=embed, view=self)
        else:
            await button_interaction.response.defer()
    
    @discord.ui.button(label="Próxima", style=discord.ButtonStyle.gray, custom_id="next_page")
    async def next_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para próxima página"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = await self.generate_embed()
            await button_interaction.response.edit_message(embed=embed, view=self)
        else:
            await button_interaction.response.defer()
