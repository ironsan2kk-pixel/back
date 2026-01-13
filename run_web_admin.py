#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🌐 ЗАПУСК ВЕБ-АДМИНКИ
═══════════════════════════════════════════════════════════════════════════════

Использование:
    python run_web_admin.py [host] [port]

Примеры:
    python run_web_admin.py                    # localhost:8080
    python run_web_admin.py 0.0.0.0 8080       # доступ из сети
"""

import sys
import os
import logging

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_admin import run_admin


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

    print("=" * 60)
    print("🌐 WEB ADMIN PANEL")
    print("=" * 60)
    print(f"📍 Адрес: http://{host}:{port}")
    print(f"📁 Директория: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"📝 Логи: {log_dir}")
    print("   - web_admin.log (все логи)")
    print("   - web_admin_errors.log (только ошибки)")
    print("=" * 60)
    print()

    run_admin(host=host, port=port)


if __name__ == "__main__":
    main()
