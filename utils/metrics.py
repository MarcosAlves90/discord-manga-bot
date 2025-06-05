"""
Sistema de métricas para monitorar o desempenho e uso do bot
"""
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from utils.logger import setup_logger

logger = setup_logger()

class BotMetrics:
    """Classe para monitoramento e métricas do bot"""
    
    def __init__(self):
        """Inicializa o sistema de métricas"""
        self.start_time = datetime.now()
        
        self.command_count = defaultdict(int)
        
        self.user_command_count = defaultdict(int)
        
        self.api_response_times = deque(maxlen=100)
        
        self.errors = defaultdict(int)
        
        self.guild_usage = defaultdict(int)
        
        self.cache_hits = 0
        self.cache_misses = 0
    
    def uptime(self):
        """Retorna o tempo de atividade do bot"""
        return datetime.now() - self.start_time
    
    def log_command(self, command_name, user_id=None, guild_id=None):
        """Registra a execução de um comando"""
        self.command_count[command_name] += 1
        
        if user_id:
            self.user_command_count[str(user_id)] += 1
        
        if guild_id:
            self.guild_usage[str(guild_id)] += 1
    
    def log_api_response(self, start_time, endpoint=None):
        """Registra o tempo de resposta de uma API"""
        elapsed = time.time() - start_time
        self.api_response_times.append(elapsed)
        
        if len(self.api_response_times) >= 10:
            avg_time = sum(self.api_response_times) / len(self.api_response_times)
            if avg_time > 1.0:
                logger.warning(f"Tempo médio de resposta da API está alto: {avg_time:.2f}s")
    
    def log_error(self, error_type):
        """Registra uma ocorrência de erro"""
        self.errors[error_type] += 1
    
    def log_cache_hit(self):
        """Registra um hit no cache"""
        self.cache_hits += 1
    
    def log_cache_miss(self):
        """Registra um miss no cache"""
        self.cache_misses += 1
    
    def get_cache_hit_rate(self):
        """Retorna a taxa de acerto do cache"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0
        return self.cache_hits / total
    
    def get_avg_api_response_time(self):
        """Retorna o tempo médio de resposta da API"""
        if not self.api_response_times:
            return 0
        return sum(self.api_response_times) / len(self.api_response_times)
    
    def get_top_commands(self, limit=5):
        """Retorna os comandos mais usados"""
        return sorted(self.command_count.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_top_users(self, limit=5):
        """Retorna os usuários que mais usam o bot"""
        return sorted(self.user_command_count.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_stats_summary(self):
        """Retorna um resumo das estatísticas"""
        return {
            "uptime": str(self.uptime()),
            "total_commands": sum(self.command_count.values()),
            "top_commands": self.get_top_commands(),
            "avg_api_response_time": f"{self.get_avg_api_response_time():.2f}s",
            "cache_hit_rate": f"{self.get_cache_hit_rate() * 100:.1f}%",
            "total_errors": sum(self.errors.values()),
            "active_guilds": len(self.guild_usage),
        }
    
    def export_stats(self, file_path='bot_metrics.json'):
        """Exporta as estatísticas para um arquivo JSON"""
        try:
            stats = {
                "uptime": str(self.uptime()),
                "total_commands": sum(self.command_count.values()),
                "commands": dict(self.command_count),
                "users": dict(self.user_command_count),
                "avg_api_response_time": self.get_avg_api_response_time(),
                "cache_hit_rate": self.get_cache_hit_rate(),
                "errors": dict(self.errors),
                "guilds": dict(self.guild_usage),
                "timestamp": datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
                
            return True
        except Exception as e:
            logger.error(f"Erro ao exportar estatísticas: {e}")
            return False

metrics = BotMetrics()
