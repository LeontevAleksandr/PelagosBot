"""Утилита для получения версии бота из git"""
import subprocess
import os
from datetime import datetime


def get_git_hash() -> str:
    """Получить короткий hash текущего коммита"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_git_branch() -> str:
    """Получить текущую ветку"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_version_info() -> dict:
    """Получить полную информацию о версии"""
    # Приоритет: GIT_HASH (Docker) > GIT_COMMIT (runtime) > get_git_hash() (локально)
    git_hash = os.getenv('GIT_HASH') or os.getenv('GIT_COMMIT') or get_git_hash()
    git_branch = os.getenv('GIT_BRANCH', get_git_branch())

    return {
        'hash': git_hash,
        'branch': git_branch,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def format_version_message() -> str:
    """Форматировать сообщение с версией для отправки пользователю"""
    info = get_version_info()

    return f"""🤖 <b>Информация о боте</b>

📦 <b>Версия:</b> <code>{info['hash']}</code>
🌿 <b>Ветка:</b> <code>{info['branch']}</code>
🕐 <b>Запущен:</b> {info['timestamp']}

✅ Бот работает корректно!"""


# Получаем версию при импорте модуля
VERSION_INFO = get_version_info()
GIT_HASH = VERSION_INFO['hash']
GIT_BRANCH = VERSION_INFO['branch']
