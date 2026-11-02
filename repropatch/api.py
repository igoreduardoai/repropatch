from pathlib import Path
import hashlib
import hmac
import json
import re
import uuid
from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import Settings, ROOT
from .auditor import status as auditor_status
import os
from .models import RunCreate
from .store import Store, now
from .budget import Budget
from .cases import Registry, CaseError
from .evaluation import summarize

ID=re.compile(r'^[a-f0-9]{32}$')

def create_app(settings:Settings|None=None):
    settings=settings or Settings.load()
    store=Store(settings.db_path)
    budget=Budget(settings.db_path,settings.live_budget_usd,settings.run_budget_usd)
    app=FastAPI(title='ReproPatch API',version='0.1.0',docs_url=None,redoc_url=None,openapi_url=None)
    registry=Registry(settings.cases_root,settings.acceptance_key)
    app.state.store=store;app.state.settings=settings;app.state.registry=registry

    def auth(authorization:str|None=Header(default=None)):
        if not settings.auth_token:
            raise HTTPException(503,'Configure REPROPATCH_AUTH_TOKEN. Anonymous access is disabled.')
        expected='Bearer '+settings.auth_token
        if not authorization or not hmac.compare_digest(authorization,expected):
            raise HTTPException(401,'Operator token required',headers={'WWW-Authenticate':'Bearer'})

    def require_run(rid):
        if not ID.fullmatch(rid):raise HTTPException(404,'Run not found')
        run=store.get(rid)
        if not run:raise HTTPException(404,'Run not found')
        return run

    @app.middleware('http')
    async def security_headers(request:Request,call_next):
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.get('/healthz')
    def health():return {'status':'ok','service':'repropatch-api','version':'0.1.0'}

    @app.get('/api/config',dependencies=[Depends(auth)])
    def config():
        # Live needs the explicit flag AND at least one case with signed, current acceptance evidence.
        accepted=registry.accepted_cases()
        live=settings.enable_live and bool(accepted) and not budget.summary()['halted']
        return {'model':settings.meta_model,'provider':'Meta Model API',
            'live_enabled':live,
            'configured_live_request':settings.enable_live,
            'live_cases':[c.public() for c in accepted] if settings.enable_live else [],
            'fixture_enabled':True,'run_cap_usd':float(settings.run_budget_usd),
            'batch_cap_usd':float(settings.live_budget_usd),
            'reason':('Live enabled for accepted registered cases only.' if live else
                      'Live blocked: needs REPROPATCH_ENABLE_LIVE and a registered case with signed acceptance evidence.'),
            'advisory_auditor':{**auditor_status(),'opt_in':os.getenv('REPROPATCH_ENABLE_AUDITOR','false').lower()=='true'},
            'single_operator':True,'max_upload_mb':settings.max_upload_bytes//1024//1024}

    @app.get('/api/runs',dependencies=[Depends(auth)])
    def runs():return {'items':store.list()}

    @app.post('/api/runs',status_code=201,dependencies=[Depends(auth)])
    def create(payload:RunCreate,idempotency_key:str|None=Header(default=None)):
        if idempotency_key and (len(idempotency_key)>100 or not re.fullmatch(r'[A-Za-z0-9_-]+',idempotency_key)):
            raise HTTPException(400,'Invalid idempotency key')
        if payload.mode=='fixture' and payload.case_id!='pagination-fixture':
            raise HTTPException(400,'Fixture mode only runs the built-in fixture case')
        if payload.mode=='live':
            if budget.summary()['halted']:raise HTTPException(409,'Ledger halted: reconcile unknown billing before new execution.')
            # Cheap, host-side checks only; the worker re-validates and owns Docker access.
            if not settings.enable_live:
                raise HTTPException(409,'Live is disabled. No paid call has been made.')
            try:case=registry.load(payload.case_id)
            except CaseError:raise HTTPException(400,'Case is not registered')
            status=registry.acceptance_status(case)
            if not status['accepted']:
                raise HTTPException(409,'Case has no valid acceptance evidence: '+status['reason'])
            if not payload.video_id:raise HTTPException(400,'The reviewed case video upload is required')
        if payload.video_id:
            with store.connection() as c:
                if not c.execute('SELECT id FROM uploads WHERE id=?',(payload.video_id,)).fetchone():
                    raise HTTPException(400,'Video does not exist')
        try:return store.create(payload.model_dump(),idempotency_key)
        except ValueError as exc:raise HTTPException(409,str(exc))

    @app.get('/api/runs/{rid}',dependencies=[Depends(auth)])
    def run(rid:str):
        row=require_run(rid)
        artifacts=store.artifacts(rid)
        return {**row,'events':store.events(rid),
                'artifacts':[{k:v for k,v in a.items() if k!='path'} for a in artifacts]}

    @app.get('/api/runs/{rid}/events',dependencies=[Depends(auth)])
    def events(rid:str,after:int=0):
        require_run(rid);return {'items':store.events(rid,max(0,after))}

    @app.post('/api/runs/{rid}/cancel',dependencies=[Depends(auth)])
    def cancel(rid:str):require_run(rid);return store.cancel(rid)

    @app.get('/api/runs/{rid}/artifacts/{aid}',dependencies=[Depends(auth)])
    def artifact(rid:str,aid:str):
        require_run(rid)
        artifact=next((a for a in store.artifacts(rid) if a['id']==aid),None)
        if not artifact:raise HTTPException(404,'Artifact not found')
        path=Path(artifact['path']).resolve();root=(settings.data_dir/'artifacts'/rid).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise HTTPException(404,'Artifact not found')
        return FileResponse(path,media_type=artifact['content_type'],filename=artifact['name'])

    @app.get('/api/budget',dependencies=[Depends(auth)])
    def get_budget():return budget.summary()

    @app.get('/api/evaluation',dependencies=[Depends(auth)])
    def evaluation():
        return summarize(store.list())

    @app.post('/api/videos',dependencies=[Depends(auth)])
    async def video(file:UploadFile=File(...)):
        if not file.filename or not file.filename.lower().endswith('.mp4'):
            raise HTTPException(415,'Only MP4 is accepted')
        uid=uuid.uuid4().hex;root=settings.data_dir/'uploads';root.mkdir(exist_ok=True)
        path=root/(uid+'.mp4');size=0;digest=hashlib.sha256();prefix=b''
        try:
            with path.open('wb') as f:
                while chunk:=await file.read(1024*1024):
                    size+=len(chunk)
                    if size>settings.max_upload_bytes:raise HTTPException(413,'Video exceeds 50 MiB')
                    if not prefix:prefix=chunk[:32]
                    digest.update(chunk);f.write(chunk)
            if size<12 or b'ftyp' not in prefix[4:12]:
                raise HTTPException(415,'MP4 signature not found; verify container format')
            # Signature check is not full media validation; ffprobe sandbox check is required for live use.
            with store.connection() as c:
                c.execute('INSERT INTO uploads VALUES(?,?,?,?,?,?)',
                          (uid,str(path),Path(file.filename).name,size,digest.hexdigest(),now()))
            return {'id':uid,'size':size,'sha256':digest.hexdigest(),'sent_to_meta':False}
        except Exception:
            path.unlink(missing_ok=True);raise
        finally:await file.close()

    web=ROOT/'web'/'public'
    if web.exists():app.mount('/',StaticFiles(directory=web,html=True),name='web')
    return app

app=create_app()
