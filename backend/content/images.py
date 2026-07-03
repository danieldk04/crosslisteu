"""
Featured-image generatie voor content_pages, zelfde patroon als in de
Revaleur blog-automation: Gemini image-modellen eerst, gratis
Pollinations.ai (Flux) als fallback zodat een ontbrekende GOOGLE_API_KEY
nooit een publicatie blokkeert.

Prompt-stijl is bewust concreet en actie-gericht (fotograferen, inpakken,
verzendlabel printen) in plaats van vage "candid lifestyle moment"-taal —
die laatste liet het model te vrij en leverde irrelevante scenes op
(bijv. iemand die in bed lag i.p.v. een reselling-actie).
"""
import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODELS = ["gemini-2.5-flash-image", "gemini-3.1-flash-image"]

# Eén scene per content-topic, meest-specifieke term eerst gecontroleerd
# (dict-volgorde bepaalt matchvolgorde) zodat een combo-keyword als
# "marktplaats naar vinted" niet per ongeluk op het verkeerde topic matcht.
TOPIC_PROMPTS = [
    ("verzendlabel", "close-up of real hands holding a smartphone photographing a folded sweater laid flat on a wooden table, ring light visible at the edge of frame, product-listing photography setup, photorealistic"),
    ("kleding", "a real person steaming a piece of clothing on a hanger against a plain wall, preparing it for an online listing photo, natural daylight, photorealistic"),
    ("marktplaats naar vinted", "a real person photographing a folded jacket flat on a table with a smartphone, small ring light visible, clean neutral background, product-listing photography setup, photorealistic"),
    ("vinted naar ebay", "a real person packing a folded clothing item into a poly mailer bag on a desk, a shipping label and printer visible nearby, photorealistic"),
    ("2dehands naar vinted", "a real person photographing a folded clothing item flat on a table with a smartphone, small ring light visible, clean neutral background, photorealistic"),
    ("marktplaats", "a real person carrying a labeled cardboard box to a car trunk for a local pickup handoff, driveway setting, daylight, photorealistic"),
    ("ebay", "close-up of real hands applying a printed shipping label to a cardboard box on a desk covered with bubble wrap, photorealistic"),
    ("vinted", "a real person photographing a folded jacket flat on a table with a smartphone, small ring light visible, clean neutral background, product-listing photography setup, photorealistic"),
]
DEFAULT_PROMPT = "a real person at a desk photographing a folded clothing item with a smartphone for an online listing, small ring light, clean neutral background, photorealistic"


def _prompt_for_keyword(keyword: str) -> str:
    kw = keyword.lower()
    for topic, prompt in TOPIC_PROMPTS:
        if topic in kw:
            return prompt
    return DEFAULT_PROMPT


def _full_prompt(keyword: str) -> str:
    base = _prompt_for_keyword(keyword)
    return (
        f'Hyperrealistic editorial photograph for a reselling/e-commerce blog. Topic: "{keyword}". '
        f"{base}. Real, natural-looking human, editorial lighting, shallow depth of field, "
        "warm neutral tones, photorealistic skin and fabric texture, sharp focus on the product. "
        "3:2 landscape orientation. No text, no watermarks, no logos, no brand names visible."
    )


def _generate_with_gemini(keyword: str) -> str | None:
    if not settings.google_api_key:
        return None

    prompt = _full_prompt(keyword)
    for model_id in GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={settings.google_api_key}"
            resp = httpx.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60,
            )
            if resp.status_code != 200:
                logger.warning(f"Gemini {model_id}: HTTP {resp.status_code}")
                continue
            data = resp.json()
            parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            for part in parts:
                inline = part.get("inlineData")
                if inline and inline.get("data"):
                    return inline["data"]
        except Exception as e:
            logger.warning(f"Gemini {model_id} fout: {e}")
    return None


def _generate_with_pollinations(keyword: str) -> str | None:
    import base64
    import random

    full_prompt = _full_prompt(keyword) + ", DSLR quality, sharp focus"
    seed = random.randint(0, 999999)
    try:
        resp = httpx.get(
            "https://image.pollinations.ai/prompt/" + full_prompt.replace(" ", "%20"),
            params={"width": 1200, "height": 800, "model": "flux", "seed": seed, "nologo": "true"},
            timeout=90,
        )
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode("utf-8")
    except Exception as e:
        logger.warning(f"Pollinations fallback mislukt: {e}")
        return None


def generate_featured_image_base64(keyword: str) -> str | None:
    """Retourneert base64 JPEG data, of None als beide providers falen (publicatie gaat dan zonder image door)."""
    image = _generate_with_gemini(keyword)
    if image:
        logger.info(f"Featured image via Gemini voor '{keyword}'")
        return image

    image = _generate_with_pollinations(keyword)
    if image:
        logger.info(f"Featured image via Pollinations voor '{keyword}'")
        return image

    logger.warning(f"Geen featured image kunnen genereren voor '{keyword}' — publiceer zonder")
    return None
