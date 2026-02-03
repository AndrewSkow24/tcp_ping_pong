"""
TCP сервер для обработки ping-запросов от клиентов.
Отвечает PONG с вероятностью 90%, отправляет keepalive каждые 5 секунд.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Set
import argparse

# Настройка логирования для сервера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Server')


class TCPServer:
    def __init__(self, host: str = '127.0.0.1', port: int = 8888,
                 log_file: str = 'logs/server.log'):
        """
        Инициализация TCP сервера.

        Args:
            host: Хост для прослушивания
            port: Порт для прослушивания
            log_file: Путь к файлу лога
        """
        self.host = host
        self.port = port
        self.log_file = log_file
        self.response_counter = 0  # Сквозная нумерация ответов
        self.clients: Dict[asyncio.StreamWriter, int] = {}  # writer -> client_id
        self.client_counter = 0  # Счётчик для ID клиентов

    def _get_next_client_id(self) -> int:
        """Получить следующий ID для клиента."""
        self.client_counter += 1
        return self.client_counter

    def _get_next_response_id(self) -> int:
        """Получить следующий ID для ответа."""
        self.response_counter += 1
        return self.response_counter - 1  # Начинаем с 0

    def _format_time(self) -> str:
        """Форматирование времени для логов (ЧЧ:ММ:СС.ССС)."""
        now = datetime.now()
        return now.strftime('%H:%M:%S.') + f"{now.microsecond // 1000:03d}"

    def _format_date(self) -> str:
        """Форматирование даты для логов (ГГГГ-ММ-ДД)."""
        return datetime.now().strftime('%Y-%m-%d')

    async def _write_log(self, request_time: str, request_msg: str,
                         response_time: str = None, response_msg: str = None):
        """
        Запись строки в лог-файл сервера.

        Формат: дата;время_получения;запрос;время_отправки;ответ
        """
        date_str = self._format_date()

        if response_time is None:  # Проигнорировано
            log_line = f"{date_str};{request_time};{request_msg};(проигнорировано);(проигнорировано)"
        else:
            log_line = f"{date_str};{request_time};{request_msg};{response_time};{response_msg}"

        # Асинхронная запись в файл
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
        logger.debug(f"Лог записан: {log_line}")

    async def handle_client(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter):
        """
        Обработка подключения клиента.

        Args:
            reader: StreamReader для чтения данных
            writer: StreamWriter для отправки данных
        """
        # Получаем информацию о клиенте
        peername = writer.get_extra_info('peername')
        client_id = self._get_next_client_id()
        self.clients[writer] = client_id

        logger.info(f"Подключился клиент #{client_id} с адреса {peername}")

        try:
            while True:
                # Читаем данные от клиента
                try:
                    data = await reader.readuntil(b'\n')
                except asyncio.IncompleteReadError:
                    logger.info(f"Клиент #{client_id} отключился")
                    break

                # Декодируем сообщение
                message = data.decode('ascii').strip()
                request_time = self._format_time()

                logger.debug(f"Получено от клиента #{client_id}: {message}")

                # Проверяем, игнорировать ли запрос (10% вероятность)
                if random.random() < 0.1:
                    logger.info(f"Запрос от клиента #{client_id} проигнорирован: {message}")
                    await self._write_log(request_time, message)
                    continue

                # Извлекаем номер запроса из сообщения
                try:
                    # Формат: [номер] PING
                    request_num = int(message[1:].split(']')[0])
                except (ValueError, IndexError):
                    logger.warning(f"Неверный формат сообщения от клиента #{client_id}: {message}")
                    continue

                # Ждём случайное время (100-1000 мс)
                delay = random.randint(100, 1000) / 1000.0
                await asyncio.sleep(delay)

                # Формируем и отправляем ответ
                response_id = self._get_next_response_id()
                response_msg = f"[{response_id}/{request_num}] PONG ({client_id})"
                response_time = self._format_time()

                writer.write((response_msg + '\n').encode('ascii'))
                await writer.drain()

                logger.debug(f"Отправлено клиенту #{client_id}: {response_msg}")

                # Логируем запрос и ответ
                await self._write_log(request_time, message, response_time, response_msg)

        except ConnectionError as e:
            logger.warning(f"Ошибка соединения с клиентом #{client_id}: {e}")
        finally:
            # Очистка при отключении клиента
            del self.clients[writer]
            writer.close()
            await writer.wait_closed()
            logger.info(f"Клиент #{client_id} отключён")

    async def keepalive_task(self):
        """
        Задача для отправки keepalive сообщений всем подключенным клиентам каждые 5 секунд.
        """
        while True:
            await asyncio.sleep(5)

            if not self.clients:
                continue

            response_id = self._get_next_response_id()
            keepalive_msg = f"[{response_id}] keepalive"

            logger.info(f"Отправка keepalive #{response_id} всем клиентам")

            # Отправляем всем подключенным клиентам
            disconnected = []
            for writer, client_id in self.clients.items():
                try:
                    writer.write((keepalive_msg + '\n').encode('ascii'))
                    await writer.drain()
                    logger.debug(f"Keepalive отправлен клиенту #{client_id}")
                except ConnectionError:
                    logger.warning(f"Не удалось отправить keepalive клиенту #{client_id}")
                    disconnected.append(writer)

            # Удаляем отключённых клиентов
            for writer in disconnected:
                del self.clients[writer]

    async def run(self, timeout: int = 300):
        """
        Запуск сервера.

        Args:
            timeout: Время работы сервера в секундах (по умолчанию 5 минут)
        """
        logger.info(f"Запуск сервера на {self.host}:{self.port}")
        logger.info(f"Логи будут сохраняться в {self.log_file}")

        # Создаём директорию для логов, если её нет
        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # Очищаем лог-файл при запуске
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('')

        # Запускаем сервер
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        async with server:
            # Запускаем задачу keepalive в фоне
            keepalive = asyncio.create_task(self.keepalive_task())

            # Запускаем сервер с таймаутом
            logger.info(f"Сервер запущен. Остановка через {timeout} секунд...")
            await asyncio.sleep(timeout)

            # Останавливаем задачи
            keepalive.cancel()
            logger.info("Сервер остановлен")


def main():
    """Точка входа для сервера."""
    parser = argparse.ArgumentParser(description='TCP PING-PONG сервер')
    parser.add_argument('--host', default='127.0.0.1', help='Хост для прослушивания')
    parser.add_argument('--port', type=int, default=8888, help='Порт для прослушивания')
    parser.add_argument('--log', default='logs/server.log', help='Файл для логов')
    parser.add_argument('--timeout', type=int, default=300, help='Время работы в секундах')
    parser.add_argument('--debug', action='store_true', help='Включить отладку')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    server = TCPServer(args.host, args.port, args.log)

    try:
        asyncio.run(server.run(args.timeout))
    except KeyboardInterrupt:
        logger.info("Сервер остановлен по запросу пользователя")


if __name__ == '__main__':
    main()