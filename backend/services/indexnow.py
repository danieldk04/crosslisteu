"""
IndexNow: pusht gepubliceerde/bijgewerkte URL's direct naar Bing/Yandex (die op hun beurt
ook Google's Search Console-crawler versneld kunnen triggeren via gedeelde IndexNow-adoptie).
Geen auth nodig — enkel een sleutel die als bewijs van site-eigendom als statisch bestand
op de root staat (frontend/{key}.txt). Faalt zacht: de pipeline mag hier nooit op vastlopen.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

INDEXNOW_KEY = "e9c75dd3136858fec240e72ecd1d275a"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
SITE_URL = "https://omnivaleur.com"


def submit_url(url_path: str) -> bool:
    """Meldt één URL bij IndexNow. Non-blocking best-effort — retourneert False bij falen."""
    try:
        response = httpx.post(
            INDEXNOW_ENDPOINT,
            json={
                "host": "omnivaleur.com",
                "key": INDEXNOW_KEY,
                "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
                "urlList": [f"{SITE_URL}{url_path}"],
            },
            timeout=10,
        )
        if response.status_code not in (200, 202):
            logger.warning(f"IndexNow gaf status {response.status_code} voor {url_path}: {response.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.error(f"IndexNow-melding mislukt (niet-blokkerend) voor {url_path}: {e}")
        return False
