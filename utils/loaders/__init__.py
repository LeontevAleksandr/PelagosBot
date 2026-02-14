"""Модуль загрузчиков данных для различных флоу бота"""

from .hotels_loader import HotelsLoader
from .excursions import ExcursionsLoader
from .transfers_loader import TransfersLoader
from .packages_loader import PackagesLoader

__all__ = [
    'HotelsLoader',
    'ExcursionsLoader',
    'TransfersLoader',
    'PackagesLoader',
]
