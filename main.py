from flask import Flask, render_template_string, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
import platform
import logging
from concurrent.futures import ThreadPoolExecutor
import os
import time
from datetime import datetime
import json

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Путь к файлу с IP магазинов
SHOP_LIST_PATH = r"shop_list.json"

# Загрузка IP магазинов из файла
stores = {}
last_modified_time = 0


def load_store_ips():
    global stores, last_modified_time
    try:
        current_modified_time = os.path.getmtime(SHOP_LIST_PATH)
        if current_modified_time <= last_modified_time:
            return

        last_modified_time = current_modified_time

        temp_stores = {}
        if not os.path.exists(SHOP_LIST_PATH):
            logging.error("JSON файл списка магазинов не найден!")
            return

        with open(SHOP_LIST_PATH, 'r', encoding='utf-8') as file:
            shops_data = json.load(file)
            for shop in shops_data:
                store = shop["name"]
                ip = shop["ip"]
                vpn_type = shop["vpn"]

                # Сохраняем предыдущий статус
                old_status = stores.get(store, {}).get('status', 'Unknown')
                old_router = stores.get(store, {}).get('router', 'Unknown')

                temp_stores[store] = {
                    'ip': ip,
                    'vpn': vpn_type,
                    'status': old_status,
                    'router': old_router,
                    'last_updated': datetime.now().strftime('%H:%M:%S')
                }

        stores.clear()
        stores.update(temp_stores)
        logging.info("Список магазинов обновлен из JSON.")

    except Exception as e:
        logging.error(f"Ошибка при загрузке JSON файла: {e}")


