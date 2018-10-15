from flask import Flask, request
from dbot import Bot, reply_markup as repl
import sqlite3
import random
import datetime
from collections import Counter

import time
from pprint import pprint

app = Flask(__name__)

b = Bot('659041701:AAGap17HlO242G-bZa-anuHLDphiqvvoxiY')

def night_maf(player_id, chat_id, c, choose):
    mafs = c.execute('SELECT a.nickname, a.do, (SELECT b.nickname FROM roles b WHERE b.player_id = a.do AND b.chat_id = ?), a.player_id FROM roles a WHERE a.player_id = ? AND a.chat_id = ? AND a.role = 1',
                (chat_id, player_id, chat_id)).fetchall()
    your = c.execute('SELECT nickname FROM roles WHERE player_id = ? AND chat_id = ?', (choose, chat_id)).fetchone()
    for m in mafs:
        if choose == m[3]:
            return 'Ты шо дурной'
        elif m[1] != choose:
            c.execute('UPDATE roles SET do = ? WHERE player_id = ? AND chat_id = ?', (choose, player_id, chat_id))
            if len(mafs) > 1:
                return 'Согласуйте выбор!\nВаш:\n{}\nДругие:\n{}'.format(your[0], '\n'.join(['{} > {}'.format(v[0], v[1] if v[1] else 'не выбрал') for v in mafs if v[3] != player_id]))
            else:
                return 'Выбор согласован'

def maf(chat_id, c):
    ch = c.execute('SELECT a.do, (SELECT b.nickname FROM roles b WHERE b.chat_id = ? AND b.player_id = a.do) FROM roles a WHERE a.chat_id = ? AND a.role = 1 AND a.do > 0', (chat_id, chat_id)).fetchone()
    if ch:
        will_die = ch[0]
        die_nick = ch[1]
    else:
        new = c.execute('SELECT player_id, nickname FROM roles WHERE chat_id = ? AND role != 1 AND alive = 1', (chat_id, )).fetchall()
        he = random.choice(new)
        will_die = he[0]
        die_nick = he[1]
    c.execute('UPDATE roles SET alive = 0 WHERE player_id = ? AND chat_id = ?', (will_die, chat_id))
    return 'Мафия посетила <a href=\"tg://user?id={}\">{}</a>'.format(will_die, die_nick)

def doc(chat_id, c):
    heal = c.execute('SELECT a.do, (SELECT b.nickname FROM roles b WHERE b.chat_id = ? AND b.player_id = a.do) FROM roles a WHERE a.chat_id = ? AND a.role = 2 AND a.do > 0', (chat_id, chat_id)).fetchone()
    if heal:
        c.execute('UPDATE roles SET alive = 1 WHERE player_id = ? AND chat_id = ?', (heal[0], chat_id))
        return 'Доктор лечил <a href=\"tg://user?id={}\">{}</a>'.format(heal[0], heal[1])

def night_doc(player_id, chat_id, c, choose):
    heal = c.execute('SELECT a.do, (SELECT b.nickname FROM roles b WHERE b.player_id = a.do AND b.chat_id = ?) FROM roles a WHERE a.player_id = ? AND a.chat_id = ?',
                (chat_id, player_id, chat_id)).fetchone()
    if heal[0]:
        return 'Ты уже пошел лечить ' + heal[1]
    elif heal[0] == choose:
        return 'Ты его только что лечил'
    else:
        c.execute('UPDATE roles SET do = ? WHERE player_id = ? AND chat_id = ?', (choose, player_id, chat_id))
        your = c.execute('SELECT nickname FROM roles WHERE player_id = ? AND chat_id = ?', (choose, chat_id)).fetchone()
        return 'Ты лечишь ' + your[0]

def put(chat_id, c):
    pit = c.execute('SELECT a.do, (SELECT b.nickname FROM roles b WHERE b.chat_id = ? AND b.player_id = a.do) FROM roles a WHERE a.chat_id = ? AND a.role = 3 AND a.do > 0', (chat_id, chat_id)).fetchone()
    if pit:
        c.execute('UPDATE roles SET mute = 1 WHERE player_id = ? AND chat_id = ?', (pit[0], chat_id))
        return 'Путана была у <a href=\"tg://user?id={}\">{}</a>'.format(pit[0], pit[1])

