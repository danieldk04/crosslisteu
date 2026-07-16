#!/usr/bin/env python3
"""
One-off backfill: injecteert relevante platform-logo's in de body van elke
al-gepubliceerde content_pages-rij die er nog geen heeft. Nodig nadat de
content-pijplijn platform-afbeeldingen ging toevoegen — bestaande blogs
(gepubliceerd vóór die wijziging) krijgen ze zo alsnog met terugwerkende
kracht. Nieuwe pagina's krijgen ze automatisch via run_pipeline().

Idempotent: inject_platform_images() slaat rijen over die al een
/assets/platforms/-figuur bevatten, dus dit script mag veilig meerdere keren
draaien.

Usage:
    python3 scripts/backfill_platform_images.py          # toepassen
    python3 scripts/backfill_platform_images.py --dry-run # alleen tonen
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main(dry_run: bool = False):
    from backend.content.web_images import inject_platform_images, strip_platform_images, platforms_in
    from backend.database import get_db

    db = get_db()
    rows = db.table("content_pages").select("*").eq("status", "published").execute().data or []
    print(f"{len(rows)} gepubliceerde pagina('s) gevonden")

    updated = skipped = 0
    for row in rows:
        body = row.get("body_html") or ""
        language = row.get("language", "en")
        keyword = row.get("primary_keyword", "")

        # Strip eventuele eerder-geïnjecteerde platform-figuren en (her)injecteer
        # met de huidige screenshots + opmaak. Idempotent: draait de body al op de
        # nieuwste versie, dan verandert er niets en slaan we de rij over.
        clean = strip_platform_images(body)
        new_body = inject_platform_images(clean, keyword, language=language)

        if new_body == body:
            skipped += 1
            continue

        names = [p["name"] for p in platforms_in(keyword + " " + clean)][:4]
        n_figs = new_body.count("/assets/platforms/")
        print(f"→ {row['region']}:{row['pillar']}:{row['slug']} ({language}) — {n_figs} screenshot(s): {', '.join(names)}")

        if not dry_run:
            db.table("content_pages").update({"body_html": new_body}).eq("id", row["id"]).execute()
        updated += 1

    verb = "zou bijwerken" if dry_run else "bijgewerkt"
    print(f"\n{updated} pagina('s) {verb}, {skipped} overgeslagen (al up-to-date / geen platform genoemd)")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
