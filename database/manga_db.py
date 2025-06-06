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
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS usuario_economia (
                    usuario_id TEXT PRIMARY KEY,
                    saldo DECIMAL(10,2) DEFAULT 0.00,
                    total_ganho DECIMAL(10,2) DEFAULT 0.00,
                    ultimo_daily TIMESTAMP DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transacao_economia (
                    id SERIAL PRIMARY KEY,
                    usuario_id TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    valor DECIMAL(10,2) NOT NULL,
                    descricao TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
    @staticmethod
    async def obter_saldo_usuario(usuario_id):
        """Obtém o saldo de pecinhas de um usuário"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow(
                "SELECT saldo, total_ganho, ultimo_daily FROM usuario_economia WHERE usuario_id = $1",
                str(usuario_id)
            )
            if row:
                return {
                    'saldo': float(row['saldo']),
                    'total_ganho': float(row['total_ganho']),
                    'ultimo_daily': row['ultimo_daily']
                }
            else:
                await conn.execute(
                    "INSERT INTO usuario_economia (usuario_id) VALUES ($1) ON CONFLICT (usuario_id) DO NOTHING",
                    str(usuario_id)
                )
                return {'saldo': 0.0, 'total_ganho': 0.0, 'ultimo_daily': None}
        finally:
            await conn.close()
    
    @staticmethod
    async def adicionar_pecinhas(usuario_id, valor, descricao=""):
        """Adiciona pecinhas ao saldo de um usuário"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO usuario_economia (usuario_id) VALUES ($1) ON CONFLICT (usuario_id) DO NOTHING",
                str(usuario_id)
            )
            
            await conn.execute("""
                UPDATE usuario_economia 
                SET saldo = saldo + $2, 
                    total_ganho = total_ganho + $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE usuario_id = $1
            """, str(usuario_id), valor)
            
            await conn.execute("""
                INSERT INTO transacao_economia (usuario_id, tipo, valor, descricao)
                VALUES ($1, 'ganho', $2, $3)
            """, str(usuario_id), valor, descricao)
            
            novo_saldo = await conn.fetchval(
                "SELECT saldo FROM usuario_economia WHERE usuario_id = $1",
                str(usuario_id)
            )
            return float(novo_saldo)
        finally:
            await conn.close()
    
    @staticmethod
    async def verificar_pode_daily(usuario_id):
        """Verifica se o usuário pode usar o comando daily (cooldown de 24h)"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow(
                "SELECT ultimo_daily FROM usuario_economia WHERE usuario_id = $1",
                str(usuario_id)
            )
            
            if not row or not row['ultimo_daily']:
                return True, None
            
            ultimo_daily = row['ultimo_daily']
            agora = datetime.now()
            tempo_restante = ultimo_daily + dt.timedelta(hours=24) - agora
            
            if tempo_restante.total_seconds() <= 0:
                return True, None
            else:
                return False, tempo_restante
        finally:
            await conn.close()
    
    @staticmethod
    async def registrar_daily(usuario_id, valor):
        """Registra o daily de um usuário e adiciona as pecinhas"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO usuario_economia (usuario_id) VALUES ($1) ON CONFLICT (usuario_id) DO NOTHING",
                str(usuario_id)
            )
            
            await conn.execute("""
                UPDATE usuario_economia 
                SET ultimo_daily = CURRENT_TIMESTAMP,
                    saldo = saldo + $2,
                    total_ganho = total_ganho + $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE usuario_id = $1
            """, str(usuario_id), valor)
            
            await conn.execute("""
                INSERT INTO transacao_economia (usuario_id, tipo, valor, descricao)
                VALUES ($1, 'daily', $2, 'Daily reward')
            """, str(usuario_id), valor)
            
            novo_saldo = await conn.fetchval(
                "SELECT saldo FROM usuario_economia WHERE usuario_id = $1",
                str(usuario_id)
            )
            return float(novo_saldo)
        finally:
            await conn.close()
    
    @staticmethod
    async def obter_ranking_economia():
        """Retorna o ranking de usuários por quantidade de pecinhas"""
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("""
                SELECT usuario_id, saldo, total_ganho
                FROM usuario_economia 
                WHERE saldo > 0
                ORDER BY saldo DESC 
                LIMIT 10
            """)
            return [(row['usuario_id'], float(row['saldo']), float(row['total_ganho'])) for row in rows]
        finally:
            await conn.close()
