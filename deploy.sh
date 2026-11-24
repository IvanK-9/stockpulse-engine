#!/usr/bin/env bash
set -e

echo "=================================================="
echo "  StockPulse 24/7 E-Com Engine Deployment Script  "
echo "=================================================="

# 1. Проверка установки Docker
if ! command -v docker &> /dev/null; then
    echo "[!] Docker не найден. Установка официального Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
fi

# 2. Проверка Docker Compose
if ! docker compose version &> /dev/null; then
    echo "[!] Docker Compose v2 не найден. Установка плагина..."
    apt-get update && apt-get install -y docker-compose-plugin
fi

# 3. Проверка .env файла
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[!] Файл .env не найден. Создаю из .env.example..."
        cp .env.example .env
        echo "[WARN] Пожалуйста, заполните ваши реальные токены в файле .env перед запуском!"
        echo "Выполните: nano .env"
        exit 1
    else
        echo "[ERR] Отсутствует .env и .env.example!"
        exit 1
    fi
fi

# 4. Проверка директорий
mkdir -p raw_data logs

# 5. Сборка и запуск контейнеров в фоновом режиме
echo "[+] Сборка и запуск сервисов в Docker..."
docker compose down --remove-orphans || true
docker compose up -d --build

echo ""
echo "[✓] Сервисы успешно запущены!"
echo "--------------------------------------------------"
docker compose ps
echo "--------------------------------------------------"
echo "Посмотреть логи в реальном времени:"
echo "  docker compose logs -f demo-bot"
echo "  docker compose logs -f lead-radar"
echo "=================================================="
