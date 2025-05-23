import psycopg2
from psycopg2 import sql
import json
from datetime import datetime
import os
import time
import threading

# Конфигурация подключения к БД
DB_CONFIG = {
    'host': '192.168.0.200',
    'port': 5438,
    'user': 'postgres',
    'password': 'user',
    'main_db': 'main',
    'docs_db': 'docs'
}

# Пути к файлам
USERS_FILE = 'users.json'
SHOPS_SMEN_FILE = 'shops_smen.json'

# Интервал обновления в секундах (5 минут)
UPDATE_INTERVAL = 300


def connect_to_db(database):
    """Установка соединения с PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=database
        )
        return conn
    except Exception as e:
        print(f"Ошибка подключения к базе {database}: {e}")
        return None


def fetch_users_data():
    """Получение данных о кассирах из таблицы user_entity"""
    conn = connect_to_db(DB_CONFIG['main_db'])
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT data FROM user_entity")
            users = cursor.fetchall()
            return [user[0] for user in users] if users else []
    except Exception as e:
        print(f"Ошибка при получении данных пользователей: {e}")
        return []
    finally:
        conn.close()


def save_users_to_file(users_data):
    """Сохранение данных о пользователях в файл users.json"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        print(f"Данные пользователей сохранены в {USERS_FILE}")
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")


def load_users_from_file():
    """Загрузка данных о пользователях из файла"""
    if not os.path.exists(USERS_FILE):
        return []

    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке файла пользователей: {e}")
        return []


def check_today_shifts():
    """Проверка открытых смен на сегодня"""
    conn = connect_to_db(DB_CONFIG['docs_db'])
    if not conn:
        return None

    today = datetime.now().strftime('%Y-%m-%d')
    open_shifts = {}

    try:
        with conn.cursor() as cursor:
            query = sql.SQL("""
                SELECT data FROM openshiftdocument_entity 
                WHERE data->>'Open' LIKE %s
            """)
            cursor.execute(query, [f'%{today}%'])
            shifts = cursor.fetchall()

            for shift in shifts:
                shift_data = shift[0]
                open_data = shift_data.get('Open', {})
                user_code = open_data.get('UserCode')

                if user_code:
                    if user_code not in open_shifts:
                        open_shifts[user_code] = []
                    open_shifts[user_code].append(shift_data)

    except Exception as e:
        print(f"Ошибка при проверке смен: {e}")
    finally:
        conn.close()

    return open_shifts


def generate_shift_report(open_shifts, users_data):
    """Генерация отчета по открытым сменам с учетом магазинов"""
    report = {}

    users_by_code = {user['Code']: user for user in users_data}

    for user_code, shifts in open_shifts.items():
        user = users_by_code.get(user_code)
        if not user:
            continue

        user_shops = user.get('Shops', [])
        user_name = user.get('Name', 'Неизвестно')

        for shop_code in user_shops:
            normalized_shop_code = str(int(shop_code)) if shop_code.isdigit() else shop_code

            if normalized_shop_code not in report:
                report[normalized_shop_code] = {
                    'is_shift_open': False,
                    'cashiers': []
                }

            report[normalized_shop_code]['is_shift_open'] = True
            report[normalized_shop_code]['cashiers'].append({
                'user_code': user_code,
                'user_name': user_name
            })

    return report


def save_shifts_report(report):
    """Сохранение отчета о сменах в файл в заданном формате"""
    now = datetime.now().isoformat()
    result = []

    for shop_code, shop_data in report.items():
        shop_entry = {
            "name": f"shop{shop_code}",
            "is_shift_open": shop_data['is_shift_open'],
            "cashiers": shop_data['cashiers'],
            "last_checked": now
        }
        result.append(shop_entry)

    try:
        with open(SHOPS_SMEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nОтчет о сменах сохранен в {SHOPS_SMEN_FILE}")
    except Exception as e:
        print(f"Ошибка при сохранении отчета: {e}")


def print_report(report):
    """Вывод отчета в консоль"""
    print("\nОтчет по открытым сменам на сегодня:")
    for shop_code, shop_data in sorted(report.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        status = "ОТКРЫТА" if shop_data['is_shift_open'] else "НЕ ОТКРЫТА"

        if shop_data['is_shift_open']:
            cashiers = ", ".join([f"{c['user_name']} (код: {c['user_code']})"
                                  for c in shop_data['cashiers']])
            print(f"Магазин {shop_code}: Смена {status} - {cashiers}")
        else:
            print(f"Магазин {shop_code}: Смена {status}")


def update_data():
    """Основная функция обновления данных"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Обновление данных...")

    # 1. Получаем данные о пользователях и сохраняем в файл
    users_data = fetch_users_data()
    if users_data:
        save_users_to_file(users_data)
    else:
        print("Не удалось получить данные пользователей, загружаем из файла")
        users_data = load_users_from_file()
        if not users_data:
            print("Нет данных о пользователях для работы")
            return

    # 2. Проверяем открытые смены на сегодня
    open_shifts = check_today_shifts()

    # 3. Генерируем отчет с учетом магазинов
    report = generate_shift_report(open_shifts, users_data)

    # 4. Сохраняем отчет в файл
    save_shifts_report(report)

    # 5. Выводим результаты в консоль
    print_report(report)

    # Запланировать следующее обновление
    threading.Timer(UPDATE_INTERVAL, update_data).start()


def main():
    # Первое обновление при запуске
    update_data()

    # Бесконечный цикл для поддержания работы программы
    while True:
        time.sleep(1)


if __name__ == "__main__":
    print("Скрипт мониторинга смен запущен")
    print(f"Обновление данных будет происходить каждые {UPDATE_INTERVAL // 60} минут")
    try:
        main()
    except KeyboardInterrupt:
        print("\nСкрипт остановлен пользователем")