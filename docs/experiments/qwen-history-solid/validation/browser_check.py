from pathlib import Path
import json
from playwright.sync_api import sync_playwright
here=Path(__file__).resolve().parent;root=here/'unpacked_final';external=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
 context=browser.new_context(offline=True,viewport={'width':1600,'height':1100})
 page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
 page.on('request',lambda req:external.append(req.url) if req.url.startswith(('http://','https://')) else None)
 page.goto((root/'index.html').as_uri(),wait_until='load')
 assert not page.locator('#scores').is_checked()
 assert page.locator('.score').count()==100
 assert page.locator('.score').evaluate_all("els => els.every(e => getComputedStyle(e).display === 'none')")
 page.locator('img').evaluate_all("els => els.forEach(e => e.loading='eager')")
 page.wait_for_function("Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)",timeout=60000)
 dimensions=page.locator('img').evaluate_all("els => els.map(e=>[e.naturalWidth,e.naturalHeight])")
 assert len(dimensions)==100 and all(x==[1400,1120] for x in dimensions)
 page.screenshot(path=str(here/'browser_blind.png'))
 visible=lambda:page.locator('.case').evaluate_all("els => els.filter(e=>!e.hidden).length")
 assert visible()==44
 page.select_option('#window','128');assert visible()==32
 page.check('#short');assert visible()==20
 page.uncheck('#short');page.select_option('#window','256');assert visible()==32
 page.select_option('#window','');page.check('#short');assert visible()==27
 page.uncheck('#short');page.fill('#search','pilot_group_02_C03_s097_e225');assert visible()==1
 assert page.locator('.case:visible .panel').count()==3
 page.check('#scores');assert page.locator('.score').evaluate_all("els=>els.every(e=>getComputedStyle(e).display==='block')")
 page.screenshot(path=str(here/'browser_scores.png'))
 page.uncheck('#scores');assert page.locator('.score').evaluate_all("els=>els.every(e=>getComputedStyle(e).display==='none')")
 assert not errors and not external
 report={'passed':True,'browser':browser.version,'protocol':'file://','network_offline':True,'external_requests':external,'javascript_errors':errors,'images_decoded':len(dimensions),'default_scores_hidden':True,'show_hide_toggle_passed':True,'all_44_segments_visible_by_default':True,'128_256_short_search_filters_passed':True,'human_labels':'unfilled CSV independently checked by bundle_check.py'}
 (here/'browser_check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));browser.close()
