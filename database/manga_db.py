"""
Gerenciador de banco de dados para o bot de mangás
"""
import asyncpg
from datetime import datetime
import datetime as dt
from utils.constants import DATABASE_URL

class MangaDatabase:
    """Gerenciador de operações do banco de dados para o bot"""
    
    @staticmethod
    async def init_db():
        """Inicializa o banco de dados se não existir"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS manga_logs (
                    id SERIAL PRIMARY KEY,
                    usuario_id TEXT NOT NULL,
                    manga_id INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL
                )
            ''')
        finally:
            await conn.close()
    
    @staticmethod
    async def registrar_manga(usuario_id, manga_id):
        """Registra um mangá pego por um usuário"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO manga_logs (usuario_id, manga_id, timestamp) VALUES ($1, $2, $3)",
                str(usuario_id), manga_id, datetime.now()
            )
        finally:
            await conn.close()
    
    @staticmethod
    async def obter_mangas_usuario(usuario_id):
        """Retorna lista de IDs de mangás pegos pelo usuário"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(
                "SELECT manga_id FROM manga_logs WHERE usuario_id = $1 GROUP BY manga_id ORDER BY MAX(timestamp) DESC", 
                str(usuario_id)
            )
            return [row['manga_id'] for row in rows]
        finally:
            await conn.close()
    
    @staticmethod
    async def obter_ranking():
        """Retorna o ranking de usuários por quantidade de mangás únicos"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("""
                SELECT usuario_id, COUNT(DISTINCT manga_id) as total 
                FROM manga_logs 
                GROUP BY usuario_id 
                ORDER BY total DESC 
                LIMIT 10
            """)
            return [(row['usuario_id'], row['total']) for row in rows]
        finally:
            await conn.close()
    
    @staticmethod
    async def contagem_manga_periodo(usuario_id, periodo_segundos):
        """Conta quantos mangás um usuário obteve em um período específico"""
        timestamp_limite = datetime.now() - dt.timedelta(seconds=periodo_segundos)
        
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM manga_logs WHERE usuario_id = $1 AND timestamp > $2",
                str(usuario_id), timestamp_limite
            )
            return result if result else 0
        finally:
            await conn.close()
