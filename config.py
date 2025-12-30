import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin IDs (для уведомлений)
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Ссылки компании
COMPANY_LINKS = {
    "conditions_price": "https://pelagostours.com/garantiya-nizkoj-czeny",
    "conditions_transfer": "https://pelagostours.com/besplatnyj-transfer",
    "conditions_discount": "https://pelagostours.com/skidka-10",
    "support": "t.me/PelagosChat",
    "youtube": "https://www.youtube.com/@pelagostours",
    "telegram": "t.me/pelagostravel",
    "rutube": "https://rutube.ru/channel/26281136/",
    "phone": "tg://call?phone=+639088888787",
    "about": "https://www.pelagos.ru/tur-operator-po-filippinam-pelagos-tours/",
    "contacts": "https://www.pelagos.ru/tur-operator-po-filippinam-pelagos-tours/",
    "reviews": "t.me/pelagostravel/2467",
    "packages": "https://pelagostours.com/tours"
}

# Настройки удаления сообщений
DELETE_TEMP_MESSAGES = True  # Удалять временные сообщения
KEEP_INFO_MESSAGES = False    # Оставлять информационные блоки