def night_put(player_id, chat_id, c, choose):
    put = c.execute('SELECT a.do, (SELECT b.nickname FROM roles b WHERE b.player_id = a.do AND b.chat_id = ?) FROM roles a WHERE a.player_id = ? AND a.chat_id = ?',
                (chat_id, player_id, chat_id)).fetchone()
    if put[0]:
        return 'Ты уже сходила к ' + put[1]
    elif player_id == choose:
        text = 'Мда...'
    else:
        your = c.execute('SELECT nickname FROM roles WHERE player_id = ? AND chat_id = ?', (choose, chat_id)).fetchone()
        text = 'Твой выбор пал на ' + your[0]
    c.execute('UPDATE roles SET do = ? WHERE player_id = ? AND chat_id = ?', (choose, player_id, chat_id))
    return text

def night_ser(player_id, chat_id, c, choose):
    if chat_id == choose:
        return 'Ты шо дурной'
    aff = c.execute('SELECT a.do, (SELECT b.nickname FROM roles b WHERE b.player_id = a.do AND b.chat_id = ?), (SELECT b.role FROM roles b WHERE b.player_id = a.do AND b.chat_id = ?) FROM roles a WHERE a.player_id = ? AND a.chat_id = ?',
                (chat_id, chat_id, player_id, chat_id)).fetchone()
    if aff[0]:
        return '{} был посещен тобой... И оказалось что он - {}'.format(aff[1], 'мафия' if aff[2] == 1 else 'не мафия')
    else:
        c.execute('UPDATE roles SET do = ? WHERE player_id = ? AND chat_id = ?', (choose, player_id, chat_id))
        your = c.execute('SELECT nickname, role FROM roles WHERE player_id = ? AND chat_id = ?', (choose, chat_id)).fetchone()
        return 'Ты посетил {} и обнаружил что он - {}'.format(your[0], 'мафия' if your[1] == 1 else 'не мафия')

ROLES = {
    1: {'name': 'мафия', 'nact': night_maf, 'act': maf},
    2: {'name': 'доктор', 'nact': night_doc, 'act': doc},
    3: {'name': 'путана', 'nact': night_put, 'act': put},
    4: {'name': 'шериф', 'nact': night_ser},
    0: {'name': 'мирный'},
}

LOBBY_INACTIVITY = {'minutes': -3} #{'seconds': -10}
DAY_INACTIVITY = {'minutes': -1} #{'seconds': -10}
NIGHT_INACTIVITY = {'minutes': -1} #{'seconds': -10}

def get_cursor():
    return sqlite3.connect('maf.bd', isolation_level=None).cursor()

def get_time(**kwargs):
    time_now = datetime.datetime.now()
    if len(kwargs) > 0:
        time_now += datetime.timedelta(**kwargs)
    return time_now

