# TCP PING-PONG Сервер и Клиенты

Асинхронный TCP сервер с двумя клиентами, реализующий протокол ping-pong
с логированием.


## Требования

- Python 3.10+

## Структура проекта 

```
tcp_ping_pong/
├── server.py           # Серверная часть
├── client.py          # Клиентская часть  
├── launcher.py        # Лаунчер для запуска всех процессов
├── requirements.txt   # Зависимости
└── logs/              # Директория для логов
```


## Установка и запуск

### 1. Клонирование и настройка

```bash
# Клонируйте репозиторий
git clone https://github.com/AndrewSkow24/tcp_ping_pong
cd tcp_ping_pong

# Убедитесь, что используете Python 3.10+
python --version

# Создайте виртуальное окружение (опционально)
python -m venv venv
source venv/bin/activate
# На Windows: venv\Scripts\activate
```

### Рекомендуемый способ запуска (через лаунчер)
```bash
# Запуск на 30 секунд (для тестирования)
python launcher.py --timeout 30

# Запуск на 5 минут с 2 клиентами
python launcher.py --timeout 300 --clients 2

# Запуск с отладочным выводом
python launcher.py --timeout 60 --debug
```