def ping(target):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout = '-w' if platform.system().lower() == 'windows' else '-W'
    timeout_value = '3000' if platform.system().lower() == 'windows' else '3'
    try:
        response = subprocess.run(['ping', param, '1', timeout, timeout_value, target],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
        return 'ttl=' in response.stdout.lower() or 'ответ от' in response.stdout.lower()
    except Exception as e:
        logging.error(f'Ошибка пинга {target}: {e}')
        return False


def check_store(store, data):
    store_ip = data['ip']
    vpn_type = data['vpn']

    if ping(store_ip):
        stores[store]['status'] = 'Online'
        stores[store]['router'] = 'Работает'
        stores[store]['last_updated'] = datetime.now().strftime('%H:%M:%S')
        return

    stores[store]['status'] = 'Offline'
    stores[store]['last_updated'] = datetime.now().strftime('%H:%M:%S')

    if vpn_type == 'Новая VPN':
        router_ip = f"{'.'.join(store_ip.split('.')[:3])}.254"
        if ping(router_ip):
            stores[store]['router'] = 'Касса не в сети'
        else:
            stores[store]['router'] = 'Роутер не в сети'
    else:
        stores[store]['router'] = 'Требуется проверка'


def ping_stores():
    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(lambda s: check_store(s, stores[s]), stores.keys())


# Настройка планировщика
scheduler = BackgroundScheduler()
scheduler.add_job(ping_stores, 'interval', seconds=10)
scheduler.add_job(load_store_ips, 'interval', minutes=30)
scheduler.start()

# Загрузка IP перед стартом
load_store_ips()

# Modern UI Template with Dark Mode
html_template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <link rel="icon" href="{{ url_for('static', filename='img/favicon.png') }}" type="image/png">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мониторинг магазинов</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script>
        // Проверка системной темы
        function getSystemTheme() {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }

        // Проверка сохраненной темы в localStorage
        function getSavedTheme() {
            return localStorage.getItem('theme');
        }

        // Установка темы
        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            updateThemeButton(theme);
        }

        // Обновление кнопки переключения темы
        function updateThemeButton(theme) {
            const btn = document.getElementById('theme-toggle');
            if (btn) {
                btn.innerHTML = theme === 'dark' 
                    ? '<i class="fas fa-sun"></i>' 
                    : '<i class="fas fa-moon"></i>';
            }
        }

        // Инициализация темы при загрузке
        function initTheme() {
            const savedTheme = getSavedTheme();
            const systemTheme = getSystemTheme();
            const theme = savedTheme || systemTheme;
            setTheme(theme);
        }

        // Переключение темы
        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        }

        document.addEventListener('DOMContentLoaded', initTheme);
    </script>
    <style>
        :root {
            --primary: #4361ee;
            --primary-light: #5e7bf1;
            --success: #4cc9f0;
            --warning: #f8961e;
            --danger: #f94144;

            /* Light theme */
            --bg-light: #f5f7fa;
            --card-light: #ffffff;
            --text-light: #212529;
            --border-light: #e9ecef;
            --muted-light: #6c757d;

            /* Dark theme */
            --bg-dark: #121212;
            --card-dark: #1e1e1e;
            --text-dark: #e0e0e0;
            --border-dark: #333333;
            --muted-dark: #9e9e9e;
        }

        [data-theme="light"] {
            --bg: var(--bg-light);
            --card: var(--card-light);
            --text: var(--text-light);
            --border: var(--border-light);
            --muted: var(--muted-light);
        }

        [data-theme="dark"] {
            --bg: var(--bg-dark);
            --card: var(--card-dark);
            --text: var(--text-dark);
            --border: var(--border-dark);
            --muted: var(--muted-dark);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        body {
            font-family: 'Roboto', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }

        /* Стилизация скроллбара для прокручиваемой таблицы */
div[style*="overflow-y: auto"]::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

div[style*="overflow-y: auto"]::-webkit-scrollbar-track {
    background-color: var(--bg); /* Адаптивный фон под тему */
    border-radius: 8px;
}

div[style*="overflow-y: auto"]::-webkit-scrollbar-thumb {
    background-color: var(--muted); /* Цвет ползунка */
    border-radius: 8px;
    border: 2px solid transparent;
    background-clip: content-box;
    transition: background-color 0.3s ease;
}

div[style*="overflow-y: auto"]::-webkit-scrollbar-thumb:hover {
    background-color: var(--primary); /* Синяя подсветка при наведении */
}

/* Firefox поддержка */
div[style*="overflow-y: auto"] {
    scrollbar-color: var(--muted) var(--bg);
    scrollbar-width: thin;
}

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: linear-gradient(135deg, var(--primary) 0%, #3a0ca3 100%);
            color: white;
            padding: 20px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            display: flex;
            align-items: center;
            font-size: 1.5rem;
            font-weight: 700;
        }

        .logo i {
            margin-right: 10px;
            font-size: 1.8rem;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .theme-toggle {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: inherit;
        }

        .theme-toggle:hover {
            background: rgba(255,255,255,0.3);
        }

        .stats {
            display: flex;
            gap: 20px;
        }

        .stat-card {
            background: rgba(255,255,255,0.2);
            padding: 10px 15px;
            border-radius: 8px;
            display: flex;
            align-items: center;
        }

        .stat-card i {
            margin-right: 8px;
        }

        .dashboard {
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 20px;
        }

        .sidebar {
    background: var(--card);
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    height: fit-content;
    border: 1px solid var(--border);
    transition:
        box-shadow 0.4s ease,
        border-color 0.4s ease,
        background-color 0.4s ease;
}

.sidebar:hover {
    box-shadow: 0 0 15px rgba(67, 97, 238, 0.4);
    border-color: var(--primary);
}

        .sidebar h3 {
            margin-bottom: 15px;
            color: var(--primary);
            font-size: 1.1rem;
        }

        .filter-group {
            margin-bottom: 20px;
        }

        .filter-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text);
        }

        select, input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-family: inherit;
            background: var(--card);
            color: var(--text);
        }

        .main-content {
    background: var(--card);
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    border: 1px solid var(--border);
    transition:
        box-shadow 0.4s ease,
        border-color 0.4s ease,
        background-color 0.4s ease;
}

