# YTCTF Platform
# Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from bcrypt import gensalt, hashpw, checkpw
from flask_sqlalchemy import SQLAlchemy
from app import app

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    username = db.Column(db.String(), unique=True)
    email = db.Column(db.String(), unique=True)
    password = db.Column(db.String())
    points = db.Column(db.Integer(), default=0)
    first_name = db.Column(db.String(32), nullable=False, server_default='User')
    last_name = db.Column(db.String(32))
    group = db.Column(db.Integer())
    is_confirmed = db.Column(db.Boolean(), default=False)
    is_admin = db.Column(db.Boolean(), default=False)

    def verify_password(self, password):
        if not isinstance(password, bytes):
            password = password.encode('UTF-8')
        if isinstance(self.password, bytes):
            self.password = self.password.decode('UTF-8')
            db.session.commit()
        return checkpw(password, self.password.encode('UTF-8'))

    def set_password(self, password):
        if not isinstance(password, bytes):
            password = password.encode('UTF-8')
        self.password = hashpw(password, gensalt()).decode()
        db.session.commit()


class Task(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    task = db.Column(db.String(), default='Untitled')
    authors = db.relationship('User', secondary='task_authors')
    files = db.relationship('TaskFiles')
    category = db.Column(db.String(), default='misc')
    description = db.Column(db.String(), default='Some strange task')
    link = db.Column(db.String())
    points = db.Column(db.Integer(), default=0)
    flag = db.Column(db.String())
    solved = db.relationship('User', secondary='tasks_solved')
    is_hidden = db.Column(db.Boolean(), default=False)
    hint = db.Column(db.String())  # FIXME: remove
    hints = db.relationship('Hint')


class TasksSolved(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))


class TaskAuthors(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))


class TaskFiles(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id', ondelete='CASCADE'))
    file = db.Column(db.String())


class FlagSubmit(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    flag = db.Column(db.String())
    time = db.Column(db.DateTime())
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id', ondelete='CASCADE'))
    task = db.relationship('Task')
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')


class TaskCategory(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(), nullable=False)
    color = db.Column(db.String())


class Event(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime(), nullable=False)
    type = db.Column(db.Integer(), nullable=False)
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id', ondelete='CASCADE'))
    task = db.relationship('Task')
    flag_submit_id = db.Column(db.Integer(), db.ForeignKey('flag_submit.id', ondelete='CASCADE'))
    flag_submit = db.relationship('FlagSubmit')
    extra = db.Column(db.String())


class Hint(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id', ondelete='CASCADE'))
    task = db.relationship('Task')
    cost = db.Column(db.Integer(), default=0)
    text = db.Column(db.String())

    def is_used_by(self, user):
        return UsedHint.query.filter_by(hint_id=self.id, user_id=user.id).one_or_none() is not None


class UsedHint(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    hint_id = db.Column(db.Integer(), db.ForeignKey('hint.id', ondelete='CASCADE'))
    hint = db.relationship('Hint')
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')


def _init():
    db.create_all()
    if User.query.get(1) is None:
        u = User(id=1, **app.config.get('ADMIN_DATA'))
        u.set_password(app.config.get('SITE_ADMIN_PASSWORD'))
        db.session.add(u)
    db.session.commit()


_init()
