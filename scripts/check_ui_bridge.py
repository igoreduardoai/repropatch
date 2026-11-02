import sys,json,re,base64,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from repropatch.config import Settings
from repropatch.api import create_app
from repropatch.worker import process_next
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
root=ROOT
OUT=ROOT/'.data'/'ui-check';OUT.mkdir(parents=True,exist_ok=True)
settings=Settings(Path(tempfile.mkdtemp(prefix='repropatch-ui-')),'preview-operator-token')
app=create_app(settings);store=app.state.store;client=TestClient(app)
errors=[]
def bridge(source,payload):
    if not payload['path'].startswith('/api/'):raise ValueError('Only API routes accepted')
    r=client.request(payload.get('method','GET'),payload['path'],headers=payload.get('headers',{}),content=payload.get('body'))
    return {'status':r.status_code,'headers':dict(r.headers),'body':base64.b64encode(r.content).decode()}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=__import__('os').getenv('CHROMIUM_EXECUTABLE','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.expose_binding('apiBridge',bridge)
 css=(root/'web/public/style.css').read_text()
 page.set_content(f'<html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>{css}</style></head><body><div id="app"></div><div id="overlay"></div><div id="toast" role="status"></div></body></html>')
 page.add_script_tag(content='''
 window.fetch=async function(input,options={}) {
  const result=await window.apiBridge({path:String(input),method:options.method||'GET',headers:Object.fromEntries(new Headers(options.headers)),body:options.body??null});
  const bytes=Uint8Array.from(atob(result.body),c=>c.charCodeAt(0));
  return new Response(bytes,{status:result.status,headers:result.headers});
 };
 if(!crypto.randomUUID) crypto.randomUUID=()=>[1,1,1,1].map(()=>crypto.getRandomValues(new Uint32Array(1))[0].toString(16).padStart(8,'0')).join('-');
 ''')
 api=(root/'web/public/assets/api.js').read_text().replace('export ','')
 js=(root/'web/public/assets/app.js').read_text()
 js=re.sub(r'^import .*?;\n','',js,flags=re.M)
 svg=(root/'web/public/favicon.svg').read_bytes();data='data:image/svg+xml;base64,'+base64.b64encode(svg).decode()
 js=js.replace('/favicon.svg',data)
 page.add_script_tag(content=api+'\n'+js,type='module')
 page.wait_for_selector('#operator-token');page.locator('#operator-token').fill('preview-operator-token')
 page.get_by_role('button',name='Connect workspace').click()
 page.wait_for_selector('#start-empty');page.locator('#start-empty').click();page.wait_for_timeout(200)
 assert process_next(store,settings)
 page.wait_for_selector('.verdict.pass',timeout=10000)
 page.locator('#toast').evaluate("e=>e.classList.remove('visible')")
 page.screenshot(path=str(OUT/'ReproPatch_Workbench_Desktop.png'),full_page=True)
 page.get_by_role('button',name='Patch diff',exact=True).click();page.wait_for_selector('.diff .added')
 page.locator('#toast').evaluate("e=>e.classList.remove('visible')")
 page.screenshot(path=str(OUT/'ReproPatch_Patch_Diff.png'),full_page=True)
 page.get_by_role('button',name='Evidence',exact=True).click();page.wait_for_selector('.artifact-row')
 assert page.locator('.artifact-row').count()==3
 with page.expect_download() as download_info:page.get_by_role('button',name='Download',exact=True).first.click()
 assert download_info.value.suggested_filename
 page.get_by_role('button',name='New run',exact=True).click();page.select_option('#method','W0')
 page.get_by_role('button',name='Run fixture',exact=True).click();page.wait_for_timeout(200)
 assert process_next(store,settings)
 page.wait_for_selector('.verdict.fail',timeout=10000)
 page.get_by_role('button',name='Evaluation',exact=True).click();page.wait_for_selector('.comparison-cards')
 assert page.get_by_text('NO RESULTS YET',exact=True).count()==1
 page.get_by_role('button',name='Settings',exact=True).click();assert page.get_by_text('BLOCKED',exact=True).count()==1
 page.get_by_role('button',name='Workbench',exact=True).click()
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200)
 overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
 page.locator('#toast').evaluate("e=>e.classList.remove('visible')")
 page.screenshot(path=str(OUT/'ReproPatch_Workbench_Mobile.png'),full_page=True)
 assert not overflow,'Viewport overflow on mobile'
 browser.close()
assert not errors,errors
report={'delivery':'in-memory ASGI bridge, not deployed networking','desktop':'1440x1100','mobile':'390x844','page_errors':errors,'horizontal_overflow':False,'checks':['operator login','W1 fixture verified','timeline','patch diff','three artifacts','artifact download','W0 fixture rejected','evaluation no model metrics','live blocked in settings','mobile viewport']}
(OUT/'ui-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
