# YTCTF Platform
# Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from datetime import datetime, timedelta
from functools import wraps
from re import match

from flask import url_for, request, g, Blueprint
from flask_restful import Resource, abort
from itsdangerous import URLSafeTimedSerializer, BadSignature

import models
from app import app
from utils import find_user

__SECRETS = (app.config.get('SECRET_KEY'),
             app.config.get('SITE_ADMIN_PASSWORD').encode())

ser = URLSafeTimedSerializer(*__SECRETS)
bp = Blueprint('api', __name__)


@bp.before_request
def before_request():
    g.api_user = None
    if getattr(g, 'user', False) is not False:
        del g.user
    token = request.args.get('token')
    if token is None:
        return
    try:
        t = ser.loads(token, max_age=86400)
    except BadSignature:
        return
    user_id = t.get('user_id')
    if user_id is None:
        return
    g.api_user = user_id and models.User.query.get(user_id)


@bp.route('/')
def docs():
    return abort(404)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.args.get('token')
        if token is None:
            return abort(401, message='Не предоставлен токен')
        if g.api_user is None:
            return abort(401, message='Неверный токен')
        return f(*args, **kwargs)

    return wrapper


def get_post_data():
    return request.json if request.is_json else request.values


class Auth(Resource):
    @staticmethod
    def post():
        data = get_post_data()
        if 'login' not in data or 'password' not in data:
            return abort(400, message='Неверный формат запроса')
        user = find_user(data['login'])
        if user is None:
            return abort(401, message='Неверный логин')
        if not user.verify_password(data['password']):
            return abort(401, message='Неверный пароль')
        return {'token': ser.dumps({'user_id': user.id})}


class Task(Resource):
    @staticmethod
    def get():
        task_id = request.args.get('id', type=int)
        if task_id is None:
            return abort(400, message='Не указан ID таска')
        task = models.Task.query.get(task_id)
        if task is None:
            return abort(404, message='Нет такого таска')
        root = request.url_root.rstrip('/')
        return {
            'task': task.task,
            'category': task.category,
            'points': task.points,
            'authors': [user.username for user in task.authors],
            'description': task.description,
            'link': task.link,
            'hints': [{
                'id': hint.id,
                'cost': hint.cost,
                'text': g.api_user and hint.is_used_by(g.api_user)
            } for hint in task.hints],
            'files': [root + url_for('static', filename=f'files/tasks/{task_id}/{file.file}')
                      for file in task.files],
            'is_hidden': task.is_hidden,
            'solved': g.api_user is not None and (g.api_user in task.solved or g.api_user.is_admin
                                                  or g.api_user in task.authors),
            'solved_by': [{
                'id': user.id,
                'username': user.username
            } for user in task.solved]
        }

    @staticmethod
    @login_required
    def post():
        data = get_post_data()
        if 'id' not in data:
            data['id'] = request.args.get('id')
        if 'flag' not in data or data['id'] is None:
            return abort(400, message='Неверный формат запроса')
        task = models.Task.query.get(int(data.get('id')))
        if task is None:
            return abort(404, message='Таск не найден')
        if g.api_user in task.solved or g.api_user.is_admin or g.api_user in task.authors:
            return abort(403, message='Таск уже сдан!')
        flag = data['flag']
        m = match(app.config.get('FLAG_REGEXP', r'^\w+ctf\w+$'), flag)
        if m is None:
            return abort(400, message='Неверный формат флага.')
        s = models.FlagSubmit(
            task_id=task.id,
            user_id=g.api_user.id,
            time=datetime.utcnow(),
            flag=flag
        )
        models.db.session.add(s)
        if task.flag != flag:
            models.db.session.commit()
            return abort(403, message='Неверный флаг')
        models.db.session.add(models.TasksSolved(task_id=task.id, user_id=g.api_user.id))
        models.db.session.commit()
        return {
            'message': 'Таск сдан',
            'points': task.points if not task.is_hidden else 0
        }


class Hint(Resource):
    @staticmethod
    @login_required
    def get():
        hint_id = request.args.get('id', type=int)
        if hint_id is None:
            return abort(400, message='Не указан ID подсказки')
        hint = models.Hint.query.get(hint_id)
        if hint is None:
            return abort(404, message='Нет такой подсказки')
        if models.UsedHint.query.filter_by(
                hint_id=hint_id, user_id=g.api_user.id
        ).one_or_none() is not None:
            return {'cost': 0, 'text': hint.text}
        models.db.session.add(models.UsedHint(hint_id=hint_id, user_id=g.api_user.id))
        g.api_user.points -= hint.cost
        models.db.session.commit()
        return {'cost': hint.cost, 'text': hint.text}


