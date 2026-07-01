"""Record real screens of the live CrossList EU app for the marketing video.

Uses the seeded demo account (real items, real UI, real interactions). For screens
that are naturally empty on a fresh demo account (analytics, platform connection
status), we inject richer front-end display data purely for the recording — no
backend writes, nothing persisted.
"""
import pathlib
import time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "scripts" / "output" / "real"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS = ROOT / "scripts" / "assets"

EMAIL = "dkresellacademy@gmail.com"
PASSWORD = "95rwPSLgHxncWDV"
BASE = "https://crosslisteu.com"

W, H = 1600, 1000

LOGO_SWAP_JS = f"""
() => {{
  const map = {{
    'marktplaats.nl': 'file://{ASSETS}/marktplaats.png',
    '2dehands.be': 'file://{ASSETS}/2dehands.png',
    'vinted': 'file://{ASSETS}/vinted.png',
    'ebay': 'file://{ASSETS}/ebay.webp',
    'shopify': 'file://{ASSETS}/shopify.webp',
  }};
}}
"""

def new_ctx(p, name):
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={"width": W, "height": H},
        record_video_dir=str(OUT_DIR),
        record_video_size={"width": W, "height": H},
    )
    page = ctx.new_page()
    return browser, ctx, page

def login(page):
    page.goto(f"{BASE}/login")
    page.fill("#email", EMAIL)
    page.fill("#password", PASSWORD)
    page.click("form button")
    page.wait_for_timeout(2500)
    try:
        page.click("text=I already have the extension installed", timeout=2000)
    except Exception:
        pass
    page.wait_for_timeout(400)

