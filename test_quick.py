"""
Быстрый тест для проверки работы системы.
Запускает сервер и двух клиентов на 15 секунд.
"""

import subprocess
import time
import os
import sys


def run_quick_test():
    """Запуск быстрого теста."""
    print("Запуск быстрого теста (15 секунд)...")

    # Убедимся, что директория logs существует
    os.makedirs("logs", exist_ok=True)

    # Запускаем сервер в фоне
    print("Запуск сервера...")
    server = subprocess.Popen(
        [sys.executable, "server.py", "--timeout", "20"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Даём серверу время запуститься
    time.sleep(2)

    # Запускаем клиентов
    print("Запуск клиента 1...")
    client1 = subprocess.Popen(
        [sys.executable, "client.py", "--id", "1", "--timeout", "15"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    time.sleep(0.5)

    print("Запуск клиента 2...")
    client2 = subprocess.Popen(
        [sys.executable, "client.py", "--id", "2", "--timeout", "15"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print("\nСистема работает... Ждём 15 секунд")

    # Ждём завершения клиентов
    client1.wait()
    client2.wait()

    # Останавливаем сервер
    server.terminate()
    server.wait()

    print("\nТест завершён!")
    print("\nПроверка логов:")

    # Показываем первые несколько строк каждого лога
    log_files = ["logs/server.log", "logs/client_1.log", "logs/client_2.log"]

    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n=== {log_file} (первые 5 строк) ===")
            with open(log_file, "r") as f:
                lines = f.readlines()[:5]
                for line in lines:
                    print(line.rstrip())
            # Показываем статистику
            with open(log_file, "r") as f:
                content = f.read()
                if log_file == "logs/server.log":
                    ignored = content.count("проигнорировано")
                    print(f"Игнорированных запросов: {ignored}")
                else:
                    timeouts = content.count("таймаут")
                    keepalives = content.count("keepalive")
                    print(f"Таймаутов: {timeouts}, Keepalive: {keepalives}")
        else:
            print(f"\nФайл {log_file} не найден")

    print("\nТест завершён успешно!")


if __name__ == "__main__":
    run_quick_test()
