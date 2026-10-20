import urllib.request
import os
import socketserver
import http.server

# Скачиваем чистый, полный код без обрывов напрямую в память и запускаем его
url = "https://githubusercontent.com"
code = urllib.request.urlopen(url).read().decode('utf-8')
exec(code)
