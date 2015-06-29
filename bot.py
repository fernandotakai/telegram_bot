import redis
import requests
import logging
import commands

logger = logging.getLogger()

class TelegramBot(object):

    COMMANDS = commands.COMMANDS

    def __init__(self, token):
        self.__running = True
        self._pool_sleep_time = 5
        self._redis = redis.Redis()
        self._token = token
        self._url = 'https://api.telegram.org/bot%s' % self._token
        
        self._processed_status = set(map(int, self._redis.smembers('bot:updates')))

        self._commands = [cls(self, self._redis) for cls in self.COMMANDS]

    def _send_request(self, method, data=None, is_post=False):
        url = "%s/%s" % (self._url, method)

        logger.info('Sending request to %s using params %s', url, data)

        if is_post:
            response = requests.post(url, data=data)
        else:
            response = requests.get(url, params=data)

        try:
            return response.json()
        except ValueError:
            logger.exception("Could not parse json returned. Response was %s", response.content)
            return None

    def me(self):
        return self._send_request('getMe')

    def process_update(self, update):
        if update['update_id'] in self._processed_status:
            return
        
        self._redis.sadd('bot:updates', update['update_id'])
        self._processed_status.add(update['update_id'])

        if 'message' not in update:
            return

        message = update['message']
        
        for command in self._commands:
            try:
                command.process(self, message)
            except Exception:
                logger.exception('Error processing %s', command)

    def get_updates(self):
        data = dict(offset=max(self._processed_status) + 1) if self._processed_status else None
        return self._send_request('getUpdates', data=data).get('result', [])

    def register_webhook(self, url):
        data = dict(url=url)
        return self._send_request('setWebhook', data=data, is_post=True)

    def send_message(self, chat_id, message, in_reply_to=None, preview=False):
        data = dict(chat_id=chat_id, text=message)

        if in_reply_to:
            data['reply_to_message_id'] = int(in_reply_to)

        data['disable_web_page_preview'] = 'true' if not preview else 'false'

        return self._send_request('sendMessage', data, is_post=True)

    def start_pool(self):
        while self.__running:

            logger.info('Getting updates')
            updates = bot.get_updates()

            for update in updates:
                logger.info("\nProcessing %s\n", update)
                bot.process_update(update)

            logger.info('Waiting %ss', self._pool_sleep_time)
            time.sleep(self._pool_sleep_time)

    def stop(self):
        self.__running = False

if __name__ == '__main__':
    import sys
    import time

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    bot = TelegramBot(sys.argv[1])

    bot.start_pool()
