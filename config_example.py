# YTCTF Platform
# Copyright © 2018 Evgeniy Filimonov <evgfilim1@gmail.com>
# See full NOTICE at http://github.com/YummyTacos/YTCTF

from pathlib import Path

CSRF_ENABLED = True
SECRET_KEY = 'SomethingRandom\xff\xaa\xbb\xcc\xdd\xee\x00'

cwd = Path(__file__).resolve().parent / 'data'
if not cwd.exists():
    cwd.mkdir(mode=0o755, parents=True)

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(cwd / 'app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

ADMIN_DATA = dict(username='admin', email='admin@example.com', is_confirmed=False,
                  is_admin=True, first_name='Admin')
SITE_ADMIN_PASSWORD = 'admin'
FLAG_REGEXP = r'^(test|yt)ctf[a-zA-Z0-9_]+$'
