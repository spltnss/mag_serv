import psycopg2
import json
from datetime import datetime
import sys
import time

DB_CONFIG = {
    "host": "192.168.0.200",
    "port": 5438,
    "user": "postgres",
    "password": "user",
    "main_db": "main",
    "docs_db": "docs",
}

EXCLUDED_SHOPS = {"1", "97"}
STATIC_POSCODES = {"1": "700123", "1z": "2001", "97": "2097"}


def connect_to_db(dbname):
    try:
        return psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=dbname,
        )
    except Exception as e:
        print(f"Ошибка подключения к базе {dbname}: {e}", file=sys.stderr)
        return None


def strip_leading_zeros(s):
    return str(int(s)) if s.isdigit() else s


def fetch_poscards():
    conn = connect_to_db(DB_CONFIG["main_db"])
    poscards = {}
    if not conn:
        return poscards

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM poscard_settings")
            for (data,) in cur.fetchall():
                shop_raw = str(data.get("Shop", "")).strip()
                code = str(data.get("Code", "")).strip()
                if not shop_raw or not code or shop_raw in EXCLUDED_SHOPS:
                    continue
                shop = strip_leading_zeros(shop_raw)
                poscards[code] = {"shop": shop, "name": f"shop{shop}"}

        for shop, code in STATIC_POSCODES.items():
            poscards[code] = {"shop": shop, "name": f"shop{shop}"}
    finally:
        conn.close()

    return poscards


def fetch_users():
    conn = connect_to_db(DB_CONFIG["main_db"])
    users = []
    if not conn:
        return users

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM user_entity")
            for (data,) in cur.fetchall():
                shops = []
                if "Shop" in data and data["Shop"]:
                    shops = [str(data["Shop"])]
                elif "Shops" in data and isinstance(data["Shops"], list):
                    shops = [str(s) for s in data["Shops"] if s]
                data["__shops__"] = [strip_leading_zeros(s) for s in shops]
                users.append(data)
    finally:
        conn.close()

    return users


def fetch_today_transactions(tranztype):
    conn = connect_to_db(DB_CONFIG["docs_db"])
    tx = []
    if not conn:
        return tx

    today = datetime.now().date()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT unitcode, seller FROM doctransaction_entity "
                "WHERE tranztype = %s AND tranzdate::date = %s",
                (tranztype, today),
            )
            for unitcode, seller in cur.fetchall():
                tx.append((str(unitcode).strip(), str(seller).strip()))
    finally:
        conn.close()

    return tx


def generate_shift_report(trans62, trans64, users, poscards):
    report = {}
    users_by_code = {u["Code"]: u for u in users}

    # Собиратель всех seller по unitcode
    sellers_by_unit = {}
    for unitcode, seller in trans62 + trans64:
        sellers_by_unit.setdefault(unitcode, set()).add(seller)

    # Для каждого poscard
    for code, info in poscards.items():
        shop_name = info["name"]
        sellers = sellers_by_unit.get(code, set())

        if sellers:
            cashiers = []
            for seller in sorted(sellers):
                user = users_by_code.get(seller)
                uname = user.get("Name", "Неизвестно") if user else "Неизвестно"
                cashiers.append({"user_code": seller, "user_name": uname})
            report[shop_name] = {"is_shift_open": True, "cashiers": cashiers}
        else:
            report[shop_name] = {"is_shift_open": False, "cashiers": []}

    return report


def save_shift_report(report, filename="shops_smen.json"):
    now_iso = datetime.now().isoformat()
    out = []
    for shop_name, data in sorted(report.items()):
        out.append(
            {
                "name": shop_name,
                "is_shift_open": data["is_shift_open"],
                "cashiers": data["cashiers"],
                "last_checked": now_iso,
            }
        )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def print_report(report):
    print("Отчет по сменам:")
    for shop_name, data in sorted(report.items()):
        if data["is_shift_open"]:
            for c in data["cashiers"]:
                print(
                    f"{shop_name}: Смена ОТКРЫТА — {c['user_name']} (код: {c['user_code']})"
                )
        else:
            print(f"{shop_name}: Смена НЕ ОТКРЫТА")


def main():
    while True:
        try:
            poscards = fetch_poscards()
            users = fetch_users()
            t62 = fetch_today_transactions(62)
            t64 = fetch_today_transactions(64)

            report = generate_shift_report(t62, t64, users, poscards)
            save_shift_report(report)
            print_report(report)

            print("\nЖдём 10 секунд до следующего обновления...\n")
            time.sleep(10)
        except Exception as e:
            print(f"Ошибка во время обновления: {e}", file=sys.stderr)
            time.sleep(10)


if __name__ == "__main__":
    main()
