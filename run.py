import os
import socket

from wsgi import app

if __name__ == "__main__":
    from waitress import serve

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    port = int(os.getenv("PORT", "8040"))
    debug_mode = os.getenv("FLASK_ENV", "development") == "development"

    print(f"Local access: http://127.0.0.1:{port}")
    if not debug_mode:
        print(f"LAN access:   http://{local_ip}:{port}")

    if debug_mode:
        app.run(debug=True, host="0.0.0.0", port=port)
    else:
        serve(app, host="0.0.0.0", port=port)
