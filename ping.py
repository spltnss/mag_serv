import os
import re
import subprocess
import time
import json
from datetime import datetime

# Путь к JSON файлу
SHOP_LIST_JSON = "shop_list.json"


def ping_shop(shop_name):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", shop_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
        )
        ip_match = re.search(r"\[(\d+\.\d+\.\d+\.\d+)\]", result.stdout)
        if ip_match:
            return ip_match.group(1)
    except:
        pass
    return None


def determine_vpn(ip, shop_num):
    if ip and ip.startswith("14.12.") and ip.endswith(f".{shop_num}.10"):
        return "Новая VPN"
    elif ip:
        return "Старая VPN"
    return "Неизвестно"


def load_shops():
    """Загружает магазины из JSON или возвращает пустой список, если файла нет."""
    if not os.path.exists(SHOP_LIST_JSON):
        return []

    with open(SHOP_LIST_JSON, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_shops(shops):
    """Сохраняет магазины в JSON."""
    os.makedirs("shops", exist_ok=True)  # Создаем папку, если ее нет
    with open(SHOP_LIST_JSON, "w", encoding="utf-8") as f:
        json.dump(shops, f, ensure_ascii=False, indent=2)


def update_shop_list():
    shops = load_shops()

    # Если файл пустой, можно загрузить начальные данные (опционально)
    if not shops:
        shops = [{"name": "shop123", "ip": "192.168.1.1", "vpn": "Новая VPN"}]  # Пример

    updated_shops = []

    for shop in shops:
        shop_name = shop["name"]
        old_ip = shop["ip"]
        old_vpn = shop["vpn"]

        # Извлекаем номер магазина
        shop_num_match = re.search(r"shop(\d+)", shop_name)
        if not shop_num_match:
            updated_shops.append(shop)
            continue

        shop_num = shop_num_match.group(1)

        # Пингуем магазин
        current_ip = ping_shop(shop_name)

        # Определяем VPN
        if current_ip:
            vpn_status = determine_vpn(current_ip, shop_num)
        else:
            current_ip = old_ip  # Сохраняем старый IP, если пинг не удался
            vpn_status = old_vpn

        updated_shops.append(
            {
                "name": shop_name,
                "ip": current_ip,
                "vpn": vpn_status,
                "last_checked": datetime.now().isoformat(),  # Доп. поле для логов
            }
        )

    save_shops(updated_shops)
    print(f"✅ Данные обновлены: {datetime.now()}")


def main():
    while True:
        update_shop_list()
        time.sleep(3600)  # Проверка раз в час


if __name__ == "__main__":
    main()
