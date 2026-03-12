"""
Главный коннектор для взаимодействия с фронтендом Pelagos через Order API

Этот модуль обеспечивает простой и эффективный интерфейс для:
1. Создания заказов из корзины бота
2. Синхронизации данных между ботом и системой Pelagos
3. Обработки результатов и ошибок
"""
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.order_api import OrderAPI
from utils.order_api_adapter import order_api_adapter

logger = logging.getLogger(__name__)


class FrontendConnector:
    """
    Главный класс для взаимодействия бота с фронтендом Pelagos

    Обеспечивает простой интерфейс для создания и управления заказами
    """

    def __init__(self, api_key: str = None):
        """
        Инициализация коннектора

        Args:
            api_key: API ключ для доступа к Pelagos API
        """
        self.api_key = api_key or os.getenv("PELAGOS_API_KEY")
        self.order_api = OrderAPI(api_key=self.api_key)

    async def create_order_from_cart(
        self,
        state_data: dict,
        order_items: List[dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Создать заказ в системе Pelagos из корзины бота

        Args:
            state_data: данные из FSM состояния бота (user_name, user_phone и т.д.)
            order_items: список элементов заказа из state_data["order"]

        Returns:
            dict с результатом создания заказа или None в случае ошибки
            Формат: {
                "success": bool,
                "order_id": int,
                "message": str,
                "parts_added": int,
                "parts_failed": int,
                "errors": List[str]
            }
        """
        logger.info("=" * 60)
        logger.info("🚀 НАЧАЛО СОЗДАНИЯ ЗАКАЗА В PELAGOS")
        logger.info("=" * 60)

        if not order_items:
            logger.warning("⚠️ Попытка создать пустой заказ")
            return {
                "success": False,
                "order_id": None,
                "message": "Корзина пуста",
                "parts_added": 0,
                "parts_failed": 0,
                "errors": ["Нет элементов для добавления в заказ"]
            }

        result = {
            "success": False,
            "order_id": None,
            "message": "",
            "parts_added": 0,
            "parts_failed": 0,
            "errors": []
        }

        try:
            # Шаг 1: Подготовка данных заказа
            logger.info("�� Шаг 1: Подготовка данных заказа")
            order_data = order_api_adapter.prepare_order_data(state_data)
            logger.info(f"   Клиент: {order_data['client_name']}")
            logger.info(f"   Агент: {order_data['agent_name']}")

            # Шаг 2: Проверка существующего заказа или создание нового
            existing_order_id = state_data.get("current_order_id")
            order_id = None

            if existing_order_id:
                # Проверяем статус существующего заказа
                logger.info(f"🔍 Найден существующий заказ #{existing_order_id}, проверяем статус...")
                order_info = await self.order_api.load_order(existing_order_id)

                if order_info and order_info.get("code") == "OK":
                    order_status = order_info.get("order", {}).get("status", 999)
                    logger.info(f"   Статус заказа: {order_status}")

                    # Статусы: 0 = Черновик, 10 = Отправлен, 20 = Получен
                    # Можем редактировать заказ если статус <= 20
                    if order_status <= 20:
                        order_id = existing_order_id
                        logger.info(f"✅ Используем существующий заказ #{order_id} (статус {order_status})")
                    else:
                        logger.info(f"⚠️ Заказ #{existing_order_id} имеет статус {order_status}, создаём новый")
                else:
                    logger.warning(f"⚠️ Не удалось загрузить заказ #{existing_order_id}, создаём новый")

            if not order_id:
                # Создаём новый заказ
                logger.info("📤 Шаг 2: Создание нового заказа в Pelagos")
                create_response = await self.order_api.create_order(
                    client_name=order_data["client_name"],
                    agent_name=order_data["agent_name"],
                    names=order_data.get("names", ""),
                    descr=order_data.get("descr", ""),
                    tourist_phone=order_data.get("tourist_phone", "")
                )

                if not create_response or create_response.get("code") != "OK":
                    error_msg = f"Не удалось создать заказ: {create_response}"
                    logger.error(f"❌ {error_msg}")
                    result["message"] = "Ошибка создания заказа"
                    result["errors"].append(error_msg)
                    return result

                order_id = create_response.get("order_id")
                if not order_id:
                    error_msg = "API не вернул order_id"
                    logger.error(f"❌ {error_msg}")
                    result["message"] = "Ошибка получения ID заказа"
                    result["errors"].append(error_msg)
                    return result

                logger.info(f"✅ Новый заказ создан успешно. ID: {order_id}")

            result["order_id"] = order_id

            # Шаг 3: Преобразование элементов корзины в пункты заказа
            logger.info(f"📋 Шаг 3: Преобразование {len(order_items)} элементов корзины")
            parts = order_api_adapter.convert_order_to_parts(order_items, state_data)
            logger.info(f"   Подготовлено {len(parts)} пунктов для добавления")

            # Шаг 4: Добавление пунктов в заказ
            logger.info(f"📤 Шаг 4: Добавление пунктов в заказ #{order_id}")

            for i, part in enumerate(parts, 1):
                try:
                    logger.info(f"   Добавление пункта {i}/{len(parts)}...")
                    logger.debug(f"      Параметры: {part}")

                    add_response = await self.order_api.add_order_part(
                        order_id=order_id,
                        **part
                    )

                    if add_response and add_response.get("code") == "OK":
                        result["parts_added"] += 1
                        logger.info(f"   ✅ Пункт {i}/{len(parts)} добавлен успешно")
                    else:
                        result["parts_failed"] += 1
                        error_msg = f"Пункт {i}: {add_response}"
                        result["errors"].append(error_msg)
                        logger.error(f"   ❌ Ошибка добавления пункта {i}: {add_response}")

                except Exception as e:
                    result["parts_failed"] += 1
                    error_msg = f"Пункт {i}: исключение {str(e)}"
                    result["errors"].append(error_msg)
                    logger.error(f"   ❌ Исключение при добавлении пункта {i}: {e}", exc_info=True)

            # Шаг 5: Формирование итогового результата
            logger.info("=" * 60)
            logger.info("📊 РЕЗУЛЬТАТЫ СОЗДАНИЯ ЗАКАЗА")
            logger.info("=" * 60)
            logger.info(f"   ID заказа: {order_id}")
            logger.info(f"   Добавлено пунктов: {result['parts_added']}/{len(parts)}")
            logger.info(f"   Ошибок: {result['parts_failed']}")

            if result["parts_added"] > 0:
                result["success"] = True
                result["message"] = f"Заказ #{order_id} создан. Добавлено {result['parts_added']} из {len(parts)} пунктов"
                logger.info(f"✅ {result['message']}")
            else:
                result["message"] = f"Заказ #{order_id} создан, но не удалось добавить пункты"
                logger.warning(f"⚠️ {result['message']}")

            if result["errors"]:
                logger.warning(f"   Список ошибок: {result['errors']}")

            logger.info("=" * 60)

            return result

        except Exception as e:
            error_msg = f"Критическое исключение при создании заказа: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result["message"] = "Критическая ошибка при создании заказа"
            result["errors"].append(error_msg)
            return result

    async def get_order_details(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить детали заказа из Pelagos

        Args:
            order_id: ID заказа

        Returns:
            dict с данными заказа или None
        """
        logger.info(f"📥 Загрузка деталей заказа #{order_id}")

        try:
            order_data = await self.order_api.load_order(order_id)

            if order_data and order_data.get("code") == "OK":
                logger.info(f"✅ Заказ #{order_id} загружен успешно")
                return order_data
            else:
                logger.error(f"❌ Не удалось загрузить заказ #{order_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при загрузке заказа #{order_id}: {e}", exc_info=True)
            return None

    async def get_order_summary(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить сводку по заказу (пункты и суммы)

        Args:
            order_id: ID заказа

        Returns:
            dict с ключами: lst (список пунктов), totals (итоговые суммы)
        """
        logger.info(f"📥 Загрузка сводки заказа #{order_id}")

        try:
            parts_data = await self.order_api.get_order_parts(order_id)

            if parts_data and parts_data.get("code") == "OK":
                logger.info(f"✅ Сводка заказа #{order_id} загружена")
                return {
                    "lst": parts_data.get("lst", []),
                    "totals": parts_data.get("totals", {}),
                    "raw_data": parts_data
                }
            else:
                logger.error(f"❌ Не удалось загрузить сводку заказа #{order_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при загрузке сводки заказа #{order_id}: {e}", exc_info=True)
            return None

    async def update_order_info(
        self,
        order_id: int,
        client_name: str = None,
        agent_name: str = None,
        names: str = None,
        descr: str = None,
        tourist_phone: str = None
    ) -> bool:
        """
        Обновить информацию о заказе

        Args:
            order_id: ID заказа
            client_name: Имя клиента
            agent_name: Имя агента
            names: Имена туристов
            descr: Описание заказа
            tourist_phone: Номер телефона туриста

        Returns:
            True если обновление успешно
        """
        logger.info(f"📤 Обновление заказа #{order_id}")

        try:
            update_response = await self.order_api.update_order(
                order_id=order_id,
                client_name=client_name,
                agent_name=agent_name,
                names=names,
                descr=descr,
                tourist_phone=tourist_phone
            )

            if update_response and update_response.get("code") == "OK":
                logger.info(f"✅ Заказ #{order_id} обновлен успешно")
                return True
            else:
                logger.error(f"❌ Не удалось обновить заказ #{order_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Исключение при обновлении заказа #{order_id}: {e}", exc_info=True)
            return False

    async def notify_new_order(self, order_items: List[dict], state_data: dict) -> None:
        """
        Отправить уведомление о новой заявке.
        Для групповых экскурсий — записать участника через sign_on_to_event (сервер сам шлёт уведомление).
        Для остальных — отправить channelmsg.
        Ошибки не прерывают основной флоу — только логируются.
        """
        name = state_data.get("user_name", "")
        phone = state_data.get("phone_number") or state_data.get("user_phone", "")
        tg = state_data.get("telegram_username", "")

        non_group_items = []

        for item in order_items:
            if item.get("type") == "excursion" and item.get("excursion_type") == "group":
                event_id = item.get("event_id", "")
                pax = item.get("people_count", 1)
                if event_id:
                    try:
                        await self.order_api.sign_on_to_event(
                            ss_id=int(event_id),
                            name=name,
                            pax=pax,
                            phone=phone,
                            tg=tg
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось записать на событие {event_id}: {e}")
                else:
                    non_group_items.append(item)
            else:
                non_group_items.append(item)

        if non_group_items:
            try:
                msg = order_api_adapter.build_channel_message(non_group_items, state_data)
                await self.order_api.send_channelmsg("grouptours", msg)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить уведомление в канал: {e}")

    async def close(self):
        """Закрыть соединение с API"""
        await self.order_api.close()


# Глобальный экземпляр (можно использовать напрямую)
frontend_connector = FrontendConnector()
