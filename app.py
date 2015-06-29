import sys
import logging

from flask import Flask
from flask import request

from bot import TelegramBot

app = Flask(__name__)
app.config.from_envvar("CONFIG_FILE")

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

if app.config.get('LOG_FILE', None):
    handler = logging.FileHandler(app.config['LOG_FILE'])
else:
    handler = logging.StreamHandler(stream=sys.stdout)

handler.setFormatter(formatter)
logger.addHandler(handler)
app.logger.addHandler(handler)

bot = TelegramBot(app.config['TOKEN'])

logger.propagate = False

@app.route("/test")
def index():
    return "it's working, it's workiiiiing"

@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    bot.process_update(update)
    return 'ok'

if __name__ == '__main__':
    me = bot.me()
    logger.info("Bot named %(first_name)s/%(username)s" % me['result'])

    if not app.config['DEBUG']:
        bot.register_webhook(app.config['URL'])

    app.run(host="0.0.0.0")
