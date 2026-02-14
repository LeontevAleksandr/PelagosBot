"""Загрузчики данных для экскурсий"""
from .private_fetcher import PrivateFetcher
from .group_fetcher import GroupFetcher
from .companion_fetcher import CompanionFetcher
from .island_fetcher import IslandFetcher

__all__ = [
    'PrivateFetcher',
    'GroupFetcher',
    'CompanionFetcher',
    'IslandFetcher'
]
