import datetime as dt
from zoneinfo import ZoneInfo
import os
import json
from time import sleep

import boto3
import yaml
import gkeepapi
import requests
from bs4 import BeautifulSoup


GREEN_CIRCLE_EMOJI = "\U0001f7e2"
# ORANGE_CIRCLE_EMOJI = "\U0001f7e0"
RED_CIRCLE_EMOJI = "\U0001f534"


class BookingBlocker:

    def __init__(self, base_url, retries=6):
        self.base_url = base_url
        self.retries = retries
        self.__referer_url = ''
        self.__session = requests.Session()
        self.__default_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "pt-BR,pt;q=0.9",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }
        self.__responses = []

    def block(self, table_num, dt, hr):

        chairs = [f"ms{table_num}_cdr_{c}" for c in "cd"]

        self.__step_001_get_poltronas(table_num, dt, hr)
        self.__step_002_post_poltronas(poltronas=chairs, dt=dt, hr=hr)
        self.__step_003_get_reserva(qtd=len(chairs), dt=dt, hr=hr)
        self.__step_004_get_pag_page(qtd=len(chairs), dt=dt, hr=hr)
        self.__step_005_post_pagamento()

        res = self.__responses
        self.__responses = []

        return res

    def is_table_available(self, content, table_num):

        soup = BeautifulSoup(content, "html.parser")

        form = soup.find(id="myForm")
        tables = form.find_all(
            id=f"mesa-1{table_num:02d}"
        )

        return len(tables) == 1

    def __step_001_get_poltronas(self, table_num, dt, hr):
        url = f"{self.base_url}/guararest/seleciona-poltronas-guararest.php"
        params = {"dt": dt, "hr": hr, "qtd": "6"}

        available = False
        for k in range(self.retries):
            response = self.__session.get(
                url,
                headers=self.__default_headers,
                params=params
            )
            available = self.is_table_available(response.content, table_num)
            self.__responses.append(available)
            if available:
                break

            print(f"Table {table_num} not available yet. Try [{k+1}/{self.retries}]")
            sleep(10)

        if not available:
            self.__responses.append(404)
            msg = f"Table {table_num} unavailable after {self.retries} retries"
            raise Exception(msg)

        print(f"[001] GET poltronas — status: {response.status_code}")
        # print(self.__session.cookies.get_dict())
        self.__referer_url = response.url

    def __step_002_post_poltronas(self, poltronas, dt, hr):
        url = f"{self.base_url}/guararest/seleciona-poltronas-guararest.php"
        params = {"dt": dt, "hr": hr, "qtd": "6"}

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

    def __step_003_get_reserva(self, qtd, dt, hr):
        url = f"{self.base_url}/guararest/reserva-trem-guararema-restaurante.php"
        params = {
            "dt": dt,
            "hr": hr,
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

    def __step_004_get_pag_page(self, qtd, dt, hr):
        url = f"{self.base_url}/guararest/pag-guararest.php"
        params = {
            "dt": dt,
            "hr": hr,
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

    return f"{date:%Y-%m-%dT%H:%M}"


def update_empata_reserva_schedule(schedule_name, date):

    fmt_date = f"{format_date(date)}:00"
    scheduler = boto3.client("scheduler")
    curr_schedule = scheduler.get_schedule(Name=schedule_name)

    curr_schedule["ScheduleExpression"] = f"at({fmt_date})"

    del curr_schedule["ResponseMetadata"]
    del curr_schedule["Arn"]
    del curr_schedule["CreationDate"]
    del curr_schedule["LastModificationDate"]

    res = scheduler.update_schedule(**curr_schedule)

    print(f"Updated schedule {res['ScheduleArn']} to {fmt_date}")


def handler(event, context):

    keep = None
    if os.getenv("ENV") == "local":
        keep = GKeepManager(
            os.getenv("GACCOUNT"),
            os.getenv("GACCOUNT_MASTER_TOKEN"),
        )
    else:
        ssm = boto3.client("ssm")
        creds_ssm = ssm.get_parameter(Name=os.getenv("SSM_GACCOUNT_CREDENTIALS"))
        creds = json.loads(creds_ssm["Parameter"]["Value"])

        keep = GKeepManager(
            creds["gaccount"],
            creds["gaccount_master_token"],
        )

    config = keep.get_config()
    print(config)
    bb = BookingBlocker(os.getenv("BASE_URL"))
    res = bb.block(config["numero_mesa"], config["data"], config["hora"])

    t = dt.datetime.now().astimezone(ZoneInfo(os.getenv("IANA_TZ")))
    t_next = t + dt.timedelta(minutes=15)
    config["ultima_execucao"] = format_date(t)
    config["proxima_execucao"] = format_date(t_next)
    config["requests_status"] = ' '.join([
        GREEN_CIRCLE_EMOJI if s else RED_CIRCLE_EMOJI for s in res
    ])

    keep.update_gkeep_note(config)
    update_empata_reserva_schedule(os.getenv("SCHEDULE_NAME"), t_next)

    return config
