"""
This webserver serves index.html as a minecraft status (which can be either Bedrock or Java Edition)
"""

import socket  # handling errors

import fastapi
import mcstatus
import uvicorn
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from mcstatus.bedrock_status import BedrockStatusResponse
from mcstatus.pinger import PingResponse
from mcstatus.querier import QueryResponse

load_dotenv()
import os
import sys
import traceback

import aiohttp

server_name = os.getenv("SERVER_NAME")
server_host = os.getenv("SERVER_HOST")
server_port = os.getenv("SERVER_PORT", 25565)

app = fastapi.FastAPI(docs_url=None)
template = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

geolocation = None  # required for ping


async def intializer():
    async with aiohttp.ClientSession() as ses:
        async with ses.get("https://api.ipify.org") as res:
            ip = await res.text()

    global geolocation
    async with aiohttp.ClientSession() as ses:
        async with ses.get(
            f"http://ip-api.com/json/{ip}?fields=status,message,continent,country,regionName,isp,reverse,mobile,proxy,hosting"
        ) as resp:
            geolocation = await resp.json()


def hide_path(string: str) -> str:
    normal = string.replace(os.getcwd(), "REDACTED")
    # also hide package paths but not . (dot)
    for package in sys.path:
        if package != ".":
            normal = normal.replace(package, "REDACTED")
    return normal


def process_traceback(exc: Exception):
    return f"{exc.__class__.__name__}\n" + hide_path(
        "\n".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    )


@app.on_event("startup")
async def start():
    await intializer()


# Let's just handle 404s ourselves
@app.exception_handler(404)
async def http_exception_handler(request: fastapi.Request, exc: Exception):
    return template.TemplateResponse(
        "404.html",
        {"thingies": process_traceback(exc), "request": request},
        status_code=404,
    )


@app.exception_handler(500)
async def http_exception_handler(request: fastapi.Request, exc: Exception):
    return template.TemplateResponse(
        "500.html",
        {"thingies": process_traceback(exc), "request": request},
        status_code=500,
    )

@app.exception_handler(RequestValidationError)
async def http_exception_handler(request: fastapi.Request, exc: Exception):
    return template.TemplateResponse(
        "422.html",
        {"thingies": process_traceback(exc), "request": request},
        status_code=422,
    )

@app.get("/")
async def index(request: fastapi.Request):
    return template.TemplateResponse(
        "index.html",
        {
            "title": server_name,
            "request": request,
            "host": server_host,
            "port": server_port,
        },
    )


@app.get("/custom")
async def specific_server(request: fastapi.Request, server: str, port: int = 25565):
    return template.TemplateResponse(
        "index.html",
        {"title": server, "request": request, "host": server, "port": port},
    )


def process_java(info: PingResponse, query: QueryResponse = None):
    j = []
    if info.players.sample:
        for player in info.players.sample:
            j.append({"name": player.name, "id": player.id})
    return {
        "status": True,
        "version": info.version.name,
        "protocol": info.version.protocol,
        "players": {
            "online": info.players.online,
            "max": info.players.max,
            "players": j,
        },
        "description": info.description,
        "favicon": info.favicon if info.favicon else None,  # bytes
        "latency": info.latency,
        "type": "java",
        "query": {
            "plugins": query.software.plugins if query else None,
            "players": {
                "online": query.players.online if query else None,
                "max": query.players.max if query else None,
                "players": query.players.names if query else None,
            },
            "brand": query.software.brand if query else None,
            "version": query.software.version if query else None,
            "motd": query.motd if query else None,
            "map": query.map if query else None,
        },
    }


def process_bedrock(info: BedrockStatusResponse):
    return {
        "status": True,
        "version": info.version.version,
        "brand": info.version.brand,
        "protocol": info.version.protocol,
        "latency": info.latency,
        "players": {
            "online": info.players_online,
            "max": info.players_max,
        },
        "motd": info.motd,
        "map": info.map,
        "gamemode": info.gamemode,
    }


@app.get("/api/server/")
async def server(host: str, port: int = None):
    try:
        a = mcstatus.JavaServer(host, port)
        try:
            return process_java(await a.async_status(), await a.async_query())
        except (OSError, socket.gaierror, socket.timeout):
            try:
                return process_java(
                    await a.async_status()
                )  # query failed because server doesn't have it enabled
            except (OSError, socket.gaierror, socket.timeout):  # not valid server
                return {"status": False}
    except (OSError, socket.gaierror, socket.timeout):
        try:
            a = mcstatus.BedrockServer(host, port)
            return process_bedrock(await a.async_status())
        except (OSError, socket.gaierror, socket.timeout):
            return {"status": False}


@app.get("/api/geo")
async def geo():
    return geolocation


@app.get("/api/raise")
async def raiser():
    raise Exception("test")


@app.get("/favicon.ico")
async def favicon():
    return fastapi.responses.FileResponse("static/favicon.ico")


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=int(os.getenv("SERVER_HOST_PORT", 10000))
    )
