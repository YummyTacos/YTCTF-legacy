# YTCTF Platform
# Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from flask import g
from flask_wtf import FlaskForm
from wtforms import (SubmitField, StringField, PasswordField, ValidationError, TextAreaField,
                     SelectMultipleField, BooleanField, FileField)
from wtforms.fields.html5 import EmailField, URLField, IntegerField
from wtforms.validators import (DataRequired, Email, EqualTo, Regexp, Optional, URL, InputRequired,
                                Length)

from re import compile as re_compile

from app import app
from models import User
from utils import find_user


class SubmitForm(FlaskForm):
    submit = SubmitField()


class UserDataForm(SubmitForm):
    email = EmailField(validators=[DataRequired(), Email()])
    login = StringField(validators=[DataRequired()])
    first_name = StringField(validators=[DataRequired(), Length(max=32,
                                                                message='Слишком длинное имя')])
    last_name = StringField(validators=[Optional(), Length(max=32,
                                                           message='Слишком длинная фамилия')])
    group = IntegerField(validators=[Optional()])

    @staticmethod
    def validate_group(cls, field):
        if field.data is None:
            return
        if not (71 <= field.data <= 76 or 81 <= field.data <= 86):
            raise ValidationError('Неверно введена группа')


class UserForm(SubmitForm):
    login = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])


class LoginForm(UserForm):
    @staticmethod
    def validate_login(cls, field):
        if find_user(field.data) is None:
            raise ValidationError('Неверное имя пользователя')

    def validate_password(self, field):
        user = find_user(self.login.data)
        if user is None:
            return  # Another validator will fail
        if not user.verify_password(field.data):
            raise ValidationError('Неверный пароль')


class RegisterForm(UserForm, UserDataForm):
    password2 = PasswordField(validators=[EqualTo('password')])

    @staticmethod
    def validate_login(cls, field):
        if find_user(field.data) is not None:
            raise ValidationError('Такой пользователь уже зарегистрирован!')

    @staticmethod
    def validate_email(cls, field):
        if User.query.filter(User.email == field.data).one_or_none() is not None:
            raise ValidationError('Такой e-mail уже зарегистрирован!')


class FlagForm(SubmitForm):
    flag = StringField('Флаг', validators=[DataRequired()])

    def __init__(self, flag):
        super().__init__()
        self._flag_re = re_compile(app.config.get('FLAG_REGEXP', r'^\w*ctf.+'))
        self._right_flag = flag

    def validate_flag(self, field):
        field.data = field.data.strip()
        if self._flag_re.fullmatch(field.data) is None:
            raise ValidationError('Неверный формат флага.')
        if field.data != self._right_flag:
            raise ValidationError('Неверный флаг. Учти, что регистр флага имеет значение.')


class ChangePasswordForm(SubmitForm):
    old_password = PasswordField(validators=[DataRequired()])
    new_password = PasswordField(validators=[DataRequired()])
    new_password2 = PasswordField(validators=[DataRequired(), EqualTo('new_password')])

    @staticmethod
    def validate_old_password(cls, field):
        if not g.user.verify_password(field.data):
            raise ValidationError('Неверный пароль')


class TaskForm(SubmitForm):
    name = StringField(validators=[DataRequired()])
    category = StringField(validators=[DataRequired()])
    description = TextAreaField(validators=[DataRequired()])
    link = URLField(validators=[Optional(), URL()])
    files = FileField('Файлы не выбраны', validators=[Optional()])
    hint = TextAreaField(validators=[Optional()])
    points = IntegerField(validators=[InputRequired()])
    flag = StringField(validators=[DataRequired(), Regexp(app.config.get('FLAG_REGEXP'))])
    author = SelectMultipleField(validators=[DataRequired()], coerce=int)
    is_hidden = BooleanField('Скрытый таск')
