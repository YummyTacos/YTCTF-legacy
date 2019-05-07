# YTCTF Platform
# Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from flask import g, Blueprint
from flask_restful import Resource

import api

bp = Blueprint('internal_api', __name__)


def wrap_api(f):
    try:
        g.api_user = g.user
        r = f()
    finally:
        del g.api_user
    return r


class Tasks(Resource):
    @staticmethod
    def get():
        return wrap_api(api.Tasks.get)


class Scoreboard(Resource):
    @staticmethod
    def get():
        return wrap_api(api.Scoreboard.get)
