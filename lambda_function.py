import datetime as dt
import os

import yaml
import gkeepapi


class BookingBlocker:

    def block(self, chairs):
        print("TODO: blocking")


def get_gkeep_note(keep):

    # gnotes = keep.all()
    gnotes = keep.find(labels=[keep.findLabel('empata_reserva')])

    gnote = None
    for note in gnotes:
        gnote = note
        break

    return gnote


def extract_config_from_note(gnote):

    config = None
    if gnote:
        config = yaml.safe_load(gnote.text)

    return config


def update_gkeep_note(keep, config):

    gnote = get_gkeep_note(keep)

    t = dt.datetime.now()
    config["ultima_execucao"] = f"{t.isoformat()}"
    config["proxima_execucao"] = f"{(t + dt.timedelta(minutes=15)).isoformat()}"

    gnote.text = yaml.dump(config, allow_unicode=True)

    keep.sync()


def handler(event, context):

    keep = gkeepapi.Keep()
    keep.authenticate(
        os.getenv("GACCOUNT"),
        os.getenv("GACCOUNT_MASTER_TOKEN")
    )

    gnote = get_gkeep_note(keep)
    config = extract_config_from_note(gnote)

    new_config = BookingBlocker().block(config["reservas"])
    print(new_config)

    update_gkeep_note(keep, config)

    return {"foo": "bar"}
