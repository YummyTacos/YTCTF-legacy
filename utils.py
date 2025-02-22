# YTCTF Platform
# Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from datetime import datetime
from pathlib import Path
from pprint import pprint
from traceback import format_exception
from hashlib import sha1
from re import compile as re_compile

from flask import g, redirect, url_for, request, flash, current_app as app
from functools import wraps
from enum import Enum, unique

from models import User, Event as EventModel


_safe_url_re = re_compile(r'^/[^/].*')


@unique
class Event(Enum):
    NEW_TASK = 1
    TASK_SOLVED = 2
    TASK_FAILED = 3
    FIRST_BLOOD = 4

    def trigger(self, **kwargs):
        return EventModel(time=datetime.utcnow(), type=self.value, **kwargs)


def save_exception(exc):
    fe = format_exception(exc.__class__, exc, exc.__traceback__)
    e = ''.join(fe)
    h = sha1(e.encode()).hexdigest()
    p = (Path(app.static_folder) / 'files/exc/').resolve()
    p.mkdir(parents=True, exist_ok=True)
    with (p / f'e{h}.txt').open('w') as f:
        f.write(f'Last occurred at {datetime.utcnow()} UTC\n\n')
        f.write(e)
        f.write('\nuser.id: {}\n'.format(getattr(g, 'user') and g.user.id))
        f.write(f'\nrequest.user_agent: {request.user_agent.string}\n')
        f.write(f'\nrequest.url: {request.url}\n')
        f.write('\nrequest:\n')
        pprint(get_dir_dict(request, key=lambda x: not x.startswith('__')), stream=f, width=100)
    return h


def find_user(name):
    return User.query.filter_by(username=name).one_or_none()


def safe_next(url, fallback=None):
    if url is not None and _safe_url_re.fullmatch(url) is not None:
        return url
    return fallback or url_for('main')


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.path))
        if not g.user.is_admin:
            flash('Нет доступа!', 'danger')
            return redirect(url_for('main'))
        return f(*args, **kwargs)
    return wrapper


def get_ending(word, n, one, two, five):
    if n % 10 == 1 and n % 100 != 11:
        return word + one
    if 2 <= n % 10 < 5 and n % 100 // 10 != 1:
        return word + two
    return word + five


def get_plural(n, one, two, five):
    return f'{n} {get_ending("", n, one, two, five)}'


def get_dir_dict(obj, *, key=None):
    if key is None:
        key = (lambda x: True)
    d = {}
    for _m in dir(obj):
        if not key(_m):
            continue
        d[_m] = getattr(obj, _m)
    return d
