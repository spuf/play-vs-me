import datetime
import time
import os
import random
import cgi

import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from bot import bot_move

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import channel

from django.utils import simplejson

# models

class Game(db.Model):
    id = db.StringProperty(required=True)
    userT = db.StringProperty(required=True)
    userF = db.StringProperty()
    move = db.BooleanProperty(default=False)
    board = db.StringProperty()
    chat = db.StringProperty(default='')
    request = db.StringProperty()

    create_time = db.DateTimeProperty(auto_now_add=True)
    update_time = db.DateTimeProperty(auto_now=True)

# helpers

board_size = 20;
templates_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'templates'))

def render(name, values = {}):
    path = os.path.join(templates_path, name + '.htm')
    return template.render(path, values)

def generate_id():
    token = long(str(random.randint(10, 99)) + str(long(time.time() * 100)))
    abc = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    base = len(abc)
    short = ''

    while token > 0:
        short += abc[token % base]
        token /= base

    return short

def send_game(game, winner, last):
    game_state = {
        'board': game.board,
        'move': game.move if game.userF else None,
        'last': last,
        'actions': count_actions(game.board),
        'winner': winner,
        'request': game.request
    }
    message = simplejson.dumps(game_state)
    if game.userT != 'bot':
        channel.send_message(game.userT + game.id, message)
    if game.userF:
        channel.send_message(game.userF + game.id, message)

def get_symbol(board, row, col):
    if 0 <= row < board_size and 0 <= col < board_size:
        return board[row * board_size + col]
    else:
        return ' '

def check_win(board, rule=5):
    for row in range(board_size):
        for col in range(board_size):
            if get_symbol(board, row, col) != ' ':
                # horizontal
                if col <= board_size - rule:
                    winning = 1
                    while get_symbol(board, row, col) == get_symbol(board, row, col + winning):
                        winning += 1
                    if winning >= rule:
                        return {'row': row, 'col': col, 'count': winning, 'dx': 1, 'dy': 0}
                # vertical
                if row <= board_size - rule:
                    # |
                    winning = 1
                    while get_symbol(board, row, col) == get_symbol(board, row + winning, col):
                        winning += 1
                    if winning >= rule:
                        return {'row': row, 'col': col, 'count': winning, 'dx': 0, 'dy': 1}
                    # /
                    if col >= rule - 1:
                        winning = 1
                        while get_symbol(board, row, col) == get_symbol(board, row + winning, col - winning):
                            winning += 1
                        if winning >= rule:
                            return {'row': row, 'col': col, 'count': winning, 'dx': -1, 'dy': 1}
                    # \
                    if col <= board_size - rule:
                        winning = 1
                        while get_symbol(board, row, col) == get_symbol(board, row + winning, col + winning):
                            winning += 1
                        if winning >= rule:
                            return {'row': row, 'col': col, 'count': winning, 'dx': 1, 'dy': 1}
    return None

def create_game(ip, chat='', bot=False):
    id = generate_id()
    board = ' ' * (board_size ** 2)
    if bot:
        game = Game(id=id, userT='bot', userF=ip, board=board, chat=chat)
    else:
        game = Game(id=id, userT=ip, board=board, chat=chat)
    game.put()
    return game

def count_actions(board):
    k = 0
    for i in range(len(board)):
        if board[i] == 'x' or board[i] == 'o':
            k += 1
    return k

def get_delta(update_time):
    s = str(datetime.datetime.now() - update_time)
    return s[:s.find('.')]

# controllers

class MainPage(webapp.RequestHandler):
    def get(self):
        leavers = db.Query(Game).filter('update_time <', datetime.datetime.now() - datetime.timedelta(days=7)).fetch(1000)
        for game in leavers:
            game.delete()

        values = {
            'games': db.Query(Game).count(1000),
            'timeout': 'week',
            'debug': str(memcache.get('latest')),
            'message': ''
        }
        if self.request.get('wrongkey'):
            values['message'] = 'You was redirect here, cuz game with that key was not found!'

        self.response.out.write(render('index', values))

    def post(self):
        enemy = self.request.get('enemy')
        if self.request.get('create') and enemy:
            ip = self.request.remote_addr
            if enemy == 'bot':
                game = create_game(ip, 'o: I&#39;m gonna win you, human!\\n', True)
            else:
                game = create_game(ip)
            self.redirect('/game/' + game.id)
        else:
            self.redirect('/?wrongrequest=true')

