import aiohttp
import asyncio
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class APIClient:
    """Базовый класс для работы с HTTP API"""
    
    def __init__(self, base_url: str, api_key: str = None, timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Ленивое создание сессии"""
        if self._session is None or self._session.closed:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session
    
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Общий метод для запросов"""
        session = await self.get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                **kwargs
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API error: {response.status} - {await response.text()}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            return None
    
    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs):
        return await self.request('GET', endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, json: Optional[Dict] = None, **kwargs):
        return await self.request('POST', endpoint, json=json, **kwargs)
    
    async def close(self):
        """Закрытие сессии (вызывать при завершении)"""
        if self._session and not self._session.closed:
            await self._session.close()