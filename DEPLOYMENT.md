## Функции

- Поиск и бронирование отелей
- Экскурсии
- Трансферы
- Пакетные туры (нету)
- Корзина заказов
- Интеграция с Pelagos API

## Структура

```
PelagosBot/
├── bot.py              # Точка входа
├── config.py           # Конфигурация
├── handlers/           # Обработчики команд
├── services/           # Бизнес-логика и API
├── keyboards/          # Клавиатуры бота
├── states/             # FSM состояния
├── utils/              # Утилиты и кэш
└── data/               # Данные и медиа
```

## Поддержка

При проблемах проверьте:
1. Логи: `docker compose logs -f`
2. Статус: `docker compose ps`
3. Healthcheck: `./health_check.sh`

# Как запустить бота на сервере

Инструкция для развертывания на Ubuntu сервере через Docker.

## Установка Docker на Ubuntu

```bash
# Обновить пакеты
sudo apt update

# Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавить пользователя в группу docker (чтобы не использовать sudo)
sudo usermod -aG docker $USER

# Перелогиниться или выполнить
newgrp docker

# Проверить установку
docker --version
docker compose version
```

## Настройка

### 1. Загрузка файлов на сервер

Через Git (если есть репозиторий):
```bash
git clone https://your-repo-url.git
cd PelagosBot
```

Или загрузите файлы через SCP/SFTP в папку `/home/user/PelagosBot`

### 2. Создание файла .env

```bash
cd /home/user/PelagosBot
nano .env
```

Вставьте свои данные:
```
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_IDS=ваш_telegram_id
PELAGOS_API_KEY=ваш_api_ключ
```

Сохраните (Ctrl+O, Enter, Ctrl+X)

Как получить:
- `BOT_TOKEN` - от @BotFather в Telegram
- `ADMIN_IDS` - узнать у @userinfobot
- `PELAGOS_API_KEY` - ключ API от Pelagos

## Запуск

```bash
cd /home/user/PelagosBot
docker compose up -d
```

Это запустит 2 контейнера:
- `pelagos-bot` - сам бот
- `pelagos-redis` - база данных для кэширования

Посмотреть логи:
```bash
docker compose logs -f
```

Остановить:
```bash
docker compose stop
```

Перезапустить:
```bash
docker compose restart
```

## Обновление бота

Когда получите новую версию:
```bash
docker compose down
# замените файлы на новые
docker compose up -d --build
```

## Если что-то не работает

- Проверьте что токен правильный в `.env`
- Посмотрите логи `docker compose logs`
- Убедитесь что Docker запущен

На Linux может понадобиться добавить себя в группу docker:
```bash
sudo usermod -aG docker $USER
```

## Мониторинг

Проверить статус контейнеров:
```bash
docker compose ps
```

Здоровье контейнеров (должно быть "healthy"):
```bash
docker ps
```

## Автозапуск на Ubuntu

Чтобы бот автоматически стартовал при перезагрузке сервера:

```bash
# Создать systemd сервис
sudo nano /etc/systemd/system/pelagos-bot.service
```

Вставьте:
```ini
[Unit]
Description=Pelagos Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/PelagosBot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=your_username

[Install]
WantedBy=multi-user.target
```

Замените `/home/user/PelagosBot` и `your_username` на свои значения.

Включите автозапуск:
```bash
sudo systemctl enable pelagos-bot
sudo systemctl start pelagos-bot
```

## Безопасность (опционально)

Настройте firewall если нужен доступ по SSH:
```bash
sudo ufw allow OpenSSH
sudo ufw enable
```

Порты для бота открывать НЕ нужно - он сам подключается к Telegram.

## Production рекомендации

- Логи ограничены 10MB x 3 файла для бота, 5MB x 2 для Redis
- Redis данные сохраняются в volume `redis-data` (не пропадут при перезапуске)
- Контейнеры автоматически перезапускаются при падении
- Healthcheck каждую минуту проверяет что бот живой
- Бот не запустится пока Redis не будет готов
- Никакие порты не exposed наружу - всё внутри Docker сети

Бэкап данных Redis (если нужно):
```bash
docker compose exec redis redis-cli SAVE
docker cp pelagos-redis:/data/dump.rdb ./backup-$(date +%Y%m%d).rdb
```

---

Всё, бот должен работать. Проверяйте в телеграме командой /start
