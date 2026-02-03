"""
TCP клиент для отправки ping-запросов на сервер.
Отправляет сообщения со случайными интервалами 300-3000 мс.
"""

import asyncio
import logging
import random
import argparse
from datetime import datetime
from typing import Optional

# Настройка логирования для клиента
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Client")


class TCPClient:
    def __init__(
        self,
        client_id: int,
        server_host: str = "127.0.0.1",
        server_port: int = 8888,
        log_file: str = "logs/client.log",
    ):
        """
        Инициализация TCP клиента.

        Args:
            client_id: Уникальный идентификатор клиента
            server_host: Хост сервера
            server_port: Порт сервера
            log_file: Путь к файлу лога
        """
        self.client_id = client_id
        self.server_host = server_host
        self.server_port = server_port
        self.log_file = log_file
        self.request_counter = 0  # Счётчик запросов
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    def _format_time(self) -> str:
        """Форматирование времени для логов (ЧЧ:ММ:СС.ССС)."""
        now = datetime.now()
        return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"

    def _format_date(self) -> str:
        """Форматирование даты для логов (ГГГГ-ММ-ДД)."""
        return datetime.now().strftime("%Y-%m-%d")

    async def _write_log(
        self, send_time: str, request_msg: str, receive_time: str, response_msg: str
    ):
        """
        Запись строки в лог-файл клиента.

        Формат: дата;время_отправки;запрос;время_получения;ответ
        Для keepalive: дата;;;время_получения;keepalive_сообщение
        """
        date_str = self._format_date()

        if not request_msg:  # Keepalive
            log_line = f"{date_str};;;{receive_time};{response_msg}"
        else:
            if response_msg == "(таймаут)":
                log_line = (
                    f"{date_str};{send_time};{request_msg};{receive_time};(таймаут)"
                )
            else:
                log_line = f"{date_str};{send_time};{request_msg};{receive_time};{response_msg}"

        # Асинхронная запись в файл
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
        logger.debug(f"Клиент #{self.client_id}: лог записан")

    async def connect(self):
        """Подключение к серверу."""
        logger.info(
            f"Клиент #{self.client_id}: подключение к {self.server_host}:{self.server_port}"
        )

        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )
            logger.info(f"Клиент #{self.client_id}: успешно подключён")
            return True
        except ConnectionError as e:
            logger.error(f"Клиент #{self.client_id}: ошибка подключения: {e}")
            return False

    async def send_ping(self):
        """Отправка ping-сообщения на сервер."""
        if not self.writer:
            logger.error(f"Клиент #{self.client_id}: нет подключения к серверу")
            return

        # Формируем сообщение
        request_msg = f"[{self.request_counter}] PING"
        send_time = self._format_time()

        # Отправляем сообщение
        try:
            self.writer.write((request_msg + "\n").encode("ascii"))
            await self.writer.drain()
            logger.debug(f"Клиент #{self.client_id}: отправлено {request_msg}")

            # Увеличиваем счётчик для следующего запроса
            current_request_num = self.request_counter
            self.request_counter += 1

            # Ждём ответ с таймаутом 2 секунды
            try:
                data = await asyncio.wait_for(self.reader.readuntil(b"\n"), timeout=2.0)
                response_msg = data.decode("ascii").strip()
                receive_time = self._format_time()

                logger.debug(f"Клиент #{self.client_id}: получено {response_msg}")

                # Проверяем, не является ли это keepalive
                if "keepalive" in response_msg:
                    # Для keepalive не нужно логировать запрос
                    await self._write_log("", "", receive_time, response_msg)
                    # После получения keepalive нужно прочитать следующий ответ
                    # на наш ping (если он будет)
                    try:
                        data = await asyncio.wait_for(
                            self.reader.readuntil(b"\n"), timeout=0.1
                        )
                        response_msg = data.decode("ascii").strip()
                        receive_time = self._format_time()
                        logger.debug(
                            f"Клиент #{self.client_id}: получен ответ после keepalive: {response_msg}"
                        )
                    except (asyncio.TimeoutError, asyncio.IncompleteReadError):
                        # Это нормально, если сервер ещё не ответил на наш ping
                        pass

                # Логируем запрос и ответ
                await self._write_log(
                    send_time, request_msg, receive_time, response_msg
                )

            except asyncio.TimeoutError:
                # Таймаут ожидания ответа
                receive_time = self._format_time()
                logger.warning(
                    f"Клиент #{self.client_id}: таймаут ожидания ответа на {request_msg}"
                )
                await self._write_log(send_time, request_msg, receive_time, "(таймаут)")

        except ConnectionError as e:
            logger.error(f"Клиент #{self.client_id}: ошибка отправки: {e}")
            # Пытаемся переподключиться
            await self.reconnect()

    async def reconnect(self):
        """Переподключение к серверу."""
        logger.info(f"Клиент #{self.client_id}: попытка переподключения...")

        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

        success = False
        retries = 0
        max_retries = 5

        while not success and retries < max_retries:
            try:
                success = await self.connect()
                if not success:
                    await asyncio.sleep(1)  # Ждём перед следующей попыткой
                    retries += 1
            except Exception as e:
                logger.error(f"Клиент #{self.client_id}: ошибка переподключения: {e}")
                retries += 1
                await asyncio.sleep(1)

        return success

    async def message_receiver(self):
        """
        Отдельная задача для приёма сообщений от сервера.
        Нужна для обработки keepalive, которые могут прийти в любой момент.
        """
        while True:
            if not self.reader:
                await asyncio.sleep(0.1)
                continue

            try:
                data = await self.reader.readuntil(b"\n")
                response_msg = data.decode("ascii").strip()
                receive_time = self._format_time()

                logger.debug(
                    f"Клиент #{self.client_id}: получено (в receiver): {response_msg}"
                )

                # Если это keepalive - логируем
                if "keepalive" in response_msg:
                    await self._write_log("", "", receive_time, response_msg)
                # Иначе это ответ на наш ping, который обработается в send_ping

            except (asyncio.IncompleteReadError, ConnectionError):
                # Соединение разорвано
                logger.warning(f"Клиент #{self.client_id}: соединение потеряно")
                await self.reconnect()
            except Exception as e:
                logger.error(f"Клиент #{self.client_id}: ошибка в receiver: {e}")
                await asyncio.sleep(0.1)

    async def run(self, timeout: int = 300):
        """
        Основной цикл работы клиента.

        Args:
            timeout: Время работы клиента в секундах
        """
        logger.info(f"Клиент #{self.client_id}: запуск, работа {timeout} секунд")

        # Создаём директорию для логов, если её нет
        import os

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # Очищаем лог-файл при запуске
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write("")

        # Подключаемся к серверу
        if not await self.connect():
            logger.error(f"Клиент #{self.client_id}: не удалось подключиться к серверу")
            return

        # Запускаем задачу приёма сообщений
        receiver_task = asyncio.create_task(self.message_receiver())

        # Основной цикл отправки сообщений
        start_time = asyncio.get_event_loop().time()

        try:
            while asyncio.get_event_loop().time() - start_time < timeout:
                # Отправляем ping
                await self.send_ping()

                # Ждём случайное время (300-3000 мс)
                delay = random.randint(300, 3000) / 1000.0
                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            logger.info(f"Клиент #{self.client_id}: работа прервана")
        finally:
            # Останавливаем задачи и закрываем соединение
            receiver_task.cancel()
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
            logger.info(f"Клиент #{self.client_id}: остановлен")


def main():
    """Точка входа для клиента."""
    parser = argparse.ArgumentParser(description="TCP PING-PONG клиент")
    parser.add_argument("--id", type=int, required=True, help="ID клиента")
    parser.add_argument("--host", default="127.0.0.1", help="Хост сервера")
    parser.add_argument("--port", type=int, default=8888, help="Порт сервера")
    parser.add_argument(
        "--log", help="Файл для логов (по умолчанию logs/client_<id>.log)"
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Время работы в секундах"
    )
    parser.add_argument("--debug", action="store_true", help="Включить отладку")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Формируем имя файла лога, если не указано
    if not args.log:
        args.log = f"logs/client_{args.id}.log"

    client = TCPClient(args.id, args.host, args.port, args.log)

    try:
        asyncio.run(client.run(args.timeout))
    except KeyboardInterrupt:
        logger.info(f"Клиент #{args.id} остановлен по запросу пользователя")


if __name__ == "__main__":
    main()
