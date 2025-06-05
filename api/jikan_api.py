"""
Cliente para a API Jikan (MyAnimeList)
"""
import asyncio
import aiohttp
import time
from utils.constants import API_BASE
from utils.logger import setup_logger
from utils.metrics import metrics

logger = setup_logger()

class JikanAPI:
    """Cliente para API Jikan (MyAnimeList)"""

    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_ttl = 3600

    async def get_session(self):
        """Retorna sessão HTTP, criando uma se necessário"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Fecha a sessão HTTP se estiver aberta"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    def _get_from_cache(self, key):
        """Recupera dados do cache se ainda forem válidos"""
        if key in self.cache:
            cached_time, data = self.cache[key]
            if time.time() - cached_time < self.cache_ttl:
                logger.debug(f"Cache hit para: {key}")
                metrics.log_cache_hit()
                return data
            else:
                del self.cache[key]
        metrics.log_cache_miss()
        return None

    def _store_in_cache(self, key, data):
        """Armazena dados no cache com timestamp atual"""
        self.cache[key] = (time.time(), data)

        if len(self.cache) > 100:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]
    async def fetch_manga_info(self, manga_id, return_full_data=False):
        """
        Busca informações de um mangá pelo ID

        Args:
            manga_id: ID do mangá no MyAnimeList
            return_full_data: Se True, retorna o objeto completo do mangá em vez da string formatada

        Returns:
            str ou dict: String formatada com link ou dados completos do mangá
        """
        cache_key = f"manga_{manga_id}_{return_full_data}"

        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        url = f"{API_BASE}/manga/{manga_id}"
        max_retries = 3
        retry_delay = 1

        session = await self.get_session()
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                async with session.get(url) as resp:
                    metrics.log_api_response(start_time, endpoint="manga_info")

                    if resp.status == 200:
                        data = await resp.json()
                        manga = data.get("data", {})

                        if return_full_data:
                            self._store_in_cache(cache_key, manga)
                            return manga
                        else:
                            titulo = manga.get("title", f"Manga ID {manga_id}")
                            url_manga = manga.get("url", "")
                            result = f"[{titulo}]({url_manga})"

                            self._store_in_cache(cache_key, result)
                            return result
                    elif resp.status == 429:
                        metrics.log_error("rate_limit")
                        await asyncio.sleep(retry_delay * 2)
                    else:
                        metrics.log_error(f"api_error_{resp.status}")
                        await asyncio.sleep(retry_delay)
            except Exception as e:
                metrics.log_error(f"connection_error")
                logger.error(f"Erro ao buscar mangá {manga_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)

        return f"Manga ID {manga_id} (Falha ao buscar informações)" if not return_full_data else {}
    
    async def obter_manga_aleatorio(self, max_attempts=5):
        """
        Busca um mangá aleatório (apenas SFW)
        
        Args:
            max_attempts: Número máximo de tentativas para encontrar um mangá SFW
            
        Returns:
            dict: Dados do mangá SFW encontrado
        """
        session = await self.get_session()
        
        for attempt in range(max_attempts):
            start_time = time.time()
            
            try:
                params = {"sfw": "true"}
                async with session.get(f"{API_BASE}/random/manga", params=params) as resp:
                    metrics.log_api_response(start_time, endpoint="random_manga")

                    if resp.status != 200:
                        metrics.log_error(f"api_error_{resp.status}")
                        if attempt == max_attempts - 1:
                            raise Exception(f"Erro ao buscar mangá aleatório: status {resp.status}")
                        continue

                    manga_data = (await resp.json()).get("data", {})
                    
                    if self._is_manga_sfw(manga_data):
                        logger.debug(f"Mangá SFW encontrado: {manga_data.get('title', 'Título não disponível')}")
                        return manga_data
                    else:
                        logger.debug(f"Mangá não-SFW filtrado: {manga_data.get('title', 'Título não disponível')}")
                        
            except Exception as e:
                if attempt == max_attempts - 1:
                    metrics.log_error("random_manga_error")
                    raise e
                await asyncio.sleep(0.5)
        
        logger.warning("Não foi possível encontrar um mangá SFW após várias tentativas")
        metrics.log_error("no_sfw_manga_found")
        raise Exception("Não foi possível encontrar um mangá adequado no momento")

    def _is_manga_sfw(self, manga_data):
        """
        Verifica se um mangá é SFW (Safe for Work) baseado nos gêneros
        
        Args:
            manga_data: Dados do mangá retornados pela API
            
        Returns:
            bool: True se o mangá for SFW, False caso contrário
        """
        if not manga_data:
            return False
            
        nsfw_genres = {
            'Hentai', 'Ecchi', 'Erotica', 'Smut'
        }
        
        nsfw_demographics = {
            'Hentai'
        }
        
        genres = manga_data.get('genres', [])
        for genre in genres:
            if genre.get('name') in nsfw_genres:
                return False
        
        demographics = manga_data.get('demographics', [])
        for demo in demographics:
            if demo.get('name') in nsfw_demographics:
                return False
        
        rating = manga_data.get('rating')
        if rating and 'Rx' in rating:
            return False
            
        return True
