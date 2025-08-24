# Bind & workers
bind = "0.0.0.0:8000"
workers = 2  # override con env GUNICORN_WORKERS
threads = 1
timeout = 60
graceful_timeout = 30
keepalive = 5

# Logs a stdout/stderr (colectables por Docker)
accesslog = "-"
errorlog = "-"
loglevel = "info"  # override con env LOG_LEVEL

# Respeto de cabeceras de proxy
forwarded_allow_ips = "*"
proxy_protocol = False