def maf_calc(count, mods=[]):
    if count < 3:
        return None
    elif count <= 5:
        active = [1, 2, 3]
    elif count >= 6 and count <= 8:
        active = [1, 1, 2, 3, 4]
    elif count >= 9 and count <= 10:
        active = [1, 1, 1, 2, 3, 4]
    elif count >= 11 and count <= 14:
        active = [1, 1, 1, 1, 2, 3, 4]
    else:
        active = [1 for i in range(count // 3)]
        active.extend([2, 3, 4])
    if not len(active) + len(mods) > count:
        active.extend(mods)
    active.extend([0 for i in range(count - len(active))])
    random.shuffle(active)
    return active
        
def render_prepare(chat_id):
    text = 'Собираем людей\n'
    c = get_cursor()
    people_notf = c.execute('SELECT nickname, player_id, (SELECT last_vote > ?) is_active FROM roles WHERE chat_id = ?',
            (get_time(**LOBBY_INACTIVITY), chat_id)).fetchall()
    people = '\n'.join(['{} <a href=\"tg://user?id={}\">{}</a>'.format('👤' if one[2] else '💤', one[1], one[0]) for one in people_notf])
    reply_markup = repl.inlinekeyboardmarkup([
        [repl.inlinekeyboardbutton('Присоединится', callback_data='connect'), repl.inlinekeyboardbutton('Отсоединится', callback_data='disconnect')],
        [repl.inlinekeyboardbutton('Начать', callback_data='start')]
        ])
    return text + people, reply_markup

def get_alives(chat_id, c, com):
    alives = []; button_alives = []; ai = 1
    for one in c.execute('SELECT nickname, player_id FROM roles WHERE chat_id = ? AND alive = 1', (chat_id, )).fetchall():
        alives.append('{}. <a href=\"tg://user?id={}\">{}</a>'.format(ai, one[1], one[0]))
        button_alives.append([repl.inlinekeyboardbutton('{}. {}'.format(ai, one[0]), callback_data='{} {}'.format(com, one[1]))])
        ai += 1
    return alives, button_alives

def render_day(chat_id):
    text = 'Ну что ж... Кто же мафия ♠️ ?'
    c = get_cursor()
    alives, button_alives = get_alives(chat_id, c, 'vote')
    text += '\n\nЖивые:\n' + '\n'.join(alives) if alives else ''
    votes = c.execute('SELECT (SELECT s.nickname FROM roles s WHERE chat_id = ? AND alive = 1 AND s.player_id = f.vote), f.vote, f.nickname, f.player_id FROM roles f WHERE chat_id = ? AND alive = 1',
            (chat_id, chat_id))
    vote = {}
    for v in votes:
        if not v[1]:
            pass
        elif v[1] in vote:
            vote[v[1]]['list'].append('🤔 <a href=\"tg://user?id={}\">{}</a>'.format(v[3], v[2]))
        else:
            vote[v[1]] = {'name': v[0], 'list': ['🤔 <a href=\"tg://user?id={}\">{}</a>'.format(v[3], v[2])]}
    text += '\n\n👉 Голосование'
    for v in vote:
        text += '\nЗа 😨 <a href=\"tg://user?id={}\">{}</a>:\n{}'.format(v, vote[v]['name'], '\n'.join(vote[v]['list']))
    control = [[repl.inlinekeyboardbutton('🔄', callback_data='reload'), repl.inlinekeyboardbutton('ℹ️', callback_data='info')]]
    button_alives.extend(control)
    return text, repl.inlinekeyboardmarkup(button_alives)

def render_night(chat_id):
    text = 'Наступила ночь\nАктивные игроки творят свое дело...\n'
    c = get_cursor()
    alives, button_alives = get_alives(chat_id, c, 'do')
    text += '\n'.join(alives)
    control = [[repl.inlinekeyboardbutton('🔄', callback_data='reload'), repl.inlinekeyboardbutton('ℹ️', callback_data='info')]]
    button_alives.extend(control)
    return text, repl.inlinekeyboardmarkup(button_alives)

def set_last_and_return(chat_id, mess_id):
    c = get_cursor()
    last = c.execute('SELECT last FROM games WHERE chat_id = ?', (chat_id, )).fetchone()
    c.execute('UPDATE games SET last = ? WHERE chat_id = ?', (mess_id, chat_id))
    return last[0] if last else None

def send_or_del(chat_id, render, reply_markup, edit_mess=None, delete=True):
    if not edit_mess:
        result = b.msg(render, chat_id=chat_id, reply_markup=reply_markup, parse_mode='HTML').send()
        if result['ok']:
            prev_mess_id = set_last_and_return(chat_id, result['result']['message_id'])
            if prev_mess_id and delete: 
                b.delete(prev_mess_id, chat_id).send()
    else:
        b.editmessagetext(render, chat_id=chat_id, message_id=edit_mess, reply_markup=reply_markup, parse_mode='HTML').send()

def send_prepare(chat_id, edit_mess=None):
    render, reply_markup = render_prepare(chat_id)
    send_or_del(chat_id, render, reply_markup, edit_mess)

def send_day(chat_id, edit_mess=None, delete=True):
    render, reply_markup = render_day(chat_id)
    send_or_del(chat_id, render, reply_markup, edit_mess, delete)
    
def send_night(chat_id, edit_mess=None, delete=True):
    render, reply_markup = render_night(chat_id)
    send_or_del(chat_id, render, reply_markup, edit_mess, delete)

def win(chat_id, c):
    pl = c.execute('SELECT player_id, nickname, role FROM roles WHERE chat_id = ?', (chat_id, )).fetchall()
    c.execute('UPDATE games SET playing = 0 WHERE chat_id = ?', (chat_id, ))
    c.execute('DELETE FROM roles WHERE chat_id = ?', (chat_id, ))
    pls = ['<a href=\"tg://user?id={}\">{}</a> - {}'.format(i[0], i[1], ROLES[i[2]]['name']) for i in pl]
    last = c.execute('SELECT last FROM games WHERE chat_id = ?', (chat_id, )).fetchone()
    if last:
        b.delete(last[0], chat_id).send()
    b.msg('Роли играли...\n' + '\n'.join(pls), chat_id=chat_id).send()
    c.execute('DELETE FROM games WHERE chat_id = ?', (chat_id, ))
    
    

def control(chat_id, c, edit_mess):
    day = c.execute('SELECT day, last_activity FROM games WHERE chat_id = ?', (chat_id, )).fetchone()
    if day[0] % 2:
        send_day(chat_id, edit_mess)
        cc = c.execute('SELECT (SELECT count(1) FROM roles WHERE chat_id = ? AND alive = 1) = (SELECT count(1) FROM roles WHERE chat_id = ? AND alive = 1 AND vote > 0)', (chat_id, chat_id)).fetchone()
        if cc[0] or day[1] < str(get_time(**DAY_INACTIVITY)):
            apl = [i[0] for i in c.execute('SELECT vote FROM roles WHERE chat_id = ?', (chat_id, )).fetchall() if i[0]]
            if len(apl) < 2:
                win(chat_id, c)
                return
            cou = Counter(apl).most_common()
            if len(cou) >= 2 and cou[0][1] == cou[1][1]:
                text = 'Никого не вешаем\n'
            else:
                c.execute('UPDATE roles SET alive = 0 WHERE chat_id = ? AND player_id = ?', (chat_id, cou[0][0]))
                pl = c.execute('SELECT nickname FROM roles WHERE chat_id = ? AND player_id = ?', (chat_id, cou[0][0])).fetchone()
                text = 'Вешаем <a href=\"tg://user?id={}\">{}</a>'.format(
                    cou[0][0], c.execute('SELECT nickname FROM roles WHERE chat_id = ? AND player_id = ?', (chat_id, cou[0][0])).fetchone()[0])
            c.execute('UPDATE roles SET vote = 0, mute = 0 WHERE chat_id = ?', (chat_id, ))
            c.execute('UPDATE games SET day = ?, last_activity = ? WHERE chat_id = ?', (day[0] + 1, get_time(), chat_id))
            b.msg(text, chat_id=chat_id, parse_mode='HTML').send()
            send_night(chat_id, edit_mess=None)
    else:
        cc = c.execute('SELECT (SELECT count(1) FROM roles WHERE chat_id = ? AND role = 1 AND alive = 1 GROUP BY do) = (SELECT count(1) FROM roles WHERE chat_id = ? AND role = 1 AND alive = 1) AND (SELECT count(1) FROM roles WHERE chat_id = ? AND do > 0 AND alive = 1 AND role > 0) = (SELECT count(1) FROM roles WHERE chat_id = ? AND alive = 1 AND role > 0)',
                (chat_id, chat_id, chat_id, chat_id)).fetchone()
        if cc[0] or day[1] < str(get_time(**NIGHT_INACTIVITY)):
            alerts = []
            for r in ROLES:
                if 'act' in ROLES[r]:
                    answer = ROLES[r]['act'](chat_id, c)
                    if answer:
                        alerts.append(b.msg(answer, chat_id=chat_id, parse_mode='HTML'))
            b.more(alerts)
            c.execute('UPDATE roles SET do = 0 WHERE chat_id = ?', (chat_id, ))
            c.execute('UPDATE games SET day = ?, last_activity = ? WHERE chat_id = ?', (day[0] + 1, get_time(), chat_id))
            send_day(chat_id, edit_mess=None)

@b.message('/day')
def test(a):
    text, buttons = render_day(a.data['chat']['id'])
    print(a.msg(text, reply_markup=buttons, parse_mode='HTML').send())
    
@b.message('/night')
def test1(a):
    text, buttons = render_night(a.data['chat']['id'])
    print(a.msg(text, reply_markup=buttons, parse_mode='HTML').send())

@b.message('/game')
def start(a):
    if a.data['chat']['type'] == 'private':
        a.msg('Используй бота в группе').send()
    else:
        chat_id = a.data['chat']['id']
        c = get_cursor()
        result = c.execute('SELECT playing FROM games WHERE chat_id = ?', (chat_id, )).fetchone()    #0-нет игры/собираются
        print(result)
        if not result:                                                                               #1-играют
            c.execute('INSERT INTO games (chat_id, playing) VALUES (?, 0)', (chat_id, ))
        if not (result and result[0]):
            send_prepare(chat_id)

def callback_start(old):
    def reg(a):
        c = get_cursor()
        is_start = c.execute('SELECT playing FROM games WHERE chat_id = ?', (a.data['message']['chat']['id'], )).fetchone()
        if is_start:
            if is_start[0]:
                text = 'Игра начата... Подожди конец' #Когда пользователь клацнул в левом окне во время игры
                b.delete(a.data['message']['message_id'], chat_id=a.data['message']['chat']['id']).send()
            else:
                text = old(a, c)
        else:
            text = 'Создай игру'  #Когда игра не создана
        a.answer(text=text).send()
        #return old
    return reg

@b.callback_query('connect')
@callback_start
def connect(a, c):
    chat_id = a.data['message']['chat']['id']
    if c.execute('SELECT 1 FROM roles WHERE chat_id = ? AND player_id = ?',
            (chat_id, a.data['from']['id'])).fetchone():
        c.execute('UPDATE roles SET last_vote = ? WHERE chat_id = ? AND player_id = ?', 
            (get_time(), chat_id, a.data['from']['id']))
        send_prepare(chat_id, edit_mess=a.data['message']['message_id'])
        return 'Счетчик обновлен'    #Когда уже в игре
    else:
        nickname = a.data['from']['first_name'] + ' ' + a.data['from']['last_name'] if 'last_name' in a.data['from'] else a.data['from']['first_name']
        c.execute('INSERT INTO roles (chat_id, nickname, player_id, last_vote, alive) VALUES (?, ?, ?, ?, 1)', 
            (chat_id, nickname, a.data['from']['id'], get_time()))
        send_prepare(chat_id, edit_mess=a.data['message']['message_id'])
        return nickname + ' в игре' #Только зашел в игру

@b.callback_query('disconnect')
@callback_start
def disconnect(a, c):
    c.execute('DELETE FROM roles WHERE chat_id = ? AND player_id = ?', (a.data['message']['chat']['id'], a.data['from']['id']))
    pprint(a.data)
    send_prepare(a.data['message']['chat']['id'], edit_mess=a.data['message']['message_id'])
    return 'Вы не в игре'
    
@b.callback_query('start')
@callback_start
def start_game(a, c):
    chat_id = a.data['message']['chat']['id']
    player_id = a.data['from']['id']
    if c.execute('SELECT 1 FROM roles WHERE chat_id = ? AND player_id = ?', (chat_id,  player_id)).fetchone():
        c.execute('UPDATE roles SET last_vote = ? WHERE chat_id = ? AND player_id = ?', (get_time(), chat_id,  player_id))
        comp = c.execute('SELECT (SELECT count(1) FROM roles WHERE chat_id = ?) all_players, (SELECT count(1) FROM roles WHERE chat_id = ? AND last_vote > ?) active_players', 
                (chat_id, chat_id, get_time(**LOBBY_INACTIVITY))).fetchone()
        if comp[0] < 3:
            return 'Мало людей...'
        elif comp[0] == comp[1]:
            last_activity = get_time()
            c.execute('UPDATE games SET playing = 1, day = 0, last_activity = ? WHERE chat_id = ?', (last_activity, chat_id))
            players = c.execute('SELECT player_id, nickname FROM roles WHERE chat_id = ?', (chat_id, )).fetchall()
            roles = maf_calc(len(players))
            ai = 0
            lols = []
            for player in players:
                c.execute('UPDATE roles SET role = ?, last_vote = ? WHERE player_id = ? AND chat_id = ?', (roles[ai], last_activity, player[0], chat_id))
                ai += 1
                lols.append('{}. <a href=\"tg://user?id={}\">{}</a>'.format(ai, player[0], player[1]))
            count_roles = ['{} x {}'.format(ROLES[r]['name'], roles.count(r)) for r in ROLES if roles.count(int(r))]
            b.msg('Роли распределены\nИграют:\n{}\nРоли: {}'.format(
                '\n'.join(lols), ', '.join(count_roles)), chat_id=chat_id, parse_mode='HTML').send()
            send_night(chat_id)
            return 'Начинаем'
        else:
            send_prepare(chat_id, edit_mess=a.data['message']['message_id'])
            return 'Сейчас активно {}% игроков'.format(comp[1]*100 // comp[0])
    else:
        return 'Присоединись сначала'

def callback_game(old):
    def reg(a):
        c = get_cursor()
        is_start = c.execute('SELECT (SELECT playing FROM games WHERE chat_id = ?) AND (SELECT 1 FROM roles WHERE chat_id = ? AND player_id = ? AND alive = 1)',
                (a.data['message']['chat']['id'], a.data['message']['chat']['id'], a.data['from']['id'])).fetchone()
        if is_start[0]:
            text = old(a, c)
        else:
            text = 'Ты не играешь' #Когда пользователь клацнул в левом окне во время игры
        a.answer(text=text).send()
        #return old
    return reg

@b.callback_query('vote ([0-9]+)')
@callback_game
def vote(a, c):
    if c.execute('SELECT 1 FROM roles WHERE player_id = ? AND chat_id = ? AND mute = 1', (a.data['from']['id'], a.data['message']['chat']['id'])).fetchone():
        return 'Ты не можешь за него голосовать'
    c.execute('UPDATE roles SET vote = ? WHERE chat_id = ? AND player_id = ?', 
            (a.args[1], a.data['message']['chat']['id'], a.data['from']['id']))
    control(a.data['message']['chat']['id'], c, a.data['message']['message_id'])
    return 'Голос засчитан'

@b.callback_query('do ([0-9]+)')
@callback_game
def do(a, c):
    role = c.execute('SELECT role FROM roles WHERE player_id = ? AND chat_id = ? AND alive = 1', (a.data['from']['id'], a.data['message']['chat']['id'])).fetchone()
    if role:
        r = ROLES[role[0]]
        if 'nact' in r:
            result = r['nact'](a.data['from']['id'], a.data['message']['chat']['id'], c, a.args[1])
            control(a.data['message']['chat']['id'], c, a.data['message']['message_id'])
            return result
        else:
            return 'Отдыхай'
    else:
        return 'Ты не активный'

@b.callback_query('info')
@callback_game
def info(a, c):
    role = c.execute('SELECT role FROM roles WHERE player_id = ? AND chat_id = ? AND alive = 1', (a.data['from']['id'], a.data['message']['chat']['id'])).fetchone()
    print(c.execute('SELECT role, do FROM roles WHERE chat_id = ?', (a.data['message']['chat']['id'], )).fetchall())
    if role:
        return 'Ты {}'.format(ROLES[role[0]]['name'])
    else:
        return 'Ты не активный'

@b.message('/clear')
def clear(a):
    c = get_cursor()
    c.execute('UPDATE games SET playing = 0 WHERE chat_id = ?', (a.data['chat']['id'], ))
    c.execute('DELETE FROM roles WHERE chat_id = ?', (a.data['chat']['id'], ))

@app.route('/maf_hook', methods=['POST']) #Telegram should be connected to this hook
def webhook():
    b.check(request.get_json())
    #pprint(request.get_json())
    return 'ok', 200

def create_db():
    c = get_cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS games
             (chat_id integer NOT NULL PRIMARY KEY,
             playing integer NOT NULL,
             last integer,
             day integer,
             last_activity timestamp)''')
    c.execute('''CREATE TABLE IF NOT EXISTS roles
             (chat_id integer NOT NULL,
             nickname text NOT NULL,
             player_id integer NOT NULL,
             role integer,
             alive integer NOT NULL,
             vote integer,
             do integer,
             prev_do integer,
             mute integer,
             last_vote timestamp NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS players
             (player_id integer NOT NULL PRIMARY KEY,
             winrate integer NOT NULL)''')

#0 - мирный
#1 - мафия
#2 - доктор
#3 - путана
#4 - шериф

if __name__ == '__main__':
    create_db()
    app.run(host='0.0.0.0', port=8080, debug=True)