.main-content:hover {
    box-shadow: 0 0 15px rgba(67, 97, 238, 0.4);
    border-color: var(--primary);
}

        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .table-header h2 {
            color: var(--text);
        }

        .search-box {
            position: relative;
            width: 300px;
        }

        .search-box input {
            padding-left: 35px;
        }

        .search-box i {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--muted);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            padding: 12px 15px;
            background-color: var(--primary);
            color: white;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.5px;
        }

        td {
            padding: 15px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
            color: var(--text);
        }

        tr:last-child td {
            border-bottom: none;
        }

        .status {
            display: inline-flex;
            align-items: center;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .status i {
            margin-right: 5px;
            font-size: 0.7rem;
        }

        .online {
            background-color: rgba(76, 201, 240, 0.1);
            color: var(--success);
        }

        .online i {
            color: var(--success);
        }

        .offline {
            background-color: rgba(249, 65, 68, 0.1);
            color: var(--danger);
        }

        .offline i {
            color: var(--danger);
        }

        .unknown {
            background-color: rgba(248, 150, 30, 0.1);
            color: var(--warning);
        }

        .router-status {
            display: flex;
            align-items: center;
        }

        .router-status i {
            margin-right: 8px;
        }

        .fa-check-circle {
            color: var(--success);
        }

        .fa-exclamation-circle {
            color: var(--warning);
        }

        .fa-times-circle {
            color: var(--danger);
        }

        .last-updated {
            color: var(--muted);
            font-size: 0.85rem;
        }

        .refresh-info {
            text-align: right;
            margin-top: 10px;
            color: var(--muted);
            font-size: 0.85rem;
        }

        @media (max-width: 1200px) {
            .dashboard {
                grid-template-columns: 1fr;
            }

            .stats {
                flex-wrap: wrap;
            }
        }

        /* Анимации */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        tr {
            animation: fadeIn 0.3s ease-out forwards;
            opacity: 0;
        }

        tr:nth-child(1) { animation-delay: 0.1s; }
        tr:nth-child(2) { animation-delay: 0.2s; }
        tr:nth-child(3) { animation-delay: 0.3s; }
        tr:nth-child(4) { animation-delay: 0.4s; }
        tr:nth-child(5) { animation-delay: 0.5s; }

        .pulse {
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(67, 97, 238, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(67, 97, 238, 0); }
            100% { box-shadow: 0 0 0 0 rgba(67, 97, 238, 0); }
        }

        @keyframes pulse-red {
    0% { box-shadow: 0 0 0 0 rgba(249, 65, 68, 0.4); }
    70% { box-shadow: 0 0 0 10px rgba(249, 65, 68, 0); }
    100% { box-shadow: 0 0 0 0 rgba(249, 65, 68, 0); }
}

.pulse-red {
    animation: pulse-red 1.5s infinite;
}
}
    </style>
</head>
<body>
    <header>
        <div class="container header-content">
            <div class="logo">
                <i class="fas fa-store-alt"></i>
                <span>Мониторинг магазинов</span>
            </div>
            <div class="header-actions">
                <div class="stats">
                    <div class="stat-card">
                        <i class="fas fa-wifi"></i>
                        <span id="total-stores">{{ stores|length }} магазинов</span>
                    </div>
                    <div class="stat-card">
                        <i class="fas fa-check-circle"></i>
                        <span id="online-stores">{{ online_count }} онлайн</span>
                    </div>
                    <div class="stat-card">
                        <i class="fas fa-exclamation-circle"></i>
                        <span id="offline-stores">{{ offline_count }} оффлайн</span>
                    </div>
                </div>
                <button id="theme-toggle" class="theme-toggle" onclick="toggleTheme()">
                    <i class="fas fa-moon"></i> Темная тема
                </button>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="dashboard">
            <div class="sidebar">
                <div class="filter-group">
                    <h3><i class="fas fa-filter"></i> Фильтры</h3>
                    <label for="status-filter">Статус</label>
                    <select id="status-filter">
                        <option value="all">Все</option>
                        <option value="online">Online</option>
                        <option value="offline">Offline</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="vpn-filter">Тип VPN</label>
                    <select id="vpn-filter">
                        <option value="all">Все</option>
                        <option value="new">Новая VPN</option>
                        <option value="old">Старая VPN</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="search-store">Поиск магазина</label>
                    <input type="text" id="search-store" placeholder="Номер магазина...">
                </div>
            </div>

            <div class="main-content">
                <div class="table-header">
                    <h2><i class="fas fa-list"></i> Список магазинов</h2>
                    <div class="search-box">
                        <i class="fas fa-search"></i>
                    </div>
                </div>

               <table style="width: 100%; table-layout: fixed; border-collapse: collapse;">
    <thead>
        <tr>
            <th>Магазин</th>
            <th>Статус</th>
            <th>Роутер</th>
            <th>Обновлено</th>
        </tr>
    </thead>
</table>

