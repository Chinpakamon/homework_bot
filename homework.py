import http
import os
import logging
import time
from logging.handlers import RotatingFileHandler
from json.decoder import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в чат Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено в чат Telegram.')
    except TelegramError as error:
        logging.error(f'Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к ENDPOINT сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != http.HTTPStatus.OK:
            raise ConnectionError(
                "API возвращает код, отличный от 200")
        return response.json()
    except requests.exceptions.HTTPError as error_http:
        logger.error(f'Http Error: {error_http}')
    except requests.exceptions.ConnectionError as error_connect:
        logger.error(f'Ошибка подключения: {error_connect}')
    except requests.exceptions.RequestException as error_request:
        logger.error(f'Ошибка запроса: {error_request}')
    except JSONDecodeError as error_json:
        logger.error(f'API возвращает код, отличный от 200. '
                     f'Ошибка - {error_json}')


def check_response(response):
    """Проверяет ответ API."""
    if type(response) is not dict:
        raise TypeError('API не соответствует ожиданиям')
    if 'homeworks' not in response:
        raise KeyError(
            'В ответе API отсутствует ключ homeworks')
    if not response.get('homeworks'):
        raise IndexError(
            'Список домашних работ не содержит элементов')
    return response.get('homeworks')[0]


def parse_status(homework):
    """Извлекает статус работы."""
    if 'homework_name' not in homework:
        raise KeyError('Неизвестное имя домашней работы')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise KeyError(f'Ключа {homework_status} нет в словаре')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность пременных окружения."""
    tokens = (
        TELEGRAM_CHAT_ID,
        TELEGRAM_TOKEN,
        PRACTICUM_TOKEN,
    )
    tokens_env = []
    for i in tokens:
        if i is None:
            tokens_env.append(i)
    return len(tokens_env) == 0


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Отсутствуют переменные окружения.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 2678400
    while True:
        try:
            response = get_api_answer(current_timestamp)
            home_work_1 = check_response(response)['status']
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)
        else:
            response = get_api_answer(current_timestamp)
            home_work_2 = check_response(response)['status']
            if home_work_1 != home_work_2:
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)
            else:
                message = 'Статус работы не изменился'
                logger.debug(message)


if __name__ == '__main__':
    main()
