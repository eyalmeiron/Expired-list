from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import colorama
import http
import re
import logging
import os
import json
import copy
import time


app = Flask(__name__)
items_db = []


@app.route('/item', methods=['POST'])
def add_item():

    response = validate_arguments(['name', 'expired_date'])
    if response is not None:
        log('POST /item')
        return response

    request_args = request.json or request.form
    name = request_args['name']
    expired_date = request_args['expired_date']
    count = int(request_args.get('count', 1))

    try:
        datetime.strptime(expired_date, '%d.%m.%y')
    except Exception:
        return create_error('expired_date is not valid', http.HTTPStatus.BAD_REQUEST, expired_date=expired_date)

    log('POST /item', name=name, expired_date=expired_date, count=count)

    for _ in range(count):
        items_db.append([name, expired_date])

    sort_and_save_items_list()

    return jsonify(list(set(map(lambda item: item[0], items_db))))


@app.route('/items', methods=['GET'])
def get_all_items():
    log('GET /items')
    return jsonify(items_db)


@app.route('/item', methods=['PUT'])
def edit_item():
    response = validate_arguments(['old_name', 'old_expired_date', 'new_name', 'new_expired_date'])
    if response is not None:
        log('PUT /item')
        return response

    request_args = request.json or request.form
    old_name = request_args['old_name']
    new_name = request_args['new_name']
    old_expired_date = request_args['old_expired_date']
    new_expired_date = request_args['new_expired_date']

    try:
        datetime.strptime(new_expired_date, '%d.%m.%y')
    except Exception:
        return create_error('new_expired_date is not valid',
                            http.HTTPStatus.BAD_REQUEST,
                            new_expired_date=new_expired_date)

    if [old_name, old_expired_date] not in items_db:
        return create_error('item not found', 404, old_name=old_name, old_expired_date=old_expired_date)

    log('PUT /item',
        old_name=old_name,
        old_expired_date=old_expired_date,
        new_name=new_name,
        new_expired_date=new_expired_date)

    items_db.remove([old_name, old_expired_date])
    items_db.append([new_name, new_expired_date])
    sort_and_save_items_list()

    return jsonify()


@app.route('/item', methods=['DELETE'])
def delete_item():
    response = validate_arguments(['name', 'expired_date'])
    if response is not None:
        log('DELETE /item')
        return response

    request_args = request.json or request.form
    name = str(request_args['name'])
    expired_date = request_args['expired_date']
    log('DELETE /item', name=name, expired_date=expired_date)

    if [name, expired_date] not in items_db:
        return create_error('item not found', 404, name=name, expired_date=expired_date)

    items_db.remove([name, expired_date])

    sort_and_save_items_list()

    return jsonify(items_db)


@app.route('/names', methods=['GET'])
def get_names():
    log('GET /names')
    return jsonify(list(set(map(lambda item: item[0], items_db))))


@app.route('/expired_items', methods=['GET'])
def get_expired_items():
    log('GET /expired_items')

    expired_items = copy.deepcopy(items_db)
    for (name, expired_date) in items_db:
        if not datetime.strptime(expired_date, '%d.%m.%y') - datetime.now() < timedelta(days=7):
            expired_items.remove([name, expired_date])

    return jsonify(expired_items)


def log(msg, color='blue', error=False, ip=True, **kargs):
    if error:
        msg = 'Error: {0}'.format(msg)
        color = 'red'

    timestamp = colorize(str(datetime.now()))
    msg = colorize(msg, color)

    if ip:
        ip = ' ({0})'.format(request.remote_addr)
    else:
        ip = ''

    if kargs:
        args = '[{0}]'.format(
            ' | '.join(['{0}={1}'.format(colorize(k), colorize(v)) for k, v in kargs.items()]))
    else:
        args = ''

    print('{timestamp}{ip}: {msg:<35} {args}'.format(
        timestamp=timestamp,
        ip=ip,
        msg=msg,
        args=args,
    ))


def colorize(text, color='blue'):
    color = getattr(colorama.Fore, color.upper())
    reset_color = colorama.Fore.RESET
    return u'{0}{1}{2}'.format(color, text, reset_color)


def validate_arguments(args=None):
    if args is None:
        args = []

    # check if the necessary arguments provided
    if len(args) > 0:
        request_args = request.json or request.form
        if request_args is None:
            return create_error('missing \'{0}\' argument{1}'.format('\' and \''.join(args),
                                                                     's' if len(args) > 1 else ''),
                                status=http.HTTPStatus.BAD_REQUEST)
        for arg in args:
            if arg not in request_args:
                return create_error('The request missing \'{0}\' argument'.format(arg),
                                    status=http.HTTPStatus.BAD_REQUEST)

    return None


def create_error(msg, status=http.HTTPStatus.SERVICE_UNAVAILABLE, print_log=True, **kargs):
    if print_log:
        log(msg, error=True, **kargs)
    resp = jsonify({'error': msg})
    resp.status_code = status
    return resp


def load_word_list():

    global items_db
    if not os.path.exists('db.txt'):
        return

    items_list_file = open('db.txt', 'r', encoding='utf-8')
    items_db = json.loads(items_list_file.read())

    items_list_file.close()


def sort_and_save_items_list():
    global items_db
    items_db = sorted(items_db, key=lambda item: (datetime.strptime((item[1]), '%d.%m.%y'), item[0]))

    items_list_file = open('db.txt', 'w', encoding='utf-8')
    items_list_file.write(json.dumps(items_db))
    items_list_file.close()


if __name__ == "__main__":

    # disable Flask warning logs
    tornado_logger = logging.getLogger('werkzeug')
    tornado_logger.disabled = True

    # load word list from file
    load_word_list()

    app.run(host='0.0.0.0')
