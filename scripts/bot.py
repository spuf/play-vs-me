import random
import pickle

from google.appengine.api import memcache

board_size = 20

def get_symbol(board, row, col):
    if 0 <= row < board_size and 0 <= col < board_size:
        return board[row * board_size + col]
    else:
        return '*'

def check_row(board, rule, symbol='x'):
    opened = 0
    closed = 0
    for row in range(board_size):
        for col in range(board_size):
            if get_symbol(board, row, col) == symbol:
                # horizontal
                if col <= board_size - rule:
                    winning = 1
                    while get_symbol(board, row, col) == get_symbol(board, row, col + winning) and winning <= rule:
                        winning += 1
                    if winning == rule:
                        if get_symbol(board, row, col + winning) == ' ' and get_symbol(board, row, col - 1) == ' ':
                            opened += 1
                        else:
                            closed += 1
                        #return {'row': row, 'col': col, 'count': winning, 'dx': 1, 'dy': 0}
                # vertical
                if row <= board_size - rule:
                    # |
                    winning = 1
                    while get_symbol(board, row, col) == get_symbol(board, row + winning, col) and winning <= rule:
                        winning += 1
                    if winning == rule:
                        if get_symbol(board, row + winning, col) == ' ' and get_symbol(board, row - 1, col) == ' ':
                            opened += 1
                        else:
                            closed += 1
                        #return {'row': row, 'col': col, 'count': winning, 'dx': 0, 'dy': 1}
                    # /
                    if col >= rule - 1:
                        winning = 1
                        while get_symbol(board, row, col) == get_symbol(board, row + winning, col - winning) and winning <= rule:
                            winning += 1
                        if winning == rule:
                            if get_symbol(board, row + winning, col - winning) == ' ' and get_symbol(board, row - 1, col + 1) == ' ':
                                opened += 1
                            else:
                                closed += 1
                            #return {'row': row, 'col': col, 'count': winning, 'dx': -1, 'dy': 1}
                    # \
                    if col <= board_size - rule:
                        winning = 1
                        while get_symbol(board, row, col) == get_symbol(board, row + winning, col + winning) and winning <= rule:
                            winning += 1
                        if winning == rule:
                            if get_symbol(board, row + winning, col + winning) == ' ' and get_symbol(board, row - 1, col - 1) == ' ':
                                opened += 1
                            else:
                                closed += 1
                            #return {'row': row, 'col': col, 'count': winning, 'dx': 1, 'dy': 1}
    return { 'opened': opened, 'closed': closed }
    #return None

def is_better(x, y):
    if x['5o'] + x['5c'] == y['5o'] + y['5c']:
        if x['4o'] == y['4o']:
            if x['3o'] == y['3o']:
                if x['2o'] == y['2o']:
                    if x['4c'] == y['4c']:
                        if x['3c'] == y['3c']:
                            if x['2c'] == y['2c']:
                                return None
                            else:
                                return (x['2c'] > y['2c'])
                        else:
                            return (x['3c'] > y['3c'])
                    else:
                        return (x['4c'] > y['4c'])
                else:
                    return (x['2o'] > y['2o'])
            else:
                return (x['3o'] > y['3o'])
        else:
            return (x['4o'] > y['4o'])
    else:
        return (x['5o'] + x['5c'] > y['5o'] + y['5c'])

def get_result(temp_board, symbol='x'):
    result = {}
    for rule in range(2, 6):
        count = check_row(temp_board, rule, symbol)
        result[str(rule) + 'o'] = count['opened']
        result[str(rule) + 'c'] = count['closed']
    return result

frases = [
    'You&#39;re fighting like a kitten :3',
    'WTF?',
    'Soooo... What you gonna do?',
    'Ha-ha! Are you scaried?',
    'The Cake is a lie!',
    'There is no way to win :(',
    'Yep. I don&#39;t know many words...',
    'Keep crying, human!',
    'Sh!t bricks!',
    'Bite my shiny metal ass!',
    'I&#39;m in Miami Bitch!'
]

def bot_move(board):
    chat = ''

    objSave = memcache.get(board)

    if objSave is not None:
        obj = pickle.loads(objSave)
        #obj['chat'] = 'Get it from memories...'
    else:
        if board.count('x') == 1:
            move = board.find('x')
            row_x = int(move / board_size)
            col_x = move % board_size
            row = row_x
            col = col_x
            while get_symbol(board, row, col) != ' ':
                row = random.randint(row_x - 1, row_x + 1)
                col = random.randint(col_x - 1, col_x + 1)
            move = board_size * row + col
        else:
            best_pos = board.find(' ')
            best_result = None
            move_result = None

            #defense
            for i in range(board_size ** 2):
                if board[i] == ' ':
                    result = get_result(board[:i] + 'x' + board[i + 1:])

                    if best_result is None:
                        best_pos = i
                        best_result = result
                        move_result = get_result(board[:i] + 'o' + board[i + 1:], 'o')

                    else:
                        better_than = is_better(result, best_result)
                        if better_than is None:
                            #get the best of two
                            result = get_result(board[:i] + 'o' + board[i + 1:], 'o')
                            if is_better(result, move_result):
                                #chat += '\\nARRGHHH! %d better than %d' %(i, best_pos)
                                best_pos = i
                                move_result = result
                        else:
                            if better_than:
                                #chat += '\\nYEP! %d better than %d' %(i, best_pos)
                                best_pos = i
                                best_result = result

            if best_result['5o'] + best_result['5c'] == 0:
                #offense
                count_before = check_row(board, 3, 'o')
                count_before_4 = check_row(board, 4, 'o')
                for i in range(board_size ** 2):
                    if board[i] == ' ':
                        temp_board = board[:i] + 'o' + board[i + 1:]
                        if best_result['4o'] == 0: # + best_result['3o']
                                count = check_row(temp_board, 4, 'o')
                                result = count['closed'] - count_before_4['closed']
                                if result > 0:
                                    best_pos = i
                                    #chat = 'Get on defense!'
                                count = check_row(temp_board, 3, 'o')
                                result = count['opened'] - count_before['opened']
                                if result > 0:
                                    best_pos = i
                                    #chat = 'Easy win :)'
                        count = check_row(temp_board, 4, 'o')
                        result = count['opened']
                        if result > 0:
                            best_pos = i
                            chat = 'Got milk?'
                            break

            #win move
            for i in range(board_size ** 2):
                if board[i] == ' ':
                    temp_board = board[:i] + 'o' + board[i + 1:]
                    count = check_row(temp_board, 5, 'o')
                    result = count['opened'] + count['closed']
                    if result > 0:
                        best_pos = i
                        chat = 'Cool story, bro!'
                        break
            move = best_pos
        #end move chosing

        obj = {'move': move, 'chat': chat}

        memcache.set(board, pickle.dumps(obj))

    if obj['chat'] == '':
        if random.randint(0, 5) == 0:
            obj['chat'] = random.choice(frases)

    return obj