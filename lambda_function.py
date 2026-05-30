import datetime as dt
import os

import yaml
import gkeepapi


class BookingBlocker:

    def block(self, chairs):
        print("TODO: blocking")


class GKeepManager:

    def __init__(self, gaccount, gaccount_master_token):
        self.__keep = gkeepapi.Keep()
        self.__keep.authenticate(gaccount, gaccount_master_token)
        self.__gnote = self.__get_gkeep_note()

    def __get_gkeep_note(self):

        # gnotes = keep.all()
        gnotes = self.__keep.find(
            labels=[self.__keep.findLabel('empata_reserva')]
        )

        for note in gnotes:
            return note

        return None

    def get_config(self):

        config = None
        if self.__gnote:
            config = yaml.safe_load(self.__gnote.text)
            return config

        return None

    def update_gkeep_note(self, config):

        self.__gnote.text = yaml.dump(config, allow_unicode=True)
        self.__keep.sync()


def handler(event, context):

    keep = GKeepManager(
        os.getenv("GACCOUNT"),
        os.getenv("GACCOUNT_MASTER_TOKEN")
    )
    config = keep.get_config()
    BookingBlocker().block(config["reservas"])

    t = dt.datetime.now()
    config["ultima_execucao"] = f"{t.isoformat()}"
    config["proxima_execucao"] = f"{(t + dt.timedelta(minutes=15)).isoformat()}"

    keep.update_gkeep_note(config)

    return {"foo": "bar"}
