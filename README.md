# StockPulse E-Com Automation & Lead Engine

Высокоскоростная инфраструктура для селлеров Wildberries/Ozon и автоматического перехвата лидов в Telegram.

## Архитектура сервиса

- **Demo Bot (`scripts/demo_bot.py`)**: Telegram-бот (`@stockpulse_demo_bot`) на aiogram 3. Прямой CDN-сбор карточек товаров WB за 170–200 мс без эмуляции браузера (Selenium/Playwright) и риска капчи.
- **Lead Radar (`scripts/lead_radar.py`)**: Снайперский слушатель 15 профильных каналов (9 чатов селлеров + 6 бирж заказов) на Telethon с автоматической фильтрацией спама и отправкой 1-click питчей.
- **Batch Exporter (`scripts/batch_wb_exporter.py`)**: Пакетная выгрузка до 1 000 артикулов в форматированный Excel за 3 минуты.

---

## 🚀 Быстрый деплой на 24/7 VPS (Ubuntu / Debian)

### 1. Подготовка на сервере
Подключитесь к вашему VPS по SSH:
```bash
ssh root@YOUR_SERVER_IP
```

### 2. Клонирование репозитория
```bash
git clone https://github.com/YOUR_USERNAME/stockpulse-engine.git /opt/stockpulse
cd /opt/stockpulse
```

### 3. Настройка переменных окружения
Скопируйте шаблон и заполните секреты:
```bash
cp .env.example .env
nano .env
```
Укажите:
- `TELEGRAM_BOT_TOKEN`
- `TG_API_ID`
- `TG_API_HASH`
- `TG_PHONE`
- `ADMIN_TG_ID`

### 4. Перенос файла авторизации Telegram (Telethon Session)
Чтобы Радар работал без повторного ввода SMS-кода, скопируйте с локального ПК файл сессии в папку `raw_data/` на сервере:
```bash
# Выполнить на локальном компьютере:
scp raw_data/telegram_reader_session.session root@YOUR_SERVER_IP:/opt/stockpulse/raw_data/
```

### 5. Запуск через Docker Compose в 1 команду
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 🛠 Управление на сервере

- **Проверить статус:**
  ```bash
  docker compose ps
  ```
- **Просмотр логов:**
  ```bash
  docker compose logs -f demo-bot
  docker compose logs -f lead-radar
  ```
- **Перезапуск:**
  ```bash
  docker compose restart
  ```
- **Остановка:**
  ```bash
  docker compose down
  ```
