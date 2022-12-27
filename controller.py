import gc
import json
import logging
import time

import machine
import uasyncio as asyncio
from machine import Pin

import abutton
import ntp
from ahttpserver import HTTPResponse, HTTPServer, sendfile
from ahttpserver.sse import EventSource
from cc1101 import CC1101
from config import GD02_PIN, ITHO_REMOTE_ID, ITHO_REMOTE_TYPE, SPI_ID, SS_PIN, BUTTON
from itho import ITHOREMOTE
from tasks import Tasks


logger = logging.getLogger(__name__)

# Controller
tasks = Tasks()
cc1101 = CC1101(SPI_ID, SS_PIN, GD02_PIN)
remote = ITHOREMOTE(cc1101, ITHO_REMOTE_TYPE, ITHO_REMOTE_ID)

# User interface
app = HTTPServer()


@app.route("GET", "/")
async def root(reader, writer, request):
    response = HTTPResponse(200, "text/html")
    await response.send(writer)
    await sendfile(writer, "index.html")


@app.route("GET", "/favicon.ico")
async def favicon(reader, writer, request):
    response = HTTPResponse(200, "image/x-icon")
    await response.send(writer)
    await sendfile(writer, "favicon.ico")


@app.route("GET", "/api/init")
async def api_init(reader, writer, request):
    response = HTTPResponse(200, "application/json")
    await response.send(writer)
    settings = dict()
    settings["start_low"] = f"{tasks.task['start_low'][0]:02d}:{tasks.task['start_low'][1]:02d}"
    settings["start_medium"] = f"{tasks.task['start_medium'][0]:02d}:{tasks.task['start_medium'][1]:02d}"
    writer.write(json.dumps(settings))


@app.route("GET", "/api/datetime")
async def api_datetime(reader, writer, request):
    """ Setup a server sent event connection to the client continuously updating the date and time """
    eventsource = await EventSource(reader, writer)
    while True:
        await asyncio.sleep(1)
        t = time.localtime()
        try:
            await eventsource.send(event="datetime", data=f"{t[2]:02d}-{t[1]:02d}-{t[0]:04d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}")
        except Exception:
            break  # close connection


@app.route("GET", "/api/set")
async def api_set(reader, writer, request):
    response = HTTPResponse(200)
    await response.send(writer)
    parameters = request.parameters
    if "start_low" in parameters:
        tasks.task["start_low"][0] = int(parameters["start_low"][:2])
        tasks.task["start_low"][1] = int(parameters["start_low"][3:])
    if "start_medium" in parameters:
        tasks.task["start_medium"][0] = int(parameters["start_medium"][:2])
        tasks.task["start_medium"][1] = int(parameters["start_medium"][3:])
    tasks.save()


@app.route("GET", "/api/click")
async def api_button(reader, writer, request):
    response = HTTPResponse(200)
    await response.send(writer)
    parameters = request.parameters
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


@app.route("GET", "/api/reset")
async def api_reset(reader, writer, request):
    """ Hard reset, useful after remote software update via FTP """
    response = HTTPResponse(200)
    await response.send(writer)
    machine.reset()


@app.route("GET", "/api/stop")
async def api_stop(reader, writer, request):
    """ Force asyncio scheduler to stop, just like ctrl-c on the repl """
    response = HTTPResponse(200)
    await response.send(writer)
    raise(KeyboardInterrupt)


# End of user interface code

async def scheduler_task():
    """ Run scheduled tasks at specific times """

    def eligible(scheduled_time):
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
        # check tasks one by one to see if they are eligible to run
        if eligible(tasks.task["start_low"]) is True:
            remote.low()
        if eligible(tasks.task["start_medium"]) is True:
            remote.medium()
        if eligible(tasks.task["ntp_time_sync"]) is True:
            asyncio.create_task(ntp.sync())
        prev_mins = curr_mins
        await asyncio.sleep(60)  # wakeup every minute (at most)

async def free_memory_task():
    """ Free memory every 60 seconds """
    while True:
        gc.collect()
        gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
        await asyncio.sleep(60)

try:
    def handle_exception(loop, context):
        # uncaught exceptions end up here
        import sys
        logger.exception(context["exception"], "global exception handler")
        sys.exit()

    # the user button on the microcontroller stops the asyncio scheduler
    def _keyboardinterrupt():
        raise(KeyboardInterrupt)

    pb = abutton.Pushbutton(Pin(BUTTON, Pin.IN, Pin.PULL_UP), suppress=True)
    pb.press_func(_keyboardinterrupt, ())

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    loop.create_task(ntp.sync())  # initial time synchronization
    loop.create_task(scheduler_task())
    loop.create_task(free_memory_task())
    loop.create_task(app.start())

    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    asyncio.run(app.stop())
    asyncio.new_event_loop()
