import subprocess
import threading


def stream_output(process, name):
    for line in process.stdout:
        print(f"[{name}] {line.rstrip()}")


processes = []
scripts = [("main.py", "МОРДА"), ("ping.py", "PING"), ("shift_watcher.py", "СМЕНЫ")]

for script, name in scripts:
    p = subprocess.Popen(
        ["python", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,  # Включаем текстовый режим, чтобы построчная буферизация работала
    )
    t = threading.Thread(target=stream_output, args=(p, name))
    t.start()
    processes.append((p, t))

# Ждем завершения всех потоков
for p, t in processes:
    p.wait()
    t.join()
