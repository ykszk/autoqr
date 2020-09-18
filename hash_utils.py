import hashlib
import base64

default_salt = '2020/08/19 12:00'  # DO NOT CHANGE


def hash_id(pid, salt=None):
    if salt is None:
        salt = default_salt
    h = hashlib.md5((salt + pid + salt).encode())
    return base64.b64encode(h.digest()).decode().rstrip('=').replace('/', '-')


def get_default_salt():
    return default_salt


def set_default_salt(salt):
    global default_salt
    default_salt = salt
