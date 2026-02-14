"""Обработчики флоу экскурсий"""
from aiogram import Router

from .common import router as common_router
from .group import router as group_router
from .private import router as private_router
from .companions import router as companions_router
from .booking import router as booking_router
from .navigation import router as navigation_router

# Главный роутер для экскурсий
router = Router()

# Регистрируем все под-роутеры
router.include_router(common_router)
router.include_router(group_router)
router.include_router(private_router)
router.include_router(companions_router)
router.include_router(booking_router)
router.include_router(navigation_router)

__all__ = ['router']
