from aiohttp import web
import os

async def index(request):
    with open("index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")

async def app_js(request):
    with open("app.js", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="application/javascript")

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/app.js", app_js)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)

