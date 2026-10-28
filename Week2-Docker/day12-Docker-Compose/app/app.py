
import os
import time
import redis
import psycopg2
from flask import Flask, jsonify

app = Flask(__name__)


def get_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=6379,
        decode_responses=True,
        socket_connect_timeout=3
    )


def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=3
    )


@app.route("/")
def index():
    hits = get_redis().incr("hits")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS visits "
                "(id serial PRIMARY KEY, ts timestamptz DEFAULT now())"
            )
            cur.execute("INSERT INTO visits DEFAULT VALUES")
            cur.execute("SELECT count(*) FROM visits")
            total = cur.fetchone()[0]

    return f"Redis hits: {hits} | Postgres visits: {total}\n"


@app.route("/health")
def health():
    return "ok"


@app.route("/breakdown")
def breakdown():
    # Get the total number of requests tracked by Redis
    hits = get_redis().get("hits")
    hits = int(hits) if hits is not None else 0

    # Get visit statistics from PostgreSQL
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM visits")
            total_visits = cur.fetchone()[0]

            cur.execute(
                "SELECT id, ts FROM visits ORDER BY id DESC LIMIT 5"
            )
            recent_visits = cur.fetchall()

    return jsonify({
        "redis": {
            "total_hits": hits
        },
        "postgres": {
            "total_visits": total_visits,
            "recent_visits": [
                {"id": row[0], "timestamp": row[1].isoformat()}
                for row in recent_visits
            ]
        }
    })


if __name__ == "__main__":
    for attempt in range(20):
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            break
        except Exception:
            if attempt == 19:
                raise
            time.sleep(2)

    app.run(host="0.0.0.0", port=5000)
