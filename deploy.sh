#!/usr/bin/env bash
# ========================================================
# EduCenter CRM & Telegram Bot Turnkey Deployment Script
# Operatsion tizim: Ubuntu / Debian Linux VPS
# ========================================================

set -e

PROJECT_DIR="/var/www/educenter_bot"
SERVICE_NAME="educenter"

echo "==============================================="
echo "🚀 EduCenter CRM & Bot Serverga o'rnatilmoqda..."
echo "==============================================="

# 1. Tizim paketlarini yangilash va kerakli vositalarni o'rnatish
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# 2. Loyiha papkasini tekshirish
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📁 $PROJECT_DIR papkasi yaratilmoqda..."
    sudo mkdir -p "$PROJECT_DIR"
    sudo chown -R $USER:$USER "$PROJECT_DIR"
fi

# 3. Virtual muhit (venv) yaratish
cd "$PROJECT_DIR"
if [ ! -d ".venv" ]; then
    echo "🐍 Python virtual muhit (.venv) yaratilmoqda..."
    python3 -m venv .venv
fi

# 4. Bog'liqliklarni o'rnatish
echo "📦 Python kutubxonalari o'rnatilmoqda..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 5. .env faylini tekshirish
if [ ! -f ".env" ]; then
    echo "⚙️ .env fayli topilmadi. Namuna (.env.example) dan nusxalandi."
    cp .env.example .env
    echo "⚠️ DIQQAT: Iltimos, .env faylini o'zingizning BOT_TOKEN va domeningiz bilan to'ldiring: nano .env"
fi

# 6. Systemd servisini o'rnatish
echo "🔧 Systemd servisi sozlanmoqda..."
sudo cp educenter.service /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

echo "==============================================="
echo "✅ EduCenter muvaffaqiyatli ishga tushirildi!"
echo "Holatni tekshirish: sudo systemctl status ${SERVICE_NAME}"
echo "Loglarni ko'rish: sudo journalctl -u ${SERVICE_NAME} -f"
echo "==============================================="
