import os
import yaml
import datetime as dt

import gkeepapi


GREEN_CIRCLE_EMOJI = "\U0001f7e2"
ORANGE_CIRCLE_EMOJI = "\U0001f7e0"
RED_CIRCLE_EMOJI = "\U0001f534"


def update_gkeep_note(gaccount, gaccount_master_token):
    keep = gkeepapi.Keep()
    keep.authenticate(os.getenv('GACCOUNT'), os.getenv('GACCOUNT_MASTER_TOKEN'))

    # gnotes = keep.all()
    gnotes = keep.find(labels=[keep.findLabel('empata_reserva')])

    gnote = None
    for note in gnotes:
        gnote = note
        break

    config = yaml.safe_load(gnote.text)

    # empata_reserva(config["reservas"])

    t = dt.datetime.now()
    config["ultima_execucao"] = f"{t.isoformat()} {RED_CIRCLE_EMOJI} {GREEN_CIRCLE_EMOJI} {ORANGE_CIRCLE_EMOJI}"
    config["proxima_execucao"] = (t + dt.timedelta(minutes=15)).isoformat()

    gnote.text = yaml.dump(config, allow_unicode=True)

    keep.sync()
