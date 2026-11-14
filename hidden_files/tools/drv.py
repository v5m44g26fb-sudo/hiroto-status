# Reconstructed verification driver (original /tmp/drv.py lost in a runtime
# restart on 2026-11-14 night; start_game and play_day are verbatim from the
# original, the three helpers are re-derived from the game's own DOM).
import asyncio, json
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8931/index.html"

def score(fx):
    return (fx.get("dist",0)*3 + fx.get("cog",0)*2 + fx.get("fol",0)/4000
            - fx.get("flm",0)*4 + fx.get("xp",0)*0.2)

async def ev(pg, expr):
    return await pg.evaluate(expr)

async def wait_state(pg, pred, timeout=20):
    for _ in range(timeout*2):
        if await ev(pg, f"() => !!({pred})"):
            return True
        await pg.wait_for_timeout(500)
    return False

async def start_game(pg, route="sakuya", name="なお", stance_idx=None):
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console:"+m.text) if m.type == "error" else None)
    await pg.goto(BASE)
    await pg.wait_for_selector("#scr-title.on", timeout=15000)
    await pg.evaluate("() => { localStorage.removeItem('debut-status-v1'); }")
    await pg.reload()
    await pg.wait_for_selector("#scr-title.on", timeout=15000)
    await pg.locator("#btn-start").click()
    await pg.wait_for_selector("#scr-world.on", timeout=10000)
    await pg.locator("#worlds .opt:not([disabled])").first.click()
    await pg.wait_for_selector("#btn-world:not([disabled])", timeout=5000)
    await pg.locator("#btn-world").click()
    await pg.wait_for_selector("#scr-persona.on", timeout=10000)
    await pg.locator("#handles .opt").first.click()
    cards = pg.locator("#stances .opt")
    if stance_idx is None:
        best, bs = 0, -1e9
        n = await cards.count()
        for i in range(n):
            t = await cards.nth(i).inner_text()
            s = 0
            for kw, w in (("安定",3),("堅実",2),("無難",2),("バランス",1),("攻め",-2),("炎上",-3),("際ど",-2)):
                if kw in t: s += w
            if s > bs: bs, best = s, i
        stance_idx = best
    await cards.nth(stance_idx).click()
    await pg.wait_for_selector("#btn-persona:not([disabled])", timeout=5000)
    await pg.locator("#btn-persona").click()
    await pg.wait_for_selector("#scr-target.on", timeout=10000)
    torder = await ev(pg, "() => ['hiroto','sakuya']")
    await pg.locator("#targets .opt").nth(0 if route == "hiroto" else 1).click()
    await pg.wait_for_selector("#btn-target:not([disabled])", timeout=5000)
    await pg.locator("#btn-target").click()
    await pg.wait_for_selector("#scr-first.on", timeout=10000)
    await pg.locator("#firsts .opt").first.click()
    await pg.wait_for_selector("#btn-first:not([disabled])", timeout=5000)
    await pg.locator("#btn-first").click()
    await pg.wait_for_selector("#v-x.on", timeout=15000)
    return errs

async def dismiss_intro(pg):
    for _ in range(4):
        if await pg.locator("#dayintro.on").count():
            await pg.locator("#dayintro").click()
            await pg.wait_for_timeout(700)
        else:
            break

async def dismiss_dm_modal(pg):
    if await pg.locator("#dmunlock.on").count():
        await pg.locator("#du-later").click()
        await pg.wait_for_timeout(400)

async def answer_dms(pg):
    await dismiss_dm_modal(pg)
    btn = pg.locator('button[data-pane="msg"]')
    if not await btn.count():
        return
    await btn.first.click()
    await pg.wait_for_timeout(500)
    for _ in range(10):
        pend = await ev(pg, "() => S.threads.filter(t=>!t.done).length")
        if not pend:
            break
        await dismiss_dm_modal(pg)
        opened = await ev(pg, """() => { const t=S.threads.find(t=>!t.done); if(!t) return false; openThread(t); return true; }""")
        if not opened:
            break
        await pg.wait_for_timeout(600)
        nch = await pg.locator("#th-choices .dmchoice").count()
        if nch:
            fxs = await ev(pg, "() => curThread.choices.map(c=>c.fx||{})")
            bi = max(range(len(fxs)), key=lambda i: score(fxs[i]))
            await pg.locator("#th-choices .dmchoice").nth(bi).click()
            await pg.wait_for_timeout(1400)
        back = pg.locator("#dm-back")
        if await back.count():
            await back.click()
            await pg.wait_for_timeout(400)
    home = pg.locator('button[data-pane="home"]')
    if await home.count():
        await home.first.click()
        await pg.wait_for_timeout(400)