class GamePage(webapp.RequestHandler):
    def get(self, id):
        ip = self.request.remote_addr
        game = db.Query(Game).filter('id =', id).get()
        if game is None:
            self.redirect('/?wrongkey=true')
            return
        else:
            if not game.userF and ip != game.userT:
                game.userF = ip
                game.put()

        token = channel.create_channel(ip + id) if ip == game.userT or ip == game.userF else 'null'
        values = {
            'id': id,
            'token': token,
            'me': 'true' if ip == game.userT else 'false',
            'move': 'null' if game.userT != 'bot' else str(game.move).lower(),
            'board': game.board,
            'actions': count_actions(game.board),
            'chat': game.chat
        }
        self.response.out.write(render('game', values))

class ChatPage(webapp.RequestHandler):
    def post(self):
        game = db.Query(Game).filter('id =', self.request.get('id')).get()
        ip = self.request.remote_addr

        if game and ip:
            text = cgi.escape(self.request.get('message').strip(), True).replace('\\', '\\\\').replace('\'', '&#39;')
            if text and len(text) <= 40:
                if ip == game.userT or ip == game.userF:
                    who = 'o' if ip == game.userT else 'x'
                    text = who + ': ' + text + '\\n'
                    while len(game.chat) + len(text) > 400:
                        game.chat = game.chat[game.chat.find('\\n') + 2:].strip('\\')
                    game.chat += text
                    game.put()
                    message = '{"chat": "' + game.chat + '"}'
                    if game.userT != 'bot':
                        channel.send_message(game.userT + game.id, message)
                    if game.userF:
                        channel.send_message(game.userF + game.id, message)

class SystemPage(webapp.RequestHandler):
    def post(self):
        game = db.Query(Game).filter('id =', self.request.get('id')).get()
        ip = self.request.remote_addr

        if game and ip:
            winner = check_win(game.board)
            status = self.request.get('status')
            
            if self.request.get('opened'):
                send_game(game, winner, None)
                
            elif self.request.get('request') and winner:
                if not game.request:
                    new_game = create_game(ip, game.chat + '<hr />', (game.userT == 'bot'))
                    game.request = new_game.id
                    game.put()
                message = '{"request": "' + game.request + '"}'
                if game.userT != 'bot':
                    channel.send_message(game.userT + game.id, message)
                if game.userF:
                    channel.send_message(game.userF + game.id, message)
            
            elif status in ['ok', 'afk', 'off']:
                message = '{"status": "' + status + '"}'
                if game.userT == 'bot':
                    channel.send_message(game.userF + game.id, message)
                else:
                    if game.userF:
                        if ip == game.userT:
                            channel.send_message(game.userF + game.id, message)
                        if ip == game.userF:
                            channel.send_message(game.userT + game.id, message)


class MovePage(webapp.RequestHandler):
    def post(self):
        game = db.Query(Game).filter('id =', self.request.get('id')).get()
        ip = self.request.remote_addr

        if game and ip:
            pos = self.request.get_range('to', 0, board_size ** 2 - 1, -1);
            if pos > -1:
                if game.board[pos] == ' ':
                    if game.userT == 'bot':
                        if game.move == False and ip == game.userF:
                            board = game.board[:pos] + 'x' + game.board[pos + 1:]
                            game.move = True
                            game.board = board
                            winner = check_win(game.board)
                            game.put()
                            send_game(game, winner, pos)
                            if winner is None:
                                bot = bot_move(game.board)
                                pos = bot['move']
                                text = bot['chat']
                                if len(text) > 0:
                                    text = 'o: ' + text + '\\n'
                                    while len(game.chat) + len(text) > 400:
                                        game.chat = game.chat[game.chat.find('\\n') + 2:].strip('\\')
                                    game.chat += text
                                    message = '{"chat": "' + game.chat + '"}'
                                    channel.send_message(game.userF + game.id, message)

                                board = game.board[:pos] + 'o' + game.board[pos + 1:]
                                game.move = False
                                game.board = board
                                game.put()

                                winner = check_win(game.board)
                                send_game(game, winner, pos)
                    else:
                        if (game.move == True and ip == game.userT) or (game.move == False and ip == game.userF):
                            board = game.board[:pos]
                            board += 'o' if game.move else 'x'
                            board += game.board[pos + 1:]
                            game.board = board
                            game.move = not game.move
                            game.put()
                            winner = check_win(game.board)
                            send_game(game, winner, pos)

# url mapping

application = webapp.WSGIApplication([
        ('/', MainPage),
        ('/system', SystemPage),
        ('/move', MovePage),
        ('/chat', ChatPage),
        ('/game/(.*)', GamePage)
    ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()