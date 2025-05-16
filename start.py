import subprocess

# Запускаем Flask-приложение
flask_proc = subprocess.Popen(["python", "main.py"])

# Запускаем ping.py
ping_proc = subprocess.Popen(["python", "ping.py"])

# Ждём завершения обоих
flask_proc.wait()
ping_proc.wait()