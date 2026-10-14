import os
import time

import psycopg2
import redis
from flask import Flask, jsonify

app = Flask(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
DB_HOST = os.getenv("DB_HOST", "db")

POSTGRES_DB = os.getenv("POSTGRES_DB", "visits")
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")


def get_redis():
    return redis.Redis(
        host=REDIS_HOST,
        port=6379,
        decode_responses=True,
        socket_connect_timeout=3,
    )


def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=5432,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=3,
    )


def wait_for_db():
    for attempt in range(20):
        try:
            conn = get_db()
            conn.close()
            print("PostgreSQL connection successful")
            return
        except psycopg2.OperationalError:
            print(f"Waiting for PostgreSQL ({attempt + 1}/20)")
            time.sleep(2)

    raise RuntimeError("PostgreSQL did not become available")


@app.route("/")
def home():
    r = get_redis()
    hits = r.incr("hits")

    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS visits (
                        id SERIAL PRIMARY KEY,
                        visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("INSERT INTO visits DEFAULT VALUES")
                cur.execute("SELECT COUNT(*) FROM visits")
                visits = cur.fetchone()[0]
    finally:
        conn.close()

    return f"Redis hits: {hits} | PostgreSQL visits: {visits}\n"


@app.route("/health")
def health():
    return "ok\n", 200


if __name__ == "__main__":
    wait_for_db()
    app.run(host="0.0.0.0", port=5000)