async def play_day(pg, post_mode="best", ev_mode="best", act_mode="best", steer=None):
    """Play the current day to its end. Returns a snapshot dict."""
    await dismiss_intro(pg)
    await dismiss_dm_modal(pg)
    # 1) post
    if not await ev(pg, "() => S.posted"):
        chs = await ev(pg, "() => curCH()[S.ch-1].posts.map(p=>({t:p.tx, fx:p.fx||{}, mis:!!p.mispost||((p.img||'').includes('mispost'))}))")
        if post_mode in ("best", "nomispost"):
            cand = [(score(c["fx"]), i) for i, c in enumerate(chs) if not c["mis"]]
            idx = max(cand)[1] if cand else 0
        elif post_mode == "mispost":
            idx = next((i for i, c in enumerate(chs) if c["mis"]), 0)
        elif post_mode == "worst":
            idx = min(range(len(chs)), key=lambda i: score(chs[i]["fx"]))
        else:
            idx = int(post_mode)
        await pg.locator("#x-compose-btn").click()
        await pg.wait_for_selector("#x-compose.on", timeout=8000)
        await pg.locator("#postopts .xcopt").nth(idx).click()
        await pg.wait_for_timeout(300)
        await pg.locator("#xc-post").click()
        await wait_state(pg, "() => S.posted", 15)
        await pg.wait_for_timeout(600)
    # 2) event (inline card in the timeline)
    if not await ev(pg, "() => S.evDone"):
        chs = await ev(pg, "() => curCH()[S.ch-1].event.choices.map(x=>x.fx||{})")
        idx = max(range(len(chs)), key=lambda i: score(chs[i])) if ev_mode == "best" else 0
        btns = pg.locator("#eventslot .evchoice")
        if await btns.count() > idx:
            await btns.nth(idx).scroll_into_view_if_needed()
            await btns.nth(idx).click()
        await wait_state(pg, "() => S.evDone", 10)
        await pg.wait_for_timeout(400)
    # 3) DMs
    await answer_dms(pg)
    # 4) activity
    if not await ev(pg, "() => S.actDone"):
        await pg.locator("#btn-activity").click()
        await pg.wait_for_selector("#scrim-act.on", timeout=8000)
        acts = await ev(pg, "() => curCH()[S.ch-1].activity.map(a=>a.fx||{})")
        idx = max(range(len(acts)), key=lambda i: score(acts[i])) if act_mode == "best" else 0
        btns = pg.locator("#actopts .actopt")
        if await btns.count() > idx:
            await btns.nth(idx).click()
            await pg.wait_for_timeout(300)
            await pg.locator("#act-go").click()
        await wait_state(pg, "() => S.actDone", 10)
        await pg.wait_for_timeout(900)
        close = pg.locator('[data-close="scrim-act"]')
        if await close.count():
            await close.first.click()
            await pg.wait_for_timeout(400)
    if steer:
        await ev(pg, "() => { const st = %s; for (const k in st) S[k]=st[k]; }" % json.dumps(steer))
    # 5) next day / ending
    await pg.locator("#btn-nextday").click()
    await pg.wait_for_selector("#dayresult.on", timeout=10000)
    await pg.wait_for_timeout(600)
    await pg.locator("#dr-go").click()
    await pg.wait_for_timeout(1200)
    return await ev(pg, "() => ({day:S.ch, fol:S.fol, cog:S.cog, flm:S.flm, dist:S.dist, xp:S.xp, posted:S.posted})")