<!-- Прокручиваемое тело таблицы -->
<div style="max-height: 600px; overflow-y: auto;">
    <table style="width: 100%; table-layout: fixed; border-collapse: collapse;">
        <tbody id="stores-table">
            {% for store, data in stores.items() %}
            <tr id="{{ store }}" class="{{ data.status|lower }}" data-vpn="{{ data.vpn }}">
                <td>
                    <strong>{{ store[4:] }}</strong><br>
                    <small>{{ data.ip }}</small>
                </td>
                <td>
                    <span class="status">
                        {% if data.status == 'Online' %}
                            <i class="fas fa-circle"></i> Online
                        {% else %}
                            <i class="fas fa-circle"></i> Offline
                        {% endif %}
                    </span>
                </td>
                <td>
                    <div class="router-status">
                        {% if data.router == 'Работает' %}
                            <i class="fas fa-check-circle"></i>
                        {% elif data.router == 'Касса offline' %}
                            <i class="fas fa-exclamation-circle"></i>
                        {% else %}
                            <i class="fas fa-times-circle"></i>
                        {% endif %}
                        {{ data.router }}
                    </div>
                </td>
                <td class="last-updated">{{ data.last_updated }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

                <div class="refresh-info">
                    <i class="fas fa-info-circle"></i> Данные обновляются автоматически каждые 10 секунд
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script>
        function fetchStatus() {
            $.get('/status', function(data) {
                // Обновляем статистику
                const total = Object.keys(data).length;
                const online = Object.values(data).filter(x => x.status === 'Online').length;

                $('#total-stores').text(total + ' магазинов');
                $('#online-stores').text(online + ' онлайн');
                $('#offline-stores').text((total - online) + ' оффлайн');

                // Обновляем таблицу
                for (const [store, info] of Object.entries(data)) {
                    const row = $('#' + store);
                    if (row.length) {
                        // Обновляем класс строки
                        row.removeClass('online offline unknown').addClass(info.status.toLowerCase());

                        // Обновляем статус
                        const statusCell = row.find('td:nth-child(2) .status');
                        statusCell.html(info.status === 'Online' 
                            ? '<i class="fas fa-circle"></i> Online' 
                            : '<i class="fas fa-circle"></i> Offline');

                        // Обновляем статус роутера
                        const routerCell = row.find('td:nth-child(3) .router-status');
                        let icon = '';
                        if (info.router === 'Работает') {
                            icon = '<i class="fas fa-check-circle"></i>';
                        } else if (info.router === 'Касса offline') {
                            icon = '<i class="fas fa-exclamation-circle"></i>';
                        } else {
                            icon = '<i class="fas fa-times-circle"></i>';
                        }
                        routerCell.html(icon + info.router);

                        // Обновляем время
                        row.find('td:nth-child(4)').text(info.last_updated);
                    }
                }
            });
        }

        // Автоматическое обновление каждые 10 секунд
        setInterval(fetchStatus, 10000);

        // Ручное обновление по кнопке
        $('#refresh-btn').click(function() {
    const btn = $(this);

    // Сохраняем исходные значения
    const originalText = btn.html();
    const originalColor = btn.css('background-color');

    // Меняем стиль и текст
    btn
    .html('<i class="fas fa-sync-alt fa-spin"></i> Идёт обновление...')
    .css('background-color', '#f94144')  // красный
    .removeClass('pulse')
    .addClass('pulse-red');


    fetchStatus();

    // Возврат через 2 секунды
    setTimeout(() => {
        btn
            .html('<i class="fas fa-sync-alt"></i> Обновить')
    .css('background-color', 'var(--primary)')
    .removeClass('pulse-red')
            .addClass('pulse'); // чтобы пульсация осталась
    }, 2000);
});

        // Поиск и фильтрация
        $('#global-search, #search-store').keyup(function() {
            const search = $(this).val().toLowerCase();
            $('#stores-table tr').each(function() {
                const storeNum = $(this).attr('id').substring(4);
                $(this).toggle(storeNum.includes(search));
            });
        });

        $('#status-filter, #vpn-filter').change(function() {
            const status = $('#status-filter').val();
            const vpn = $('#vpn-filter').val();

            $('#stores-table tr').each(function() {
                const row = $(this);
                const rowStatus = row.hasClass('online') ? 'online' : 'offline';
                const rowVpn = row.data('vpn') === 'Новая VPN' ? 'new' : 'old';

                const statusMatch = status === 'all' || rowStatus === status;
                const vpnMatch = vpn === 'all' || rowVpn === vpn;

                row.toggle(statusMatch && vpnMatch);
            });
        });

        // Инициализация
        $(document).ready(function() {
            fetchStatus();
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    online_count = sum(1 for data in stores.values() if data.get('status') == 'Online')
    offline_count = len(stores) - online_count

    return render_template_string(html_template,
                                  stores=stores,
                                  online_count=online_count,
                                  offline_count=offline_count)


@app.route('/status')
def status():
    return jsonify({
        store: {
            **data,
            'vpn': data['vpn']
        } for store, data in stores.items()
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)