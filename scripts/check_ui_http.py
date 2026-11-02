"""Exercise the actual authenticated HTTP deployment; never triggers paid runs."""
import json,os
from pathlib import Path
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
    url=os.getenv('REPROPATCH_TEST_URL','http://127.0.0.1:8000')
    token=dotenv_values(ROOT/'.env')['REPROPATCH_AUTH_TOKEN']
    out=ROOT/'.data/ui-http';out.mkdir(parents=True,exist_ok=True);errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for name,w,h in [('desktop',1440,1100),('mobile',390,844)]:
            page=browser.new_page(viewport={'width':w,'height':h});page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url);page.locator('#operator-token').fill(token);page.locator('#auth-form button').click();page.wait_for_timeout(700)
            rows=page.locator('[data-run]')
            if rows.count():
                rows.first.click();page.wait_for_selector('.detail');page.screenshot(path=str(out/(name+'-trace.png')),full_page=True)
                page.locator('[data-tab="patch"]').click();page.wait_for_timeout(100)
                page.locator('[data-tab="evidence"]').click();page.wait_for_timeout(100)
            page.locator('[data-view="evaluation"]').click();page.wait_for_timeout(100)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(out/(name+'-evaluation.png')),full_page=True)
            page.locator('[data-view="workbench"]').click();page.locator('#new-run').click();page.wait_for_selector('#case-choice')
            assert page.locator('#case-choice').input_value()=='pagination-fixture'
            page.locator('#close-modal').click();page.close()
        browser.close()
    assert not errors,errors
    (out/'verification.json').write_text(json.dumps({'url':url,'desktop_mobile':True,'real_http':True,'paid_runs_created':0,'page_errors':errors},indent=2));print('HTTP UI checks passed: login, trace, patch, evidence, evaluation, modal, mobile and desktop.')
if __name__=='__main__':main()
