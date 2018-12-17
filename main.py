# YTCTF Platform
# Copyright © 2018 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from datetime import datetime

from flask import session, g, render_template, redirect, url_for, flash, request, abort
from flask_restful import Api
from werkzeug.exceptions import HTTPException

import api
from app import app
from admin import bp as admin_bp
from forms import LoginForm, RegisterForm, FlagForm, ChangePasswordForm, UserDataForm
from models import User, Task, db, TasksSolved, FlagSubmit, TaskAuthors
from utils import find_user, login_required, admin_required, get_ending, Event, save_exception

_api = Api(api.bp)

# noinspection PyTypeChecker
_api.add_resource(api.Auth, '/auth')
# noinspection PyTypeChecker
_api.add_resource(api.Task, '/task')
# noinspection PyTypeChecker
_api.add_resource(api.Tasks, '/tasks')
# noinspection PyTypeChecker
_api.add_resource(api.User, '/user')
# noinspection PyTypeChecker
_api.add_resource(api.Scoreboard, '/scoreboard')
# noinspection PyTypeChecker
_api.add_resource(api.Updates, '/events')


@app.before_request
def before_request():
    if request.args.get('t') is not None:
        return abort(418)
    g.get_ending = get_ending
    user_id = session.get('user_id', None)
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)


@app.errorhandler(418)
def teapot(exc):
    return render_template('teapot.html'), 418


@app.errorhandler(Exception)
def broken(exc):
    if app.debug:
        raise exc
    h = save_exception(exc)
    err_code, err_name, err_desc = 500, 'Internal Server Error', ''
    if isinstance(exc, HTTPException):
        err_code, err_name, err_desc = exc.code, exc.name, exc.description
    return render_template('broken.html', exc=h, code=err_code, name=err_name,
                           desc=err_desc), err_code


@app.route('/', methods=['GET', 'POST'])
def main():
    if g.user is None:
        form = LoginForm()
        if form.validate_on_submit():
            session['user_id'] = find_user(form.login.data).id
            return redirect(request.args.get('next') or url_for('main'))
        flash('Для доступа к платформе необходимо войти', 'warning')
        return render_template('login.html', form=form)
    # next_ = request.args.get('next')
    # if next_:
    #     return redirect(next_)
    return render_template('checker.html', tasks=Task.query.all())


@app.route('/logout')
def logout():
    if g.user is not None:
        session.pop('user_id')
    return redirect(url_for('main'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user is not None:
        flash('Ты уже вошёл в аккаунт', 'warning')
        return redirect(url_for('main'))
    form = RegisterForm()
    if form.validate_on_submit():
        u = User(username=form.login.data, email=form.email.data, first_name=form.first_name.data,
                 last_name=form.last_name.data or None, group=form.group.data or None)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        flash('Ты успешно зарегистрировался!')
        return redirect(url_for('main', username=form.login.data))
    return render_template('login.html', form=form)


@app.route('/change_password/<int:user_id>', methods=['GET', 'POST'])
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password(user_id=None):
    if user_id is None:
        u = g.user
    elif g.user.is_admin:
        u = User.query.get(user_id)
        if u is None:
            flash(f'Нет пользователя с id={user_id}', 'danger')
            return redirect(url_for('main'))
    else:
        flash('Нет доступа!', 'danger')
        return redirect(url_for('main'))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        u.set_password(form.new_password.data)
        db.session.commit()
        flash('Пароль изменён успешно!', 'success')
        return redirect(url_for('main'))
    return render_template('chpasswd.html', form=form, username=u.username)


@app.route('/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id=None):
    u = User.query.get(user_id)
    if u is None:
        flash(f'Нет пользователя с id={user_id}', 'danger')
        return redirect(url_for('main'))
    TasksSolved.query.filter(TasksSolved.user_id == user_id).delete()
    TaskAuthors.query.filter(TaskAuthors.user_id == user_id).update({
        TaskAuthors.user_id: 1
    })
    FlagSubmit.query.filter(FlagSubmit.user_id == user_id).delete()
    db.session.delete(u)
    db.session.commit()
    flash('Пользователь удалён', 'success')
    return redirect(url_for('main'))


@app.route('/scoreboard')
def scoreboard():
    return render_template('scoreboard.html')


@app.route('/<int:task_id>', methods=['GET', 'POST'])
@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task(task_id):
    task_ = Task.query.get(task_id)
    if not task_:
        flash(f'Нет таска под номером {task_id}', 'danger')
        return redirect(url_for('main'))
    form = FlagForm(task_.flag)
    if form.is_submitted():
        s = FlagSubmit(
            task_id=task_id,
            user_id=g.user.id,
            time=datetime.utcnow(),
            flag=form.flag.data
        )
        db.session.add(s)
        db.session.commit()
        if form.flag.data != task_.flag:
            e = Event.TASK_FAILED.trigger(flag_submit_id=s.id)
        else:
            e = Event.TASK_SOLVED.trigger(flag_submit_id=s.id)
        db.session.add(e)
        db.session.commit()
    if form.validate_on_submit():
        if not g.user.is_admin and g.user not in task_.solved and g.user not in task_.authors:
            if not task_.is_hidden:
                g.user.points += task_.points
            else:
                flash('Баллы за этот таск не были начислены, т.к. он скрыт.', 'warning')
            if len(task_.solved) == 0:
                # `s` is initialized if the form is submitted, but `validate_on_submit`
                #  return False if the form was not submitted, so `s` is always initialized.
                # noinspection PyUnboundLocalVariable
                db.session.add(Event.FIRST_BLOOD.trigger(flag_submit_id=s.id))
            task_.solved.append(g.user)
            db.session.commit()
        # Redirecting to the same endpoint to prevent 'resend data?' question from browser
        return redirect(url_for('task', task_id=task_id))
    if task_.is_hidden:
        flash('Этот таск скрыт. Возможно, тебе не стоит его решать.', 'danger')
    return render_template('task.html', task=task_, form=form)


@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
def user(user_id):
    u = User.query.get(user_id)
    form = UserDataForm()
    if u is None:
        flash(f'Нет пользователя с id={user_id}', 'danger')
        return redirect(url_for('main'))
    solved_tasks = [
        Task.query.get(t.task_id) for t in TasksSolved.query.filter(
            TasksSolved.user_id == user_id
        ).all()
    ]
    task_author = [
        Task.query.get(t.task_id) for t in TaskAuthors.query.filter(
            TaskAuthors.user_id == user_id
        ).all()
    ]
    first_blood = []
    for t in solved_tasks:
        ts = TasksSolved.query.filter(TasksSolved.task_id == t.id).first()
        if ts.user_id == user_id:
            first_blood.append(t.id)
    if (g.user is not None and (g.user.id == user_id or g.user.is_admin)) and \
            form.validate_on_submit():
        u.first_name = form.first_name.data
        u.last_name = form.last_name.data
        u.group = form.group.data
        u.username = form.login.data
        u.email = form.email.data
        db.session.commit()
        flash('Информация изменена', 'success')
    return render_template('user.html', user=u, form=form, solved=solved_tasks, first=first_blood,
                           author=task_author)


@app.route('/auth')
@login_required
def auth():
    return render_template('api_auth.html', token=api.ser.dumps({'user_id': g.user.id}))


app.register_blueprint(api.bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/admin')

if __name__ == '__main__':
    app.run()
