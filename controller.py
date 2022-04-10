import ntp
import json
import machine
import sys
import time
import uasyncio as asyncio
import s2pico

import abutton
from ahttpserver import CRLF, MimeType, ResponseHeader, Server, StatusLine, sendfile
from itho import ITHOREMOTE

# Run times for scheduled tasks
# format = "task name": [hh, mm]
tasks = {
    "start_low": [22, 30],
    "start_medium": [7, 0],
    "ntp_time_sync": [5, 0]
}

try:
    # load previously saved run times (if found)
    with open("tasks.json") as fp:
        temp = json.loads(fp.read())

    # reject file if keys and data types don't match dict 'tasks'
    if not all(key in temp for key in tasks):
        raise KeyError("missing key in tasks.json")
    for key in temp:
        if not (type(temp[key]) is list and len(temp[key]) == 2):
            raise TypeError("expected list with length of 2")

    tasks = temp
except (ValueError, KeyError, TypeError) as e:
    sys.print_exception(e)
except OSError as e:
    print(e, "- file tasks.json not found")

remote = ITHOREMOTE()

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
    settings["start_low"] = "{:02d}:{:02d}".format(tasks["start_low"][0], tasks["start_low"][1])
    settings["start_medium"] = "{:02d}:{:02d}".format(tasks["start_medium"][0], tasks["start_medium"][1])
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
        tasks["start_low"][0] = int(parameters["start_low"][:2])
        tasks["start_low"][1] = int(parameters["start_low"][3:])
    if "start_medium" in parameters:
        tasks["start_medium"][0] = int(parameters["start_medium"][:2])
        tasks["start_medium"][1] = int(parameters["start_medium"][3:])
    writer.write(json.dumps(parameters))
    try:
        with open("tasks.json", "w") as fp:
            json.dump(tasks, fp)
    except Exception as e:
        sys.print_exception(e)


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
    sys.exit()


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
        if elegible(tasks["start_low"]) is True:
            remote.low()
        if elegible(tasks["start_medium"]) is True:
            remote.medium()
        if elegible(tasks["ntp_time_sync"]) is True:
            asyncio.create_task(ntp.sync())
        prev_mins = curr_mins
        await asyncio.sleep(60)  # wakeup every minute (at most)


def set_global_exception_handler():
    def handle_exception(loop, context):
        # uncaught exceptions raised in route handlers end up here
        print("global exception handler:", context)

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


try:
    set_global_exception_handler()

    pb = abutton.Pushbutton(s2pico.button, suppress=True)
    pb.press_func(sys.exit, ())

    asyncio.create_task(ntp.sync())  # initial time synchronization
    asyncio.create_task(scheduler())
    asyncio.run(app.start())  # must be last, does not return
except KeyboardInterrupt:
    pass
finally:
    asyncio.run(app.stop())
    asyncio.new_event_loop()
