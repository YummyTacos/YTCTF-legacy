# YTCTF Platform
# Copyright © 2018 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from os import remove
from pathlib import Path
from secrets import choice
from string import ascii_letters, digits

from flask import Blueprint, flash, redirect, url_for, request, render_template, \
    current_app as app
from werkzeug.utils import secure_filename

from forms import TaskForm
from models import User, db, FlagSubmit, Task, TasksSolved, TaskFiles
from utils import admin_required, Event

bp = Blueprint('admin', __name__)


@bp.route('/reset_password/<int:user_id>')
@admin_required
def reset_password(user_id):
    u = User.query.get(user_id)
    if u is None:
        flash(f'Нет пользователя с id={user_id}', 'danger')
        return redirect(url_for('main'))
    new_passwd = ''.join([choice(ascii_letters + digits) for _ in range(12)])
    u.set_password(new_passwd)
    db.session.commit()
    flash(f'Пароль сброшен! Новый пароль: {new_passwd}', 'success')
    return redirect(url_for('user', user_id=user_id))


@bp.route('/recalc')
@admin_required
def recalculate():
    for t in FlagSubmit.query.all():
        if Task.query.get(t.task_id) is None:
            db.session.delete(t)
    for t in TasksSolved.query.all():
        if Task.query.get(t.task_id) is None:
            db.session.delete(t)
    for u in User.query.all():
        u.points = 0
        for t in TasksSolved.query.filter_by(user_id=u.id):
            task_ = Task.query.get(t.task_id)
            if u.is_admin or u in task_.authors:
                db.session.delete(t)
                continue
            if not task_.is_hidden:
                u.points += task_.points
    for t in Task.query.filter(Task.is_hidden.isnot(True)).all():
        for u in t.authors:
            u.points += t.points
    db.session.commit()
    flash('Баллы пересчитаны', 'success')
    return redirect(url_for('scoreboard'))


@bp.route('/task/add', methods=['GET', 'POST'])
@admin_required
def add_task():
    form = TaskForm()
    form.author.choices = [(u.id, u.username) for u in User.query.all()]
    if form.validate_on_submit():
        t = Task(
            task=form.name.data,
            description=form.description.data.replace('\r\n', '\n'),
            category=form.category.data,
            points=form.points.data,
            link=form.link.data or None,
            flag=form.flag.data,
            is_hidden=form.is_hidden.data,
            hint=form.hint.data or None
        )
        for user_id in form.author.data:
            author = User.query.get(user_id)
            t.authors.append(author)
            author.points += t.points
        db.session.add(t)
        db.session.commit()
        for file in request.files.getlist('files'):
            filename = secure_filename(file.filename)
            base_dir = (Path(app.static_folder) / f'files/tasks/{t.id}').resolve()
            base_dir.mkdir(parents=True, exist_ok=True)
            file.save(str(base_dir / filename))
            db_file = TaskFiles(file=filename)
            db.session.add(db_file)
            t.files.append(db_file)
        db.session.add(Event.NEW_TASK.trigger(task_id=t.id))
        db.session.commit()
        flash('Таск добавлен!', 'success')
        return redirect(url_for('task', task_id=t.id))
    return render_template('admin_task.html', form=form, new=True)


@bp.route('/task/<int:task_id>/modify', methods=['GET', 'POST'])
@admin_required
def modify_task(task_id):
    form = TaskForm()
    task_ = Task.query.get(task_id)
    if task_ is None:
        flash(f'Нет таска с id={task_id}', 'danger')
        return redirect(url_for('main'))
    form.author.choices = [(u.id, u.username) for u in User.query.all()]
    if form.validate_on_submit():
        for u in task_.solved:
            u.points -= (task_.points - form.points.data)
        for u in task_.authors:
            u.points -= (task_.points - form.points.data)
        task_.task = form.name.data
        task_.description = form.description.data.replace('\r\n', '\n')
        task_.category = form.category.data
        task_.points = form.points.data
        task_.link = form.link.data or None
        task_.authors = [User.query.get(user_id) for user_id in form.author.data]
        task_.flag = form.flag.data
        task_.is_hidden = form.is_hidden.data
        task_.hint = form.hint.data
        for file in request.files.getlist('files'):
            filename = secure_filename(file.filename)
            base_dir = (Path(app.static_folder) / f'files/tasks/{task_.id}').resolve()
            base_dir.mkdir(parents=True, exist_ok=True)
            file.save(str(base_dir / filename))
            db_file = TaskFiles(file=filename)
            db.session.add(db_file)
            task_.files.append(db_file)
        db.session.commit()
        flash('Таск изменён!', 'success')
        return redirect(url_for('task', task_id=task_id))
    form.name.data = task_.task
    form.description.data = task_.description or ''
    form.category.data = task_.category
    form.points.data = task_.points
    form.link.data = task_.link or ''
    form.author.data = [user.id for user in task_.authors]
    form.flag.data = task_.flag
    form.is_hidden.data = task_.is_hidden
    form.hint.data = task_.hint
    return render_template('admin_task.html', form=form, task=task_, new=False)


@bp.route('/task/<int:task_id>/delete')
@admin_required
def delete_task(task_id):
    task_ = Task.query.get(task_id)
    if task_ is None:
        flash(f'Нет таска с id={task_id}', 'danger')
        return redirect(url_for('main'))
    for u in task_.solved:
        u.points -= task_.points
    db.session.delete(task_)
    db.session.commit()
    flash('Таск удалён', 'success')
    return redirect(url_for('main'))


@bp.route('/delete_file/<int:file_id>')
@admin_required
def delete_file(file_id):
    file = TaskFiles.query.get(file_id)
    if file is None:
        flash(f'Нет файла с id={file_id}')
        return redirect(url_for('main'))
    t_id = file.task_id
    remove(Path(f'static/files/tasks/{t_id}/{file.file}').resolve())
    db.session.delete(file)
    db.session.commit()
    flash('Файл удалён', 'success')
    return redirect(url_for('.modify_task', task_id=t_id))


@bp.route('/submits')
@admin_required
def submits():
    submits_ = [
        {'task': Task.query.get(x.task_id),
         'submit': x,
         'correct': Task.query.get(x.task_id).flag == x.flag,
         'user': User.query.get(x.user_id)}

        for x in FlagSubmit.query.all()
    ]
    return render_template('flagsubmit.html', submits=submits_)
