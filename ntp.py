import time

import machine
import ntptime
import uasyncio as asyncio


async def sync(tries=5, winter_offset=+1, summer_offset=+2):
    """ Synchronize RTC with NTP and adjust to timezone

    From https://forum.micropython.org/viewtopic.php?f=2&t=4034

    :param tries int: number of retries if NTP server cannot be reached
    :param winter_offset int: offset from UTC for local winter time (default is for CET)
    :param summer_offset int: offset from UTC for local summer time (default is for CET)
    :return bool: True if sync succesful else False
    """
    print("Synchronize time with", ntptime.host, end="")

    while tries > 0:
        try:
            ntptime.settime()  # UTC
            print()
            break
        except OSError:
            print(".", end="")
            tries -= 1
            await asyncio.sleep(0.5)
    else:
        print("\nNTP time synchronization failed")
        return False

    t = time.time()

    tm = list(time.localtime(t))
    tm = tm[0:3] + [0, ] + tm[3:6] + [0, ]
    year = tm[0]

    # datetime of change to summer time for the current year
    t1 = time.mktime((year, 3, (31 - (int(5 * year / 4 + 4)) % 7), 1, 0, 0, 0, 0))
    # datetime of change to winter time for the current year
    t2 = time.mktime((year, 10, (31 - (int(5 * year / 4 + 1)) % 7), 2, 0, 0, 0, 0))

    if t >= t1 and t < t2:
        tm[4] += 2  # local time offset from UTC in summer, +2 for CET
    else:
        tm[4] += 1  # local time offset from UTC in winter, +1 for CET

    machine.RTC().datetime(tm)

    return True


if __name__ == "__main__":
    asyncio.run(sync())
