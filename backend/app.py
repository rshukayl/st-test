import os
import re
import secrets

import psycopg
import redis
from flask import Flask, jsonify, request

app = Flask(__name__)
cache = redis.Redis(
    host=os.environ['REDIS_HOST'],
    password=os.environ['REDIS_PASSWORD'],
    socket_connect_timeout=2,
    socket_timeout=2,
    decode_responses=True,
)
SESSION_TTL = int(os.environ['SESSION_TTL'])


def database():
    return psycopg.connect(
        host=os.environ['POSTGRES_HOST'],
        port=os.environ['POSTGRES_PORT'],
        dbname=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD'],
        connect_timeout=2,
        options='-c statement_timeout=2000',
    )


@app.get('/healthz')
def health():
    try:
        with database() as conn:
            conn.execute('SELECT 1').fetchone()
        if not cache.ping():
            raise RuntimeError('Redis unavailable')
    except Exception:
        app.logger.exception('Dependency health check failed')
        return jsonify(status='unhealthy'), 503
    return jsonify(status='ok', postgres='ok', redis='ok')


@app.get('/')
def index():
    try:
        with database() as conn:
            db_time = conn.execute('SELECT CURRENT_TIMESTAMP').fetchone()[0]
        session_id = request.cookies.get('session_id', '')
        if not re.fullmatch(r'[0-9a-f]{64}', session_id):
            session_id = secrets.token_hex(32)
        key = f'session:{session_id}:visits'
        with cache.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, SESSION_TTL)
            visits, _ = pipe.execute()
    except Exception:
        app.logger.exception('Request failed')
        return jsonify(error='Dependency unavailable'), 503

    response = jsonify(
        message='Local DevOps lab',
        database_time=db_time.isoformat(),
        session_visits=visits,
        forwarded={
            'for': request.headers.get('X-Forwarded-For'),
            'proto': request.headers.get('X-Forwarded-Proto'),
            'host': request.headers.get('X-Forwarded-Host'),
        },
    )
    response.set_cookie('session_id', session_id, max_age=SESSION_TTL,
                        secure=True, httponly=True, samesite='Lax')
    return response
