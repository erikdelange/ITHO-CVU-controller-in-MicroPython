import json
import logging
import time

import machine
import s2pico
import uasyncio as asyncio

import abutton
import ntp
from ahttpserver import (CRLF, MimeType, ResponseHeader, Server, StatusLine, sendfile)
from itho import ITHOREMOTE
from tasks import Tasks


print(f"Starting {__name__}")
logger = logging.getLogger(__name__)

# Controller
tasks = Tasks()
remote = ITHOREMOTE()

# User interface
app = Server()


@app.route("GET", "/")
async def root(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.TEXT_HTML)
    writer.write(CRLF)
    await writer.drain()
    await sendfile(writer, "index.html")


@app.route("GET", "/favicon.ico")
async def favicon(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.IMAGE_X_ICON)
    writer.write(CRLF)
    await writer.drain()
    await sendfile(writer, "favicon.ico")


@app.route("GET", "/api/init")
async def api_init(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.APPLICATION_JSON)
    writer.write(CRLF)
    await writer.drain()
    settings = dict()
    settings["start_low"] = "{:02d}:{:02d}".format(tasks.task["start_low"][0], tasks.task["start_low"][1])
    settings["start_medium"] = "{:02d}:{:02d}".format(tasks.task["start_medium"][0], tasks.task["start_medium"][1])
    writer.write(json.dumps(settings))


@app.route("GET", "/api/datetime")
async def api_datetime(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.APPLICATION_JSON)
    writer.write(CRLF)
    await writer.drain()
    t = time.localtime()
    timestring = "{:02d}-{:02d}-{:04d} {:02d}:{:02d}:{:02d}".format(t[2], t[1], t[0], t[3], t[4], t[5])
    writer.write(json.dumps({"datetime": timestring}))


@app.route("GET", "/api/set")
async def api_set(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.APPLICATION_JSON)
    writer.write(CRLF)
    await writer.drain()
    parameters = request["parameters"]
    if "start_low" in parameters:
        tasks.task["start_low"][0] = int(parameters["start_low"][:2])
        tasks.task["start_low"][1] = int(parameters["start_low"][3:])
    if "start_medium" in parameters:
        tasks.task["start_medium"][0] = int(parameters["start_medium"][:2])
        tasks.task["start_medium"][1] = int(parameters["start_medium"][3:])
    writer.write(json.dumps(parameters))
    tasks.save()

@app.route("GET", "/api/click")
async def api_button_low(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()
    parameters = request["parameters"]
    if "button" in parameters:
        value = parameters["button"]
        if value == "Low":
            remote.low()
        elif value == "Medium":
            remote.medium()
        elif value == "High":
            remote.high()
        elif value == "10%20Min":
            remote.timer10()
        elif value == "20%20Min":
            remote.timer20()
        elif value == "30%20Min":
            remote.timer30()
        elif value == "Join":
            remote.join()
        elif value == "Leave":
            remote.leave()
    writer.write(json.dumps(parameters))


@app.route("GET", "/api/reset")
async def api_reset(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()
    machine.reset()


@app.route("GET", "/api/stop")
async def api_stop(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()
    raise(KeyboardInterrupt)


async def scheduler():
    """ Run scheduled tasks """

    def elegible(scheduled_time):
        """ Check if scheduled time lies between now and the last time the scheduler ran """
        s_mins = scheduled_time[0] * 60 + scheduled_time[1]

        if prev_mins < s_mins <= curr_mins:
            return True
        return False

    tm = time.localtime()[3:5]
    prev_mins = tm[0] * 60 + tm[1]

    while True:
        tm = time.localtime()[3:5]
        curr_mins = tm[0] * 60 + tm[1]

        # just three tasks, no complex data structures needed
        # check tasks one by one to see if they are elegible to run
        if elegible(tasks.task["start_low"]) is True:
            remote.low()
        if elegible(tasks.task["start_medium"]) is True:
            remote.medium()
        if elegible(tasks.task["ntp_time_sync"]) is True:
            asyncio.create_task(ntp.sync())
        prev_mins = curr_mins
        await asyncio.sleep(60)  # wakeup every minute (at most)


try:
    def handle_exception(loop, context):
        # uncaught exceptions end up here
        import sys

        logger.exception(context["exception"], "global exception handler")

        sys.exit()

    # the user button on the s2pico stops the system
    def _keyboardinterrupt():
        raise(KeyboardInterrupt)

    pb = abutton.Pushbutton(s2pico.button, suppress=True)
    pb.press_func(_keyboardinterrupt, ())

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    loop.create_task(ntp.sync())  # initial time synchronization
    loop.create_task(scheduler())
    loop.create_task(app.start())

    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    asyncio.run(app.stop())
    asyncio.new_event_loop()
