import datetime as dt
from zoneinfo import ZoneInfo
import os

import yaml
import gkeepapi
import requests


class BookingBlocker:

    def __init__(self, base_url):
        self.base_url = base_url
        self.__referer_url = ''
        self.__session = requests.Session()
        self.__default_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "pt-BR,pt;q=0.9",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }
        self.__responses = []

    def block(self, chairs):
        self.__step_001_get_poltronas()
        self.__step_002_post_poltronas(poltronas=chairs)
        self.__step_003_get_reserva(qtd=len(chairs))
        self.__step_004_get_pag_page(qtd=len(chairs))
        self.__step_005_post_pagamento()

        res = self.__responses
        self.__response = []

        return res

    def __step_001_get_poltronas(self):
        url = f"{self.base_url}/guararest/seleciona-poltronas-guararest.php"
        params = {"dt": "07-09-2026", "hr": "09-30", "qtd": "6"}

        response = self.__session.get(
            url,
            headers=self.__default_headers,
            params=params
        )
        print(f"[001] GET poltronas — status: {response.status_code}")
        # print(self.__session.cookies.get_dict())
        self.__referer_url = response.url
        self.__responses.append(response.status_code)

    def __step_002_post_poltronas(self, poltronas):
        url = f"{self.base_url}/guararest/seleciona-poltronas-guararest.php"
        params = {"dt": "07-09-2026", "hr": "09-30", "qtd": "6"}

        headers = self.__default_headers | {
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "referer": self.__referer_url,
        }

        body = {p: "okay" for p in poltronas}

        response = self.__session.post(
            url,
            headers=headers,
            params=params,
            data=body
        )
        print(f"[002] POST poltronas — status: {response.status_code}")
        self.__referer_url = response.url
        self.__responses.append(response.status_code)

    def __step_003_get_reserva(self, qtd):
        url = f"{self.base_url}/guararest/reserva-trem-guararema-restaurante.php"
        params = {
            "dt": "07-09-2026",
            "hr": "09-30",
            "adt": "0",
            "crs": "0",
            "bab": "0",
            "qtd": qtd,
            "vlr": "0",
        }

        headers = self.__default_headers | {
            "cache-control": "max-age=0",
            "referer": self.__referer_url,
        }

        response = self.__session.get(url, headers=headers, params=params)
        print(f"[003] GET reserva — status: {response.status_code}")
        self.__referer_url = response.url
        self.__responses.append(response.status_code)

    def __step_004_get_pag_page(self, qtd):
        url = f"{self.base_url}/guararest/pag-guararest.php"
        params = {
            "dt": "07-09-2026",
            "hr": "09-30",
            "qtd": qtd,
            "adt": qtd,
            "crs": "0",
            "bab": "0",
            "vlr": f"{310 * qtd:.02f}",
        }

        headers = self.__default_headers | {"referer": self.__referer_url}

        response = self.__session.get(url, headers=headers, params=params)
        print(f"[004] GET pag-page — status: {response.status_code}")
        self.__referer_url = response.url
        self.__responses.append(response.status_code)

    def __step_005_post_pagamento(self):
        url = f"{self.base_url}/pay/pgm-guararest.php"

        headers = self.__default_headers | {
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "referer": self.__referer_url,
        }

        body = {
            "namex": "Anderson matias Ferreira",
            "cpfx": "445.004.060-00",
            "emailx": "and@email.com",
            "telx": "(11) 9 3667-7776",
            "namePartix[]": "Anderson matias Ferreira",
            "TitCardNome": "",
            "TitCardCPF": "",
            "TitCardRG": "",
            "TitCardCEP": "",
            "TitCardAdress": "",
            "TitCardCNro": "",
            "TitCardCCplt": "",
            "TitCardBairro": "",
            "TitCardCidade": "",
            "TitCardEstado": "",
        }

        response = self.__session.post(url, headers=headers, data=body)
        print(f"[005] POST pagamento — status: {response.status_code}")
        self.__responses.append(response.status_code)

        return None


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


def format_date(date):

    return f"{date:%Y-%m-%d %H:%M:%S}"


def handler(event, context):

    keep = GKeepManager(
        os.getenv("GACCOUNT"),
        os.getenv("GACCOUNT_MASTER_TOKEN")
    )
    config = keep.get_config()
    bb = BookingBlocker(os.getenv("BASE_URL"))
    res = bb.block(config["reservas"])

    t = dt.datetime.now().astimezone(ZoneInfo(os.getenv("IANA_TZ")))
    config["ultima_execucao"] = format_date(t)
    config["proxima_execucao"] = format_date(t + dt.timedelta(minutes=15))

    keep.update_gkeep_note(config)

    return {"foo": "bar"}
