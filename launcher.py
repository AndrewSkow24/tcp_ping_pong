"""
Лаунчер для запуска сервера и клиентов в отдельных процессах.
"""
import subprocess
import sys
import time
import signal
import os
from typing import List

# Пути к файлам
SERVER_SCRIPT = "server.py"
CLIENT_SCRIPT = "client.py"
LOGS_DIR = "logs"


def create_logs_dir():
    """Создание директории для логов."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    print(f"Директория для логов: {LOGS_DIR}")


def start_server(timeout: int = 300) -> subprocess.Popen:
    """
    Запуск сервера в отдельном процессе.

    Args:
        timeout: Время работы в секундах

    Returns:
        Объект процесса сервера
    """
    cmd = [
        sys.executable, SERVER_SCRIPT,
        "--host", "127.0.0.1",
        "--port", "8888",
        "--log", "logs/server.log",
        "--timeout", str(timeout)
    ]

    print("Запуск сервера...")
    print(f"Команда: {' '.join(cmd)}")

    # Запускаем сервер в отдельном процессе
    # Используем PIPE для перенаправления вывода
    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Даём серверу время на запуск
    time.sleep(2)

    if server_process.poll() is not None:
        # Сервер завершился с ошибкой
        print("Ошибка: сервер не запустился")
        stdout, _ = server_process.communicate()
        print(f"Вывод сервера:\n{stdout}")
        sys.exit(1)

    print("Сервер успешно запущен")
    return server_process


def start_client(client_id: int, timeout: int = 300) -> subprocess.Popen:
    """
    Запуск клиента в отдельном процессе.

    Args:
        client_id: ID клиента
        timeout: Время работы в секундах

    Returns:
        Объект процесса клиента
    """
    log_file = f"logs/client_{client_id}.log"

    cmd = [
        sys.executable, CLIENT_SCRIPT,
        "--id", str(client_id),
        "--host", "127.0.0.1",
        "--port", "8888",
        "--log", log_file,
        "--timeout", str(timeout)
    ]

    print(f"Запуск клиента #{client_id}...")
    print(f"Команда: {' '.join(cmd)}")

    # Запускаем клиента в отдельном процессе
    client_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Даём клиенту время на подключение
    time.sleep(1)

    if client_process.poll() is not None:
        # Клиент завершился с ошибкой
        print(f"Ошибка: клиент #{client_id} не запустился")
        stdout, _ = client_process.communicate()
        print(f"Вывод клиента #{client_id}:\n{stdout}")

    print(f"Клиент #{client_id} запущен")
    return client_process


def monitor_processes(processes: List[subprocess.Popen], timeout: int):
    """
    Мониторинг процессов и их вывода.

    Args:
        processes: Список процессов для мониторинга
        timeout: Максимальное время работы в секундах
    """
    print(f"\nМониторинг процессов в течение {timeout} секунд...")
    print("Нажмите Ctrl+C для досрочной остановки")
    print("-" * 50)

    start_time = time.time()

    try:
        while time.time() - start_time < timeout:
            # Проверяем вывод всех процессов
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    # Процесс завершился
                    stdout, _ = process.communicate()
                    if stdout:
                        if i == 0:
                            print(f"\nСервер завершился:\n{stdout}")
                        else:
                            print(f"\nКлиент #{i} завершился:\n{stdout}")
                    continue

                # Читаем вывод, если есть
                try:
                    output = process.stdout.readline()
                    if output:
                        # Выводим с префиксом для идентификации
                        if i == 0:
                            print(f"[Сервер] {output.rstrip()}")
                        else:
                            print(f"[Клиент#{i}] {output.rstrip()}")
                except:
                    pass

            time.sleep(0.1)

        print(f"\nВремя работы ({timeout} секунд) истекло")

    except KeyboardInterrupt:
        print("\nПолучен сигнал прерывания, останавливаем процессы...")
    finally:
        # Останавливаем все процессы
        for i, process in enumerate(processes):
            if process.poll() is None:  # Если процесс ещё работает
                if i == 0:
                    print("Остановка сервера...")
                else:
                    print(f"Остановка клиента #{i}...")

                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        print("Все процессы остановлены")


def main():
    """Основная функция запуска."""
    import argparse

    parser = argparse.ArgumentParser(description='Лаунчер для TCP PING-PONG')
    parser.add_argument('--timeout', type=int, default=300,
                        help='Время работы в секундах (по умолчанию 300 = 5 минут)')
    parser.add_argument('--clients', type=int, default=2,
                        help='Количество клиентов (по умолчанию 2)')
    parser.add_argument('--debug', action='store_true',
                        help='Включить отладочный вывод')

    args = parser.parse_args()

    print("=" * 60)
    print("TCP PING-PONG Лаунчер")
    print("=" * 60)
    print(f"Время работы: {args.timeout} секунд ({args.timeout / 60:.1f} минут)")
    print(f"Количество клиентов: {args.clients}")
    print("=" * 60)

    # Создаём директорию для логов
    create_logs_dir()

    # Собираем аргументы для процессов
    common_args = []
    if args.debug:
        common_args = ["--debug"]

    processes = []

    try:
        # Запускаем сервер
        server_cmd = [sys.executable, SERVER_SCRIPT,
                      "--host", "127.0.0.1",
                      "--port", "8888",
                      "--log", "logs/server.log",
                      "--timeout", str(args.timeout)] + common_args

        print(f"\nЗапуск сервера: {' '.join(server_cmd)}")
        server_process = subprocess.Popen(
            server_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(("server", server_process))

        # Даём серверу время на запуск
        time.sleep(2)

        # Проверяем, запустился ли сервер
        if server_process.poll() is not None:
            print("Ошибка: сервер не запустился")
            stdout, _ = server_process.communicate()
            print(f"Вывод сервера:\n{stdout}")
            sys.exit(1)

        print("Сервер запущен")

        # Запускаем клиентов
        for client_id in range(1, args.clients + 1):
            client_cmd = [sys.executable, CLIENT_SCRIPT,
                          "--id", str(client_id),
                          "--host", "127.0.0.1",
                          "--port", "8888",
                          "--log", f"logs/client_{client_id}.log",
                          "--timeout", str(args.timeout)] + common_args

            print(f"\nЗапуск клиента #{client_id}: {' '.join(client_cmd)}")
            client_process = subprocess.Popen(
                client_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            processes.append((f"client_{client_id}", client_process))

            # Небольшая задержка между запуском клиентов
            time.sleep(0.5)

        print(f"\nВсе процессы запущены. Работаем {args.timeout} секунд...")
        print("Нажмите Ctrl+C для досрочной остановки")
        print("-" * 50)

        # Мониторим процессы
        start_time = time.time()

        # Читаем вывод процессов
        while time.time() - start_time < args.timeout:
            all_done = True

            for name, process in processes:
                if process.poll() is None:
                    all_done = False

                    # Пробуем прочитать строку вывода
                    try:
                        line = process.stdout.readline()
                        if line:
                            print(f"[{name}] {line.rstrip()}")
                    except:
                        pass

            if all_done:
                print("\nВсе процессы завершились")
                break

            time.sleep(0.1)

        print(f"\nВремя работы ({args.timeout} секунд) истекло")

    except KeyboardInterrupt:
        print("\n\nПолучен Ctrl+C, останавливаем процессы...")
    finally:
        # Останавливаем все процессы
        print("\nЗавершение работы...")
        for name, process in processes:
            if process.poll() is None:  # Если процесс ещё работает
                print(f"Останавливаем {name}...")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    print(f"Принудительно завершаем {name}...")
                    process.kill()

        print("\nВсе процессы остановлены")
        print("\nЛоги сохранены в директории 'logs':")
        print("  - server.log - логи сервера")
        for client_id in range(1, args.clients + 1):
            print(f"  - client_{client_id}.log - логи клиента #{client_id}")
        print("\nЗавершение работы лаунчера")


if __name__ == '__main__':
    main()