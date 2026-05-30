import os

import requests


BASE_URL = os.getenv('BASE_URL')
session = requests.Session()


# Headers comuns reutilizados em todas as requisições
HEADERS_BASE = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "pt-BR,pt;q=0.9",
    "priority": "u=0, i",
    "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}


# ─────────────────────────────────────────────────────────────
# 001 - GET poltronas (seleção de poltronas)
# ─────────────────────────────────────────────────────────────
def step_001_get_poltronas():
    url = f"{BASE_URL}/guararest/seleciona-poltronas-guararest.php"
    params = {"dt": "07-09-2026", "hr": "09-30", "qtd": "6"}

    headers = {
        **HEADERS_BASE,
        "sec-fetch-site": "none",
    }
    # Remove sec-fetch-user não presente no original desta requisição
    headers.pop("sec-fetch-user", None)

    response = session.get(url, headers=headers, params=params)
    print(f"[001] GET poltronas — status: {response.status_code}")
    print(session.cookies.get_dict())
    return response.url


# ─────────────────────────────────────────────────────────────
# 002 - POST poltronas (confirma seleção das poltronas)
# ─────────────────────────────────────────────────────────────
def step_002_post_poltronas(referer_url, poltronas):
    url = f"{BASE_URL}/guararest/seleciona-poltronas-guararest.php"
    params = {"dt": "07-09-2026", "hr": "09-30", "qtd": "6"}

    headers = {
        **HEADERS_BASE,
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "referer": referer_url,
    }
    headers.pop("sec-fetch-user", None)

    body = {p: "okay" for p in poltronas}

    response = session.post(url, headers=headers, params=params, data=body)
    print(f"[002] POST poltronas — status: {response.status_code}")
    return response.url


# ─────────────────────────────────────────────────────────────
# 003 - GET reserva (página de resumo da reserva)
# ─────────────────────────────────────────────────────────────
def step_003_get_reserva(referer_url, qtd):
    url = f"{BASE_URL}/guararest/reserva-trem-guararema-restaurante.php"
    params = {
        "dt": "07-09-2026",
        "hr": "09-30",
        "adt": "0",
        "crs": "0",
        "bab": "0",
        "qtd": qtd,
        "vlr": "0",
    }

    headers = {
        **HEADERS_BASE,
        "cache-control": "max-age=0",
        "referer": referer_url,
    }
    headers.pop("sec-fetch-user", None)

    response = session.get(url, headers=headers, params=params)
    print(f"[003] GET reserva — status: {response.status_code}")
    return response.url


# ─────────────────────────────────────────────────────────────
# 004 - GET página de pagamento
# ─────────────────────────────────────────────────────────────
def step_004_get_pag_page(referer_url, qtd):
    url = f"{BASE_URL}/guararest/pag-guararest.php"
    params = {
        "dt": "07-09-2026",
        "hr": "09-30",
        "qtd": qtd,
        "adt": qtd,
        "crs": "0",
        "bab": "0",
        "vlr": f"{310 * qtd:.02f}",
    }

    headers = {
        **HEADERS_BASE,
        "referer": referer_url,
    }

    response = session.get(url, headers=headers, params=params)
    print(f"[004] GET pag-page — status: {response.status_code}")
    return response.url


# ─────────────────────────────────────────────────────────────
# 005 - POST pagamento (submissão dos dados do titular)
# ─────────────────────────────────────────────────────────────
def step_005_post_pagamento(referer_url):
    url = f"{BASE_URL}/pay/pgm-guararest.php"

    headers = {
        **HEADERS_BASE,
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "referer": referer_url,
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

    response = session.post(url, headers=headers, data=body)
    print(f"[005] POST pagamento — status: {response.status_code}")
    return response


def reservar_poltronas(*poltronas):

    referer_url = step_001_get_poltronas()
    referer_url = step_002_post_poltronas(
        referer_url=referer_url,
        poltronas=poltronas
    )
    referer_url = step_003_get_reserva(
        referer_url=referer_url,
        qtd=len(poltronas)
    )
    referer_url = step_004_get_pag_page(
        referer_url=referer_url,
        qtd=len(poltronas)
    )
    step_005_post_pagamento(referer_url=referer_url)


if __name__ == "__main__":
    print("Iniciando fluxo de reserva...\n")

    reservar_poltronas("ms12_cdr_a", "ms12_cdr_b", "ms12_cdr_c", "ms12_cdr_d")

    print("\nFluxo concluído.")
