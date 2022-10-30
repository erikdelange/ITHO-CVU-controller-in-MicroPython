# Storage for scheduled tasks
#
# The Taaks class contains a dict with run-times for the scheduled
# tasks and functions to load this dict from a json file and store
# its content to a json file.
#
# Copyright 2022 (c) Erik de Lange
# Released under MIT license

import json


class Tasks:
    TASKS_FILE = "tasks.json"

    def __init__(self):
        self.task = {
            "start_low": [22, 30],
            "start_medium": [7, 0],
            "ntp_time_sync": [5, 0]
        }  # default values for first time use

        self.load()

    def load(self, filename=TASKS_FILE):
        try:
            # load previously saved run times (if found)
            with open(filename) as fp:
                temp = json.loads(fp.read())

            # json format and content check: reject file if keys
            # and value data types don't match dict 'self.tasks'
            if not all(key in temp for key in self.task):
                raise KeyError(f"missing key in {filename}")
            for key in temp:
                if not (type(temp[key]) is list and len(temp[key]) == 2):
                    raise TypeError("expected list with length of 2 "
                        f"for key '{key}', found {type(temp[key]).__name__}"
                    )

            self.task = temp
        except (ValueError, KeyError, TypeError) as e:
            print(f"{e.__class__.__name__} loading {filename} - {e}")
        except OSError as e:
            print(f"{e} - file {filename}")

    def save(self, filename=TASKS_FILE):
        try:
            with open(filename, "w") as fp:
                json.dump(self.task, fp)
        except OSError as e:
            logging.critical(f"[Errno {e.args[0]}] {e.args[1]}: {filename}")
