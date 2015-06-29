import re
from decorator import decorator

def split(text, splits=0):
    return re.split('\s|\xa0', text, splits)

class ValidationException(Exception):
    pass

@decorator
def reply(f, *args, **kwargs):
    """ if a command needs to show the message as a reply """
    r = f(*args, **kwargs)

    if r:
        if isinstance(r, dict):
            r['needs_reply'] = True
        elif isinstance(r, basestring):
            r = dict(answer=r, needs_reply=True)

    return r

@decorator
def preview(f, *args, **kwargs):
    """ if a command needs to show an url with a preview """
    r = f(*args, **kwargs)

    if r:
        if isinstance(r, dict):
            r['needs_preview'] = True
        elif isinstance(r, basestring):
            r = dict(answer=r, needs_preview=True)

    return r

class Command(object):

    # can be a single slash command or a 
    # list of commands
    SLASH_COMMAND = None

    # defines if the command needs a reply or not
    REPLY_NEEDED = False

    # if the command supplies this, we will parse the text using this
    # regex and try to validate the command using it
    REGEX = None

    def __init__(self, bot, redis):
        self._bot = bot
        self._redis = redis

        if isinstance(self.SLASH_COMMAND, basestring):
            self.SLASH_COMMAND = [self.SLASH_COMMAND]

        if self.SLASH_COMMAND:
            self._commands = dict([(c.split(' ')[0].replace("/", ""), c) for c in self.SLASH_COMMAND])
            command_re = r'^\/(%s)\s?(.*)?$' % '|'.join("\\b%s\\b" % c.replace('/', '') for c in self._commands.keys())
            self._slash_re = re.compile(command_re, re.I)
            self._slash_args_re = re.compile(r'\[(\w+)\]')

    def __validate_slash_command(self, text, message):

        result = self._slash_re.findall(text)

        if not result:
            return False

        try:
            command, args = result[0]
            command = command.lower()
            args = args.split()
        except ValueError:
            command, result[0][0].lower()
            args = None

        try:
            full_command = self._commands[command]
            command_args = self._slash_args_re.findall(full_command)

            if command_args and len(command_args) != len(args):
                    raise ValidationException("Wrong number of arguments %s" % full_command)

            message['args'] = dict(zip(command_args, args))
        except (KeyError, IndexError):
            return False

        message['command'] = command.lower()

        return True

    def __validate_regex(self, text, message):
        result = self.REGEX.findall(text)

        if not result:
            return False

        message['result'] = result[0]
        return True

    def can_respond(self, text, message):
        if self.REGEX:
            return self.__validate_regex(text, message)

        if self.SLASH_COMMAND:
            return self.__validate_slash_command(text, message)

        return False

    def __send_message(self, command_response, message):
        if isinstance(command_response, basestring):
            command_response = dict(answer=command_response)

        if not isinstance(command_response, dict):
            raise ValueError("Command response must be a dict")

        if 'answer' not in command_response:
            raise ValueError("Command response must have an answer")

        answer = command_response['answer']
        needs_reply = command_response.get('needs_reply', False)
        needs_preview = command_response.get('needs_preview', False)

        reply_id = message.get('message_id', None) if needs_reply else None
        
        self._bot.send_message(message['chat']['id'], answer, reply_id, needs_preview)

    def process(self, bot, message):
        try:
            text = message['text'].encode("utf-8").decode("utf-8")
            text = text.replace(u'\xa0', ' ')
            message['text'] = text
        except KeyError:
            message['text'] = ''

        try:
            if self.can_respond(text, message):
                response = self.respond(text, message)
                self.__send_message(response, message)
        except ValidationException, e:
            self.__send_message(dict(answer=e.message), message)

class Ping(Command):
    """ Simple ping command to make sure the bot itself works """

    SLASH_COMMAND = '/ping'

    def respond(self, text, message):
        return 'pong'

class Help(Command):
    """ LOLHELP """
    SLASH_COMMAND = '/help'

    @reply
    def respond(self, text, message):
        return 'Deus ajuda quem cedo madruga'

COMMANDS = [Ping, Help]
