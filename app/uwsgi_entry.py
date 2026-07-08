from __future__ import annotations


def application(environ, start_response):
    body = b"monitor_price: ok\n"
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]
