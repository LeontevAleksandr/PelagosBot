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
    "support": "https://t.me/pelagos_support",
    "youtube": "https://youtube.com/@pelagostours",
    "rutube": "https://rutube.ru/pelagostours",
    "instagram": "https://instagram.com/pelagostours",
    "about": "https://pelagostours.com/about",
    "contacts": "https://pelagostours.com/contacts",
    "reviews": "https://pelagostours.com/reviews",
    "packages": "https://pelagostours.com/tours"
}

# Настройки удаления сообщений
DELETE_TEMP_MESSAGES = True  # Удалять временные сообщения
KEEP_INFO_MESSAGES = True    # Оставлять информационные блоки