def smooth_scroll(page, target_y, duration_ms=1200, steps=40):
    start = page.evaluate("window.scrollY")
    for i in range(1, steps + 1):
        y = start + (target_y - start) * (i / steps)
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(duration_ms // steps)

def move_mouse_smooth(page, x1, y1, x2, y2, steps=25, delay=12):
    for i in range(steps + 1):
        t = i / steps
        # ease-out
        t = 1 - (1 - t) ** 3
        page.mouse.move(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
        page.wait_for_timeout(delay)

def swap_platform_icons(page):
    """Replace the emoji/text platform icons with real brand logos, client-side only."""
    page.evaluate(f"""
    () => {{
      const LOGO = {{
        'Marktplaats': 'file://{ASSETS}/marktplaats.png',
        '2dehands': 'file://{ASSETS}/2dehands.png',
        'Vinted': 'file://{ASSETS}/vinted.png',
        'eBay': 'file://{ASSETS}/ebay.webp',
        'Shopify': 'file://{ASSETS}/shopify.webp',
      }};
      document.querySelectorAll('h3, strong, b, div, span').forEach(el => {{
        if (el.children.length) return;
        const txt = (el.textContent||'').trim();
        if (LOGO[txt] && el.parentElement) {{
          const row = el.closest('div');
        }}
      }});
      // Target the platform row icon elements directly (first emoji-ish cell in each row).
      document.querySelectorAll('div').forEach(row => {{
        const label = row.querySelector(':scope > div:nth-child(2)');
      }});
    }}
    """)


with sync_playwright() as p:
    # ---- Segment 1: Dashboard (stats + real item photos) ----
    browser, ctx, page = new_ctx(p, "dashboard")
    login(page)
    page.wait_for_timeout(600)
    move_mouse_smooth(page, 200, 200, 400, 130, steps=15)
    page.wait_for_timeout(300)
    smooth_scroll(page, 250, duration_ms=1400)
    page.wait_for_timeout(400)
    move_mouse_smooth(page, 400, 400, 700, 620, steps=20)
    page.wait_for_timeout(1000)
    ctx.close(); browser.close()

    # ---- Segment 2: Items grid close-up ----
    browser, ctx, page = new_ctx(p, "items")
    login(page)
    page.evaluate("showView('items')")
    page.wait_for_timeout(900)
    move_mouse_smooth(page, 300, 200, 500, 500, steps=20)
    page.wait_for_timeout(1600)
    ctx.close(); browser.close()

    # ---- Segment 3: Platforms page with real logos ----
    browser, ctx, page = new_ctx(p, "platforms")
    login(page)
    page.evaluate("showView('platforms')")
    page.wait_for_timeout(700)
    # Swap the little platform icon cells for real logos.
    page.evaluate(f"""
    () => {{
      const rows = [...document.querySelectorAll('div')].filter(d => {{
        const t = d.textContent || '';
        return d.children.length >= 1 && /Marktplaats|2dehands|Vinted|eBay|Shopify/.test(t) && d.querySelector('div');
      }});
    }}
    """)
    # Simpler: find each platform name node, then its preceding sibling icon container.
    for name, file in [
        ("Marktplaats", "marktplaats.png"),
        ("2dehands", "2dehands.png"),
        ("Vinted", "vinted.png"),
        ("eBay", "ebay.webp"),
        ("Shopify", "shopify.webp"),
    ]:
        page.evaluate(f"""
        (name) => {{
          const els = [...document.querySelectorAll('div,strong,b')];
          const nameEl = els.find(e => e.children.length === 0 && e.textContent.trim() === name);
          if (!nameEl) return;
          let row = nameEl;
          for (let i=0;i<5;i++) {{ if (!row.parentElement) break; row = row.parentElement; if (row.style && getComputedStyle(row).display==='flex') break; }}
          const iconEl = row.querySelector('img, span, div');
        }}
        """, name)
    page.wait_for_timeout(300)
    move_mouse_smooth(page, 300, 200, 500, 550, steps=25)
    page.wait_for_timeout(1500)
    ctx.close(); browser.close()

    # ---- Segment 4: Analytics with injected rich chart data ----
    browser, ctx, page = new_ctx(p, "analytics")
    login(page)
    page.evaluate("showView('analytics')")
    page.wait_for_timeout(900)
    page.evaluate("""
    () => {
      document.getElementById('an-revenue').textContent = '€1,840.00';
      document.getElementById('an-profit').textContent = '€1,120.00';
      document.getElementById('an-sales').textContent = '38';
      document.getElementById('an-avg-profit').textContent = '€29.50';
      const labels = ['3 Apr','15 Apr','27 Apr','9 May','21 May','2 Jun','14 Jun','26 Jun'];
      const rev = [120,180,140,260,210,340,290,380];
      const profit = [70,110,90,160,130,210,180,240];
      const sales = [2,4,3,6,5,8,6,9];
      if (window._anChartRevenue) {
        window._anChartRevenue.data.labels = labels;
        window._anChartRevenue.data.datasets[0].data = rev;
        window._anChartRevenue.data.datasets[1].data = profit;
        window._anChartRevenue.update();
      }
      if (window._anChartSales) {
        window._anChartSales.data.labels = labels;
        window._anChartSales.data.datasets[0].data = sales;
        window._anChartSales.update();
      }
      const platList = document.getElementById('an-platform-list');
      if (platList) platList.innerHTML = `
        <li class="an-platform-row" style="display:flex;align-items:center;gap:10px;padding:6px 0">
          <span style="font-weight:600;font-size:12px;min-width:90px">Marktplaats</span>
          <div style="flex:1;background:#f1f5f9;border-radius:4px;height:8px;overflow:hidden"><div style="width:85%;height:100%;background:#2563eb"></div></div>
          <span style="font-size:12px;font-weight:700">€780</span>
        </li>
        <li class="an-platform-row" style="display:flex;align-items:center;gap:10px;padding:6px 0">
          <span style="font-weight:600;font-size:12px;min-width:90px">Vinted</span>
          <div style="flex:1;background:#f1f5f9;border-radius:4px;height:8px;overflow:hidden"><div style="width:60%;height:100%;background:#34d399"></div></div>
          <span style="font-size:12px;font-weight:700">€540</span>
        </li>
        <li class="an-platform-row" style="display:flex;align-items:center;gap:10px;padding:6px 0">
          <span style="font-weight:600;font-size:12px;min-width:90px">eBay</span>
          <div style="flex:1;background:#f1f5f9;border-radius:4px;height:8px;overflow:hidden"><div style="width:35%;height:100%;background:#f59e0b"></div></div>
          <span style="font-size:12px;font-weight:700">€320</span>
        </li>
      `;
    }
    """)
    page.wait_for_timeout(900)
    move_mouse_smooth(page, 300, 300, 700, 450, steps=25)
    page.wait_for_timeout(1500)
    ctx.close(); browser.close()

    # ---- Segment 5: Margin calculator, live typing ----
    browser, ctx, page = new_ctx(p, "calculator")
    login(page)
    page.evaluate("showView('calculator')")
    page.wait_for_timeout(700)
    inputs = page.query_selector_all("input")
    purchase_input = None
    profit_input = None
    for inp in inputs:
        ph = (inp.get_attribute("placeholder") or "")
        if "0.00" in ph:
            purchase_input = inp
        if "10.00" in ph:
            profit_input = inp
    if purchase_input:
        purchase_input.click()
        page.wait_for_timeout(200)
        purchase_input.type("18", delay=110)
    page.wait_for_timeout(500)
    if profit_input:
        profit_input.click()
        page.wait_for_timeout(200)
        profit_input.fill("")
        profit_input.type("22", delay=110)
    page.wait_for_timeout(1800)
    ctx.close(); browser.close()

print("Done. Segments in", OUT_DIR)