class Tasks(Resource):
    @staticmethod
    def get():
        as_user = request.args.get('as', type=int)
        user_ = None
        if g.api_user is not None and g.api_user.is_admin and as_user is not None:
            user_ = models.User.query.get(as_user)
        if user_ is None and g.api_user is not None:
            user_ = g.api_user
        if user_ is not None:
            solved_tasks = [
                s.task_id for s in models.TasksSolved.query.filter_by(user_id=user_.id).all()
            ]
            authored_tasks = [
                s.task_id for s in models.TaskAuthors.query.filter_by(user_id=user_.id).all()
            ]
        else:
            solved_tasks, authored_tasks = [], []
        tasks = models.Task.query
        filters = request.args.getlist('type')
        if len(filters) == 1:
            filters = filters[0].split(',')
        if 'hidden' not in filters:
            tasks = tasks.filter(models.Task.is_hidden.isnot(True))
        if 'my' in filters or 'new' in filters:
            if 'new' in filters:
                tasks = tasks.filter(models.Task.id.notin_(solved_tasks + authored_tasks))
            if 'my' in filters:
                tasks = tasks.filter(models.Task.id.in_(authored_tasks))
        tasks = tasks.all()
        return [{
            'id': task.id,
            'task': task.task,
            'category': task.category,
            'points': task.points,
            'hidden': task.is_hidden,
            'authored': user_ is not None and (user_.is_admin or task.id in authored_tasks),
            'solved': task.id in solved_tasks,
            'solved_count': len(task.solved)
        } for task in tasks]


class Scoreboard(Resource):
    @staticmethod
    def get():
        data = []
        query = models.User.query.filter(models.User.is_admin.isnot(True))
        if request.args.get('type', '') != 'all':
            authors = {a.user_id for a in models.TaskAuthors.query.all()}
            query = query.filter(models.User.id.notin_(authors) & (models.User.points != 0))
        for u in query.order_by(models.User.points.desc()).all():
            extra = u.first_name
            if u.last_name:
                extra += f' {u.last_name}'
            if u.group:
                extra += f', {u.group}'
            is_self = g.api_user is not None and g.api_user.id == u.id
            data.append({
                'is_self': is_self,
                'user_id': u.id,
                'username': u.username,
                'extra': extra,
                'points': u.points
            })
        return data


class User(Resource):
    @staticmethod
    def get():
        user_id = request.args.get('id', type=int)
        username = request.args.get('username')
        if (user_id is None and username is None) or \
                (user_id is not None and username is not None):
            return abort(400, message='Неверный формат запроса')
        if user_id is not None:
            user = models.User.query.get(user_id)
        else:  # username is not None
            user = find_user(username)
        if user is None:
            return abort(404, message='Пользователь не найден')
        solved_tasks = [
            t.task_id for t in models.TasksSolved.query.filter(
                models.TasksSolved.user_id == user.id
            ).all()
        ]
        task_author = [
            t.task_id for t in models.TaskAuthors.query.filter(
                models.TaskAuthors.user_id == user.id
            ).all()
        ]
        first_blood = []
        for t in solved_tasks:
            ts = models.TasksSolved.query.filter(models.TasksSolved.task_id == t.id).first()
            if ts.user_id == user.id:
                first_blood.append(t.id)
        data = {
            'id': user.id,
            'username': user.username,
            'points': user.points,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'group': user.group,
            'solved_task_ids': solved_tasks,
            'first_blood_task_ids': first_blood,
            'author_of_task_ids': task_author
        }
        if g.api_user is not None and (g.api_user.id == user.id or g.api_user.is_admin):
            data['email'] = user.email
        return data


class Updates(Resource):
    @staticmethod
    def get():
        offset = request.args.get('offset')
        events = models.Event.query
        if offset is None:
            events = events.filter(models.Event.time >= datetime.utcnow() - timedelta(1))
        else:
            events = events.filter(models.Event.id > offset)
        events = events.all()
        data = [{
            'id': e.id,
            'time': e.time.timestamp(),
            'type': e.type,
            'task_id': e.task_id or (e.flag_submit.task_id if e.flag_submit else None),
            'user_id': e.flag_submit.user_id if e.flag_submit else None,
            'extra': e.extra
        } for e in events]
        return data
