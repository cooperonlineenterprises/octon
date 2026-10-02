#!/usr/bin/env python3
"""Durable, source-only fixture facet of the existing authority/transaction owners.

The independently CURRENT keeper must stay alive. Saved state never bootstraps a
replacement keeper. Controller replacement and primary-store restoration are
bounded to that retained authority, launch handle, fence and kernel boot.
"""
from __future__ import annotations
import copy
import array
import ctypes
from datetime import datetime, timezone
import sys
if __name__=='__main__' and sys.platform!='linux':
    print('{"permission_grant":false,"execution_authorized":false,"error":"durable fixture execution profile requires Linux"}')
    raise SystemExit(2)
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import socketserver
import stat
import struct
import sys
import tempfile
import threading
import time
from contextlib import contextmanager

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'authority/scripts')]
import fixture_admission as A
import governance_shadow as G
import installation_runtime_v2 as V
import protected_fixture as P

PROFILE='octon.durable-fixture-profile.v2'
PROTOCOL='octon.durable-fixture-currentness.v3'
OWNER='octon.durable-fixture-owner.v2'
INDEX='octon.durable-fixture-reference-index.v1'
INTENT='octon.durable-fixture-publication.v1'
CONSUMPTION='octon.durable-fixture-consumption.v1'
ROOT=Path('/state/target')
AUTH=Path('/authority')
CURRENT=Path('/continuity')
IPC=Path('/ipc')
KINDS={'consumption','journal','receipt','recovery','observation','history','archive','owner','controller','control','canonical'}
NS_GET_NSTYPE=0xb703
CLONE_NEWPID=0x20000000


def namespace_proof(descriptor):
    if fcntl.ioctl(descriptor,NS_GET_NSTYPE)!=CLONE_NEWPID:raise ValueError('descriptor is not an actual PID namespace')
    value=os.fstat(descriptor)
    return {'identity':[value.st_dev,value.st_ino],'link':os.readlink('/proc/self/fd/'+str(descriptor)),'type':CLONE_NEWPID}


def received_envelope(connection):
    descriptors=[]
    try:
        data,ancillary,flags,_=connection.recvmsg(A.MAX+1,socket.CMSG_SPACE(4*array.array('i').itemsize),socket.MSG_CMSG_CLOEXEC)
        for level,kind,raw in ancillary:
            if level!=socket.SOL_SOCKET or kind!=socket.SCM_RIGHTS:raise ValueError('unexpected descriptor control message')
            values=array.array('i');values.frombytes(raw[:len(raw)-len(raw)%values.itemsize]);descriptors.extend(values)
        if flags&(socket.MSG_CTRUNC|socket.MSG_TRUNC):raise ValueError('truncated namespace descriptor message')
        while b'\n' not in data and len(data)<=A.MAX:
            more=connection.recv(A.MAX+1-len(data))
            if not more:break
            data+=more
        if not data.endswith(b'\n') or b'\n' in data[:-1] or len(data)>A.MAX:raise ValueError('unsupported bounded request framing')
        return A.strict(data),descriptors
    except BaseException:
        for descriptor in descriptors:os.close(descriptor)
        raise


def sha(data):return hashlib.sha256(data).hexdigest()


def sync_directory(path):
    descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def make_directories(path):
    missing=[];cursor=Path(path)
    while not cursor.exists():missing.append(cursor);cursor=cursor.parent
    if cursor.is_symlink():raise ValueError('durable directory symlink unsupported')
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        sync_directory(directory);sync_directory(directory.parent)


def durable_bytes(path,data,*,exclusive=False,mode=0o600):
    """Complete file data, then atomic publication, then parent acknowledgment."""
    path=Path(path);make_directories(path.parent)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as handle:
        temporary=Path(handle.name)
        try:
            handle.write(data);handle.flush();os.fsync(handle.fileno());os.chmod(temporary,mode)
            if exclusive:
                libc=ctypes.CDLL(None,use_errno=True)
                if libc.renameat2(-100,os.fsencode(temporary),-100,os.fsencode(path),1):
                    raise OSError(ctypes.get_errno(),'exclusive durable publication refused')
            else:os.replace(temporary,path)
            temporary=None;sync_directory(path.parent)
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)


def durable_json(path,value,*,exclusive=False):
    durable_bytes(path,A.canonical(value),exclusive=exclusive)


def host(keeper=False):
    P.linux_owner()
    if os.environ.get('OCTON_OWNED_DURABLE_FIXTURE')!='durable-fixture-v2':
        raise ValueError('explicit owned durable fixture marker required')
    mounts={left.split()[4]:(right.split()[0],left.split()[5]) for left,right in
            [line.split(' - ',1) for line in Path('/proc/self/mountinfo').read_text().splitlines()]}
    required=['/state','/ipc']+(['/authority','/continuity'] if keeper else [])
    for path in required:
        if path not in mounts or mounts[path][0] not in {'ext4','xfs'}:
            raise ValueError('qualified kernel named-volume binding unavailable: '+path)
    if not keeper and ('ro' not in mounts['/ipc'][1].split(',') or '/authority' in mounts or '/continuity' in mounts):
        raise ValueError('controller must have only read-only IPC and no authority/continuity mount')
    return mounts


def confined(root,value):return V.confined(Path(root),value)


def path_state(path,relative):
    try:info=path.lstat()
    except FileNotFoundError:return {'path':relative,'type':'absent','mode':None,'sha256':None}
    kind='file' if stat.S_ISREG(info.st_mode) else 'directory' if stat.S_ISDIR(info.st_mode) else 'symlink' if stat.S_ISLNK(info.st_mode) else 'other'
    return {'path':relative,'type':kind,'mode':stat.S_IMODE(info.st_mode),'sha256':sha(path.read_bytes()) if kind=='file' else None}


def canonical_path(path):
    lexical=Path(os.path.abspath(path))
    if lexical.is_relative_to(ROOT):
        confined(ROOT,lexical.relative_to(ROOT).as_posix());return True
    if lexical.resolve().is_relative_to(ROOT):raise ValueError('staging alias reaches canonical storage')
    return False


def owner_path():return ROOT/'.octon/agent/transactions/durable/authority-owner.json'


def projected_schema(value):
    # The existing qualification projection, without changing historical schemas.
    if isinstance(value,dict):return {k:(v.replace('project-dossier',r'\.octon/dossier').replace(r'\.agent',r'\.octon/agent') if k=='pattern' and isinstance(v,str) else projected_schema(v)) for k,v in value.items()}
    if isinstance(value,list):return [projected_schema(v) for v in value]
    if isinstance(value,str):return value.replace('.agent/scripts/','.octon/runtime/scripts/').replace('.agent/','.octon/agent/').replace('project-dossier/','.octon/dossier/')
    return value


def profile(root=ROOT,expected=None):
    root=Path(root);value=V.load(root/'.octon/durable-profile.json')
    schema=V.load(root/'.octon/runtime/durable-fixture-v2.schema.json')
    if G.CONTRACTS.validate_schema(value,{'$ref':'#/$defs/profile'},root_schema=schema):raise ValueError('unsupported closed durable profile')
    if expected is not None and value!=expected:raise ValueError('restored/mixed enrolled durable profile')
    V.inspect(root);P.inspect_profile(root,value['parent_profile'])
    if value['source_revision']!=V.load(root/'.octon/manifest.json')['source_revision'] or [r['path'] for r in value['assets']]!=['.octon/runtime/durable_fixture.py','.octon/runtime/durable_fixture_worker.py','.octon/runtime/durable-fixture-v2.schema.json']:
        raise ValueError('durable source/dependency inventory mismatch')
    for item in value['assets']:
        if sha(confined(root,item['path']).read_bytes())!=item['sha256']:
            raise ValueError('durable runtime dependency changed')
    return value


def install(root):
    """Fresh source-owned additive facet; never grants or ordinary generation."""
    root=Path(root);parent=V.load(root/'.octon/protected-profile.json');P.inspect_profile(root,parent)
    source=HERE.parents[2]
    inventory=V.load(source/'shared/source-contracts/durable-fixture-inventory.json')
    expected_assets=[{'source':'skills/octon-project-bootstrap/scripts/durable_fixture.py','target':'.octon/runtime/durable_fixture.py'},
                     {'source':'skills/octon-project-bootstrap/scripts/durable_fixture_worker.py','target':'.octon/runtime/durable_fixture_worker.py'},
                     {'source':'shared/source-contracts/durable-fixture-v2.schema.json','target':'.octon/runtime/durable-fixture-v2.schema.json'}]
    if inventory!={'schema_version':'octon.source.durable-fixture-inventory.v1','permission_grant':False,
                   'status':'source_only_disposable_qualification','profile_schema':PROFILE,
                   'parent_profile_schema':P.PROFILE,'currentness_schema':PROTOCOL,
                   'required_dependencies':['python>=3.11','openssl-ed25519','linux-named-volume-flock-fsync','retained-current-fixture-keeper'],
                   'assets':expected_assets}:
        raise ValueError('unsupported closed durable source inventory')
    outputs=[confined(root,row['target']) for row in expected_assets]+[confined(root,'.octon/durable-profile.json')]
    inputs=[confined(source,row['source']) for row in expected_assets]
    if any(path.exists() for path in outputs):raise ValueError('existing durable facet cannot be overwritten')
    for src,dest in zip(inputs,outputs):dest.write_bytes(src.read_bytes())
    value={'schema_version':PROFILE,'permission_grant':False,'fixture_only':True,'parent_profile':parent,
           'source_revision':V.load(root/'.octon/manifest.json')['source_revision'],
           'host_profile':'linux-durable-controller-replacement-v2','retained_dependency':'live-original-keeper-and-launch-handle-same-kernel-boot',
           'assets':[{'path':row['target'],'sha256':sha((root/row['target']).read_bytes())} for row in expected_assets],
           'source_inputs':[{'path':path.relative_to(source).as_posix(),'sha256':sha(path.read_bytes())} for path in
                            [source/'shared/source-contracts/durable-fixture-inventory.json',*inputs]]}
    durable_json(outputs[-1],value,exclusive=True)
    return value


def prepare_fixture(ticket):
    """Trusted keyless fixture preparation through existing work/packaging owners."""
    host(True)
    import shutil
    import subprocess
    import qualify_disposable_runtime as Q
    import installation_runtime as R
    import test_long_running_work as records
    from test_disposable_runtime import module
    from test_fixture_admission import seal
    if ROOT.exists() or any(AUTH.iterdir()) or any(CURRENT.iterdir()):raise ValueError('fresh owned stores required')
    old=Path('/tmp/durable-seed');Q.generate(old)
    def cli(root,*args):
        result=subprocess.run([sys.executable,'-B',root/'octon',*map(str,args)],cwd=root,capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr or result.stdout)
        return result
    start=Path('/tmp/start.json')
    cli(old,'work','start','--title','Durable fixture existing task','--scope','One exact local handoff',
        '--authority-basis','authority:current-user-disposable-fixture','--owner','fixture-owner','--operator','fixture-operator',
        '--acceptance','Preserve IDs and exact receipts','--validation','Read-only check','--next-action','Qualify replacement','--output',start)
    initial=R.load(start);cli(old,'transaction','apply','--plan',start,'--accept-digest',initial['canonical_plan_digest'])
    Q.generate(ROOT,admission=True);ROOT.chmod(0o700)
    for relative in ['tasks/TASK-0001.md','state/focus.json']:
        destination=ROOT/'.octon/agent'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(old/'.octon/agent'/relative,destination)
    synthetic=Path('/tmp/preservation-records')
    seeded=subprocess.run([sys.executable,'-B',HERE/'scaffold_project.py','--target',synthetic,'--project-name','Synthetic preserved record fixture','--profile','minimal','--layout','compact'],capture_output=True,text=True)
    if seeded.returncode:raise ValueError(seeded.stderr or seeded.stdout)
    records.accepted_decision(synthetic,'DEC-0042');records.task_and_evidence(synthetic)
    preserved=['tasks/TASK-0001.md']
    for directory in ['decisions','evidence']:
        for source in (synthetic/'.agent'/directory).iterdir():
            relative=directory+'/'+source.name;make_directories((ROOT/'.octon/agent'/relative).parent)
            shutil.copy2(source,ROOT/'.octon/agent'/relative);preserved.append(relative)
    for source in (old/'.octon/agent/transactions/receipts').glob('*.json'):
        relative='transactions/receipts/'+source.name;make_directories((ROOT/'.octon/agent'/relative).parent)
        shutil.copy2(source,ROOT/'.octon/agent'/relative);preserved.append(relative)
    P.install(ROOT);install(ROOT)
    refresh={'time':datetime.now(timezone.utc).isoformat(),'id':secrets.token_hex(16)}
    context_path=Path('/tmp/render-context.json');durable_json(context_path,{'root':str(ROOT),'refresh':refresh})
    os.environ['OCTON_FIXTURE_ADMISSION_CONTEXT']=str(context_path)
    result=subprocess.run([sys.executable,'-B',ROOT/'.octon/runtime/scripts/refresh.py','--refresh'],cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise ValueError(result.stderr or result.stdout)
    path=Path('/tmp/handoff.json')
    cli(ROOT,'work','handoff','--task-id','TASK-0001','--next-action','Continue durable fixture work',
        '--summary','Durable protected fixture handoff','--operator','fixture-operator','--output',path)
    plan=R.load(path);sys.path.insert(0,str(ROOT/'.octon/runtime/scripts'))
    tx=module(ROOT/'.octon/runtime/scripts/octon_transaction.py','durable_fixture_prepare')
    decoded=tx._decode_operations(plan);staged,_,_=tx._staged_result(ROOT,plan,decoded)
    outcomes=tx._planned_outcomes(plan,decoded,staged);paths=tx._receipt_paths(ROOT,plan,outcomes)
    record={'receipt_id':plan['planned_receipt_id'],'operation':plan['operation'],'plan_digest':plan['canonical_plan_digest'],
            'paths':paths,'created_directories':tx._created_parent_directories(ROOT,[row['path'] for row in paths])}
    bound=A.binding(ROOT,plan,record);bound['refresh']=refresh
    bundle=R.load(Q.SCRIPTS.parent/'fixtures/governance-shadow/covered-v2.json')
    now=datetime.now(timezone.utc);begin=(now-A.timedelta(minutes=1)).isoformat();end=(now+A.timedelta(hours=1)).isoformat()
    bundle['evaluation_time']=now.isoformat()
    bundle['intent']['original_expression']='Qualify one durable protected fixture handoff.'
    bundle['intent']['interpretation']='This direct invocation permits disposable qualification only.'
    for grant in bundle['delegations']:
        grant.update(valid_from=begin,valid_until=end);grant['scope']['operations']=['work.handoff'];grant['scope']['decision_classes']=['work.local_handoff']
    action=bundle['action'];controls=bundle['controls']
    action.update(operation='work.handoff',decision_class='work.local_handoff',plan_digest=bound['plan_digest'],
                  expected_state_digest=bound['expected_state_digest'],policy_digest=bound['policy_digest'],work_contract_digest=bound['work_digest'])
    bundle['work_binding']['contract_digest']=bound['work_digest']
    controls.update(observed_at=begin,fresh_until=end,state_digest=action['expected_state_digest'],policy_digest=action['policy_digest'])
    controls['policy_scope']['operations']=['work.handoff'];controls['policy_scope']['decision_classes']=['work.local_handoff']
    for budget in controls['budget_snapshots']:budget['period_accounting'].update(start=begin,end=end)
    for obligation in controls['obligation_results']:obligation.update(observed_at=begin,fresh_until=end)
    seal(bundle)
    bound.update(intent_digest=bundle['intent']['digest'],issuer_ref=bundle['intent']['principal_ref'],
                 delegation_refs=[G.delegation_reference(row) for row in bundle['delegations']],action_digest=action['digest'])
    context={'schema_version':A.CONTEXT,'fixture_authority':'current-user-disposable-admission-only','root':str(ROOT),
             'issuer_public_key':'pending-trusted-keeper','issuer_key_digest':'0'*64,'actor_ref':action['actor_ref'],
             'actor_private_key':'/tmp/no-worker-signing-key','port':0,'plan':plan,'record':record,'binding':bound,'refresh':refresh}
    # Saved configuration is not the trusted initial-launch credential.
    durable_json(AUTH/'bootstrap.json',{'context':context,'bundle':bundle,'bootstrap_digest':sha(ticket.encode())},exclusive=True)
    os.environ.pop('OCTON_FIXTURE_ADMISSION_CONTEXT',None)
    return {'schema_version':PROFILE,'permission_grant':False,'receipt_ref':record['receipt_id'],'binding_digest':A.digest(bound),
            'synthetic_preservation':[{'path':'.octon/agent/'+relative,'sha256':sha((ROOT/'.octon/agent'/relative).read_bytes())} for relative in preserved]}


def effective_time(state):
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=state['boot_id'] or not state['time_available']:
        raise ValueError('current trusted time/boot continuity unavailable')
    now=P.trusted_time(state)
    return now


class Keeper:
    """Existing authority owner, with references rather than duplicate work/grants."""
    def __init__(self,configuration,ticket):
        host(True)
        if os.getpid()!=1:raise ValueError('keeper bootstrap requires dedicated PID1')
        for path in [AUTH,CURRENT,IPC]:path.chmod(0o700)
        if any((CURRENT/name).exists() for name in ['index.json','keeper.private.pem']) or owner_path().exists():
            raise ValueError('saved state/keys/owner cannot bootstrap a current keeper')
        self.mutex=threading.RLock();self.context=configuration['context'];self.bundle=configuration['bundle'];self.mock_attempts=0;self.namespace_fds={}
        if self.context['root']!=str(ROOT) or self.context['plan']['operation']!='work.handoff':
            raise ValueError('durable fixture is one exact existing-task handoff')
        self.profile=profile();ROOT.chmod(0o700)
        self.instance=secrets.token_hex(32);self.bootstrap=ticket
        if not isinstance(self.bootstrap,str) or len(self.bootstrap)!=64:raise ValueError('trusted initial launch ticket required')
        if sha(ticket.encode())!=configuration['bootstrap_digest']:raise ValueError('saved records/new key are not trusted initial launch')
        owner={'schema_version':OWNER,'permission_grant':False,'root':str(ROOT),'profile_digest':A.digest(self.profile),
               'keeper_instance':self.instance,'bootstrap_digest':sha(self.bootstrap.encode())}
        durable_json(owner_path(),owner,exclusive=True)
        self.private,self.public=A.keypair(CURRENT,'keeper')
        self.issuer_private,issuer_public=A.keypair(AUTH,'issuer-1')
        for path in [CURRENT/'keeper.private.pem',CURRENT/'keeper.public.pem',AUTH/'issuer-1.private.pem',AUTH/'issuer-1.public.pem']:
            with path.open('rb') as handle:os.fsync(handle.fileno())
            sync_directory(path.parent)
        now=datetime.now(timezone.utc).isoformat()
        self.authority={'schema_version':'octon.durable-fixture-authority.v2','permission_grant':False,
                        'owner':owner,'context':self.context,'bundle':self.bundle,'generation':0,'control_generation':1,
                        'issuers':[{'public_key':issuer_public,'digest':sha(issuer_public.encode()),'generation':1}],
                        'controllers':[], 'allowed_commands':['apply','recover','reconcile','rollback']}
        durable_json(AUTH/'authority.json',self.authority,exclusive=True)
        self.state={'schema_version':INDEX,'permission_grant':False,'instance':self.instance,'owner_ref':sha(owner_path().read_bytes()),
                    'authority_ref':sha((AUTH/'authority.json').read_bytes()),'references':{},'nonces':[],
                    'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'clock_origin_wall':now,
                    'clock_origin_monotonic':time.monotonic(),'time_floor':now,'time_available':True}
        self.state['storage_identity']={str(path):[path.stat().st_dev,path.stat().st_ino] for path in [Path('/state'),AUTH,CURRENT,IPC]}
        durable_json(IPC/'fence.lock',{'schema_version':INDEX,'permission_grant':False,'instance':self.instance},exclusive=True)
        self.fence=(IPC/'fence.lock').stat();self.state['fence_identity']=[self.fence.st_dev,self.fence.st_ino]
        self.save()

    def save(self):
        schema=V.load(ROOT/'.octon/runtime/durable-fixture-v2.schema.json')
        if G.CONTRACTS.validate_schema(self.state,{'$ref':'#/$defs/index'},root_schema=schema):raise ValueError('unsupported closed continuity index')
        durable_json(CURRENT/'index.json',self.state)
        self.tip=sha((CURRENT/'index.json').read_bytes())

    def check(self):
        if sha((CURRENT/'index.json').read_bytes())!=self.tip or V.load(CURRENT/'index.json')!=self.state:
            raise ValueError('restored/truncated continuity differs from live current tip')
        if sha((AUTH/'authority.json').read_bytes())!=self.state['authority_ref'] or V.load(AUTH/'authority.json')!=self.authority:
            raise ValueError('stale primary authority cannot become current')
        if sha(owner_path().read_bytes())!=self.state['owner_ref']:
            raise ValueError('missing/restored canonical owner binding')
        profile(expected=self.profile)
        if any([Path(path).stat().st_dev,Path(path).stat().st_ino]!=identity for path,identity in self.state['storage_identity'].items()):raise ValueError('durable storage binding replaced')
        for controller in self.authority['controllers']:
            descriptor=self.namespace_fds.get(controller['id'])
            try:proof=namespace_proof(descriptor) if descriptor is not None else None
            except (OSError,ValueError):proof=None
            if proof is None or os.get_inheritable(descriptor) or proof['identity']!=controller['namespace_identity'] or proof['link']!=controller['pid_namespace']:raise ValueError('retained actual controller namespace handle unavailable; no metadata restoration')
        descriptor=(IPC/'fence.lock').stat()
        if [descriptor.st_dev,descriptor.st_ino]!=self.state['fence_identity']:
            raise ValueError('stable fence replaced; split domain refused')
        effective_time(self.state)

    @contextmanager
    def fence_lock(self):
        # Never acquire the mutex while waiting for the executor's fence.
        with (IPC/'fence.lock').open('rb') as handle:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                durable_json(Path('/tmp/control-contended.json'),{'permission_grant':False,'same_fence':self.state['fence_identity']})
                fcntl.flock(handle,fcntl.LOCK_EX)
            try:
                with self.mutex:self.check();yield
            finally:fcntl.flock(handle,fcntl.LOCK_UN)

    def holder(self,request):
        self.check()
        if type(request['generation']) is not int or request['generation']<1:raise ValueError('unsupported controller generation')
        if request['generation']!=self.authority['generation'] or request['controller_id']!=self.authority['controllers'][-1]['id']:
            raise ValueError('stale immutable controller enrollment')
        with (IPC/'fence.lock').open('rb') as handle:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return
            else:fcntl.flock(handle,fcntl.LOCK_UN);raise ValueError('trusted holder fence unavailable')

    def evaluation(self):
        self.check();now=effective_time(self.state);self.state['time_floor']=now.isoformat();self.save()
        bundle=copy.deepcopy(self.authority['bundle']);bundle['evaluation_time']=now.isoformat()
        copied=HERE/'authority'
        result=G.evaluate(bundle,root=copied if copied.is_dir() else G.ROOT)
        if result['coverage']!='covered':raise ValueError('current authority '+result['coverage'])
        return bundle,result,now

    def consume_nonce(self,request):
        nonce=request['nonce']
        if nonce in self.state['nonces']:raise ValueError('replayed signed keeper request')
        self.state['nonces'].append(nonce);self.save()

    def control_cas(self,body):
        if type(body['expected_control_generation']) is not int or body['expected_control_generation']!=self.authority['control_generation'] or body['expected_control_digest']!=A.digest(self.authority['bundle']):raise ValueError('stale current control CAS')

    def enroll(self,expected,namespace,request,descriptor):
        with self.fence_lock():
            self.control_cas(request['body']);self.consume_nonce(request)
            if type(expected) is not int or expected<0:raise ValueError('unsupported replacement generation')
            if not isinstance(namespace,str) or not __import__('re').fullmatch(r'pid:\[[0-9]+\]',namespace):raise ValueError('actual controller namespace required')
            proof=namespace_proof(descriptor)
            if proof['link']!=namespace or proof['identity']!=request['body']['namespace_identity']:raise ValueError('actual namespace descriptor differs from signed launch subject')
            if expected!=self.authority['generation']:raise ValueError('stale replacement enrollment CAS')
            self.authority['generation']+=1;generation=self.authority['generation'];identity=secrets.token_hex(32)
            # Credential storage is outside the canonical project/content scan.
            area=Path('/state/controllers')/str(generation);make_directories(area)
            private,public=A.keypair(area,'controller')
            for path in [private,area/'controller.public.pem']:
                with path.open('rb') as handle:os.fsync(handle.fileno())
                sync_directory(path.parent)
            retained=os.dup(descriptor);os.set_inheritable(retained,False);self.namespace_fds[identity]=retained
            row={'id':identity,'generation':generation,'public_key':public,'key_path':str(private),'pid_namespace':namespace,'namespace_identity':proof['identity']}
            self.authority['controllers'].append(row);durable_json(AUTH/'authority.json',self.authority)
            self.state['authority_ref']=sha((AUTH/'authority.json').read_bytes());self.save()
            return {**row,'keeper_public':self.public,'keeper_instance':self.instance,'fence_identity':self.state['fence_identity'],
                    'context':self.context,'parent_profile':self.profile['parent_profile']}

    def control(self,bundle,request):
        with self.fence_lock():
            self.control_cas(request['body']);self.consume_nonce(request)
            if any(bundle[k]!=self.authority['bundle'][k] for k in ['intent','delegations','action','work_binding']):
                raise ValueError('control cannot renew/expand original authority')
            old=self.authority['bundle']['controls'];new=bundle['controls']
            if not set(old['revoked_delegation_ids']).issubset(new['revoked_delegation_ids']) or old['emergency_stop'] and not new['emergency_stop'] or new['authority_epoch']<old['authority_epoch']:
                raise ValueError('authority resurrection refused')
            self.authority['bundle']=bundle;self.authority['control_generation']+=1
            durable_json(AUTH/'authority.json',self.authority);self.state['authority_ref']=sha((AUTH/'authority.json').read_bytes());self.save()
            return {'applied':True,'control_generation':self.authority['control_generation']}

    def record_path(self,kind,relative):
        if kind not in KINDS:raise ValueError('unknown record kind')
        path=confined(ROOT,relative);record=self.context['record'];identity=record['receipt_id']
        fixed={'consumption':f'.octon/agent/transactions/durable/{identity}/consumed.json',
               'journal':f'.octon/agent/transactions/pending/{identity}.json',
               'receipt':f'.octon/agent/transactions/receipts/{identity}.json',
               'recovery':f'.octon/agent/transactions/recovered/{identity}.json'}
        if kind in fixed and relative!=fixed[kind]:raise ValueError('publication outside original identity')
        if kind=='canonical' and relative not in {row['path'] for row in record['paths']}:raise ValueError('footprint expansion')
        if kind=='observation' and not relative.startswith(f'.octon/agent/transactions/evidence/{identity}/'):raise ValueError('observation subject expansion')
        if kind=='history' and relative!=f'.octon/agent/transactions/durable/{identity}/unknown-external.json':raise ValueError('history subject expansion/kind overlap')
        if kind=='archive' and not __import__('re').fullmatch(r'\.octon/agent/transactions/durable/'+identity+r'/archive/(?:journal|receipt|recovery)-[a-f0-9]{64}\.json',relative):raise ValueError('historical archive subject expansion')
        if kind in {'owner','controller','control'}:raise ValueError('administrative records are not producer publication')
        return path

    def prepare(self,kind,relative,data,delete=False):
        path=self.record_path(kind,relative);record=self.context['record'];value=None
        if type(delete) is not bool:raise ValueError('unsupported publication delete flag')
        if delete and kind not in {'journal','canonical'}:raise ValueError('consumption/terminal/history deletion forbidden')
        if kind=='archive':
            source_kind=path.name.split('-',1)[0];original=self.record_path(source_kind,{'journal':f'.octon/agent/transactions/pending/{record["receipt_id"]}.json','receipt':f'.octon/agent/transactions/receipts/{record["receipt_id"]}.json','recovery':f'.octon/agent/transactions/recovered/{record["receipt_id"]}.json'}[source_kind])
            reference=self.state['references'].get(original.relative_to(ROOT).as_posix())
            if not reference or reference['status']!='confirmed' or reference['sha256']!=sha(data) or original.read_bytes()!=data or path.name!=source_kind+'-'+sha(data)+'.json':raise ValueError('archive is not exact current canonical record bytes')
            value=A.strict(data)
            if A.lineage(value)!=A.lineage(record):raise ValueError('archive lineage changed')
            self.validate_terminal(value)
        elif kind=='canonical':
            item=next(row for row in record['paths'] if row['path']==relative)
            if delete and not any(item[field]['type']=='absent' for field in ['before','after']):raise ValueError('canonical deletion outside exact original footprint')
            if not delete and sha(data) not in {item['before']['sha256'],item['after']['sha256']}:raise ValueError('canonical bytes beyond before/postimage')
            terminal=self.record_path('receipt',f'.octon/agent/transactions/receipts/{record["receipt_id"]}.json')
            if terminal.exists() and V.load(terminal).get('status') in {'applied','rolled_back'} and (delete or not path.is_file() or sha(path.read_bytes())!=sha(data)):
                raise ValueError('terminal effect cannot change without explicit rollback-in-progress lineage')
        else:
            value=A.strict(data)
            if value.get('permission_grant') is not False:raise ValueError('record claims permission')
            if kind in {'journal','receipt','recovery'} and A.lineage(value)!=A.lineage(record):raise ValueError('forged original record lineage')
            if kind in {'journal','receipt','recovery'}:
                name='harness-transaction-v3.schema.json' if kind=='receipt' else 'harness-transaction.schema.json'
                schema=projected_schema(V.load(ROOT/'.octon/agent/schemas'/name))
                if G.CONTRACTS.validate_schema(value,{'$ref':'#/$defs/'+('pending' if kind=='journal' else kind)},root_schema=schema):raise ValueError('unsupported original transaction record schema')
            if kind=='observation':
                A.validate_observation(value,record['receipt_id']);self.validate_evidence(value['admission_evidence'])
                if path.name!=A.digest(value)+'.json':raise ValueError('observation content address changed')
            if kind in {'receipt','recovery'}:self.validate_terminal(value)
            if kind=='consumption' and value!={'schema_version':CONSUMPTION,'permission_grant':False,'lineage':A.lineage(record),'binding':self.context['binding']}:raise ValueError('unsupported closed consumption lineage')
            if kind=='history' and value!={'schema_version':'octon.mock-external-outcome.v1','permission_grant':False,'receipt_ref':record['receipt_id'],'attempt_ref':'MOCK-'+A.digest(A.lineage(record)),'outcome':'unknown','replay_permitted':False}:raise ValueError('unsupported exact unknown external fixture record')
        existing=self.state['references'].get(relative)
        if existing and existing['kind']!=kind:raise ValueError('publication kinds are disjoint')
        if existing and existing['status']=='confirmed' and (not path.is_file() or sha(path.read_bytes())!=existing['sha256']):raise ValueError('publication predecessor restored/changed')
        if existing and existing['status']=='tombstone' and path.exists():raise ValueError('publication predecessor tombstone restored')
        if kind=='consumption' and existing:raise ValueError('consumed identity is never replayed')
        if existing and existing['status']=='prepared':raise ValueError('uncertain publication must reconcile before retry')
        if kind=='receipt':
            if not existing and value['status']!='applied':raise ValueError('receipt cannot start at a restored terminal state')
            if existing:
                prior=V.load(path)
                if (prior['status'],value['status']) not in {('applied','rollback_in_progress'),('rollback_in_progress','rollback_in_progress'),('rollback_in_progress','rolled_back')}:raise ValueError('receipt history transition refused')
                expected=copy.deepcopy(prior);expected['status']=value['status']
                if value['status']=='rolled_back':expected['rollback']['available']=False
                if expected!=value:raise ValueError('receipt bytes/provenance/history cannot be rewritten')
        if delete and kind=='journal' and not any(row['status']=='confirmed' and row['kind'] in {'receipt','recovery'} and V.load(confined(ROOT,row['relative'])).get('status') in {'applied','rolled_back','recovered_to_preimage'} for row in self.state['references'].values()):
            raise ValueError('journal cannot disappear without current terminal reference')
        if delete and kind=='journal' and (not existing or existing['status']!='confirmed' or not existing.get('archive_ref')):raise ValueError('journal cleanup requires exact retained historical bytes')
        if delete and kind=='journal':
            terminal=self.record_path('receipt',f'.octon/agent/transactions/receipts/{record["receipt_id"]}.json')
            recovery=self.record_path('recovery',f'.octon/agent/transactions/recovered/{record["receipt_id"]}.json')
            value=V.load(terminal if terminal.exists() else recovery)
            self.validate_postimages(value)
        entry={'schema_version':INTENT,'permission_grant':False,'kind':kind,'relative':relative,
               'sha256':sha(data),'delete':delete,'status':'prepared','generation':self.authority['generation'],
               'binding':self.context['binding'],'lineage_digest':A.digest(A.lineage(record)),
               'prior_publications':copy.deepcopy(existing.get('prior_publications',[]))+[{k:v for k,v in existing.items() if k!='prior_publications'}] if existing else []}
        self.state['references'][relative]=entry;self.save();return entry

    def validate_evidence(self,item):
        for issuer in self.authority['issuers']:
            if issuer['digest']==item['issuer_key_digest']:
                context=copy.deepcopy(self.context);context.update(issuer_public_key=issuer['public_key'],issuer_key_digest=issuer['digest'])
                return A.validate_evidence(context,item,self.context['binding'])
        raise ValueError('historical issuer not enrolled')

    def validate_terminal(self,value):
        if value.get('artifact_kind')=='transaction_receipt':
            groups=[row for row in value['validation'] if row.get('schema_version')=='octon.fixture-admission-evidence.v1' and row.get('fixture_only') is True]
            if len(groups)!=1 or not groups[0]['decisions']:raise ValueError('missing authenticated receipt provenance')
            phases={self.validate_evidence(item)['phase'] for item in groups[0]['decisions']}
            if value['status']=='applied' and not {'effect','validate'}.issubset(phases):raise ValueError('missing effect/validation provenance')

    def validate_postimages(self,value):
        field='after' if value['status'] in {'applied','rollback_in_progress'} else 'before'
        for row in value['paths']:
            actual=path_state(confined(ROOT,row['path']),row['path'])
            allowed=[row['before'],row['after']] if value['status']=='rollback_in_progress' else [row[field]]
            if actual not in allowed:raise ValueError('terminal ACK postimage differs from exact record')

    def confirm(self,kind,relative):
        path=self.record_path(kind,relative);entry=self.state['references'].get(relative)
        if not entry or entry['kind']!=kind:raise ValueError('unprepared publication')
        if entry['delete']:
            if path.exists():raise ValueError('tombstone does not match actual absence')
            if kind=='journal':
                archived=entry['prior_publications'][-1].get('archive_ref') if entry['prior_publications'] else None
                proof=self.state['references'].get(archived)
                if not proof or proof['kind']!='archive' or proof['status']!='confirmed' or proof['sha256']!=entry['sha256'] or sha(confined(ROOT,archived).read_bytes())!=entry['sha256']:raise ValueError('journal tombstone lacks exact retained archival content')
            entry['status']='tombstone'
        else:
            if not path.is_file() or sha(path.read_bytes())!=entry['sha256']:raise ValueError('missing/truncated/changed publication retains uncertainty')
            if kind=='observation':self.validate_evidence(V.load(path)['admission_evidence'])
            if kind in {'receipt','recovery'}:self.validate_terminal(V.load(path))
            if kind in {'receipt','recovery'}:
                self.validate_postimages(V.load(path))
            if kind=='canonical':
                item=next(row for row in self.context['record']['paths'] if row['path']==relative)
                if path_state(path,relative) not in [item['before'],item['after']]:raise ValueError('canonical ACK filesystem kind/mode/postimage changed')
            if kind=='archive':
                source_kind=path.name.split('-',1)[0]
                for reference in self.state['references'].values():
                    if reference['kind']==source_kind and reference['status']=='confirmed' and reference['sha256']==entry['sha256']:reference['archive_ref']=relative
            entry['status']='confirmed'
        # A replacement may see an unacknowledged rename/unlink. Reading it is
        # insufficient: synchronize the actual file and directory ancestry
        # before advancing this owner's durable confirmed/tombstone reference.
        if not entry['delete']:
            with path.open('rb') as handle:os.fsync(handle.fileno())
        parent=path.parent
        while parent.is_relative_to(ROOT):sync_directory(parent);parent=parent.parent
        sync_directory(Path('/state'))
        self.save();return entry

    def observation(self,phase):
        current,result,now=self.evaluation();bound=self.context['binding'];nonce=secrets.token_hex(32)
        request={'schema_version':A.SCHEMA,'nonce':nonce,'actor_ref':self.context['actor_ref'],'phase':phase,'binding':bound}
        deadline=min([A.timestamp(current['controls']['fresh_until'])]+[A.timestamp(row['valid_until']) for row in current['delegations']]+[A.timestamp(row['fresh_until']) for row in current['controls']['obligation_results']]+[A.timestamp(row['period_accounting']['end']) for row in current['controls']['budget_snapshots']])
        answer={'schema_version':A.SCHEMA,'request_digest':A.digest(request),'nonce':nonce,'fixture_only':True,
                'live_authorization':False,'permission_grant':False,'admitted':True,'expires_at':min(deadline,now+A.timedelta(seconds=10)).isoformat(),
                'coverage':'covered','controls_digest':current['controls']['digest'],'issuer_ref':bound['issuer_ref'],
                'actor_ref':self.context['actor_ref'],'binding':bound,'phase':phase,'shadow_result':result}
        issuer=self.authority['issuers'][-1]
        return {'schema_version':'octon.fixture-admission-evidence.v1','fixture_only':True,'issuer_key_digest':issuer['digest'],
                'signed_decision':{'response':answer,'signature':A.sign(self.issuer_private,answer)}}

    def handle(self,envelope,descriptor=None):
        schema=V.load(ROOT/'.octon/runtime/durable-fixture-v2.schema.json')
        if G.CONTRACTS.validate_schema(envelope,{'$ref':'#/$defs/envelope'},root_schema=schema):raise ValueError('unsupported closed currentness envelope schema')
        if set(envelope)!={'request','signature'}:raise ValueError('unsupported keeper envelope')
        request=envelope['request']
        if set(request)!={'schema_version','instance','controller_id','generation','nonce','command','body'} or request['schema_version']!=PROTOCOL or request['instance']!=self.instance:
            raise ValueError('untrusted keeper incarnation/request')
        command=request['command'];body=request['body']
        methods={'enroll':{'expected_generation','pid_namespace','namespace_identity','expected_control_generation','expected_control_digest'},'control':{'bundle','expected_control_generation','expected_control_digest'},'fault':{'kind'},'current':set(),'admit':{'phase'},'confirm':{'kind','relative'},'mock-attempt':{'attempt_ref'}}
        if not isinstance(body,dict) or not isinstance(request['nonce'],str) or not __import__('re').fullmatch('[a-f0-9]{64}',request['nonce']):raise ValueError('malformed narrow request')
        if command in methods and set(body)!=methods[command]:raise ValueError('unsupported closed method body')
        if command=='inspect' and (set(body) not in [set(),{'snapshot_barrier'}] or body and body['snapshot_barrier'] is not True):raise ValueError('unsupported inspection body')
        if command=='prepare' and (body.get('format') not in {'bytes','json'} or set(body)!={'kind','relative','format','delete','data' if body['format']=='bytes' else 'value'}):raise ValueError('unsupported publication body')
        if command in {'enroll','control','fault','inspect'}:
            A.verify(self.public,request,envelope['signature'])
            if command=='enroll':
                if descriptor is None:raise ValueError('actual namespace descriptor required for enrollment')
                return self.enroll(body['expected_generation'],body['pid_namespace'],request,descriptor)
            if command=='control':return self.control(body['bundle'],request)
            if command=='fault':
                with self.fence_lock():
                    self.consume_nonce(request)
                    if body['kind']=='time_unavailable':self.state['time_available']=False
                    elif body['kind']=='new_boot':self.state['boot_id']='unqualified-new-boot'
                    elif body['kind']=='backward_floor':self.state['time_floor']='2999-01-01T00:00:00+00:00'
                    elif body['kind']=='expire':
                        self.state['clock_origin_wall']='2999-01-01T00:00:00+00:00';self.state['time_floor']=self.state['clock_origin_wall']
                    elif body['kind']=='close_namespace':
                        controller=self.authority['controllers'][-1];os.close(self.namespace_fds.pop(controller['id']))
                    else:raise ValueError('unsupported trusted fault')
                    self.save();return {'fault':body['kind']}
            with self.mutex:self.check();self.consume_nonce(request);return copy.deepcopy({'authority':self.authority,'index':self.state,'mock_attempts':self.mock_attempts})
        with self.mutex:
            self.holder(request)
            controller=self.authority['controllers'][-1];A.verify(controller['public_key'],request,envelope['signature'])
            nonce=request['nonce']
            if not isinstance(nonce,str) or len(nonce)!=64 or nonce in self.state['nonces']:raise ValueError('replayed request')
            self.consume_nonce(request)
            if command=='current':
                bundle,result,now=self.evaluation()
                return {'context':self.context,'profile':self.profile,'parent_profile':self.profile['parent_profile'],'bundle':bundle,
                        'generation':self.authority['generation'],'control_generation':self.authority['control_generation'],
                        'storage_identity':self.state['storage_identity'],
                        'control_digest':A.digest(self.authority['bundle']),'issuers':self.authority['issuers'],
                        'clock':{key:self.state[key] for key in ['boot_id','clock_origin_wall','clock_origin_monotonic','time_floor','time_available']},
                        'references':copy.deepcopy(self.state['references']),'result':result,'evaluation_time':now.isoformat()}
            if command=='admit':
                if body['phase'] not in A.PHASES:raise ValueError('unenrolled admission phase')
                return self.observation(body['phase'])
            self.evaluation()
            if command=='mock-attempt':
                expected='MOCK-'+A.digest(A.lineage(self.context['record']))
                relative=f'.octon/agent/transactions/durable/{self.context["record"]["receipt_id"]}/unknown-external.json'
                entry=self.state['references'].get(relative)
                if body['attempt_ref']!=expected or not entry or entry['status']!='confirmed' or self.mock_attempts:raise ValueError('mock attempt identity is already unknown or unprepared')
                self.mock_attempts+=1
                raise ValueError('bounded mock provider response deliberately lost; outcome unknown')
            if command=='prepare':return copy.deepcopy(self.prepare(body['kind'],body['relative'],A.canonical(body['value']) if body['format']=='json' else __import__('base64').b64decode(body['data'],validate=True),body.get('delete',False)))
            if command=='confirm':return copy.deepcopy(self.confirm(body['kind'],body['relative']))
            raise ValueError('unknown narrow keeper method')

    def serve(self):
        keeper=self
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.request.settimeout(10)
                descriptors=[]
                try:
                    _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    if uid!=0:raise ValueError('producer cannot use keeper channel')
                    envelope,descriptors=received_envelope(self.request)
                    expected=1 if envelope.get('request',{}).get('command')=='enroll' else 0
                    if len(descriptors)!=expected:raise ValueError('exactly one enrollment namespace descriptor required; no rights on other methods')
                    result=keeper.handle(envelope,descriptors[0] if descriptors else None)
                    if envelope['request']['command']=='inspect' and envelope['request']['body'].get('snapshot_barrier') is True:
                        durable_json(Path('/tmp/snapshot-ready.json'),{'permission_grant':False})
                        while not Path('/tmp/snapshot-release').exists():time.sleep(.02)
                    answer={'schema_version':PROTOCOL,'instance':keeper.instance,'request_digest':A.digest(envelope['request']),'result':result,'permission_grant':False}
                    self.wfile.write(A.canonical({'answer':answer,'signature':A.sign(keeper.private,answer)}))
                except Exception as error:self.wfile.write(A.canonical({'error':str(error),'permission_grant':False}))
                finally:
                    for descriptor in descriptors:os.close(descriptor)
        class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):daemon_threads=True
        try:
            with Server(str(IPC/'keeper.sock'),Handler) as server:
                os.chmod(IPC/'keeper.sock',0o600)
                print(json.dumps({'schema_version':PROTOCOL,'instance':self.instance,'public_key':self.public,'permission_grant':False}),flush=True)
                server.serve_forever(poll_interval=.05)
        finally:
            for descriptor in self.namespace_fds.values():os.close(descriptor)
            self.namespace_fds.clear()


def exchange(pin,envelope,descriptors=()):
    request=envelope['request']
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(30);connection.connect(str(IPC/'keeper.sock'))
        if descriptors:connection.sendmsg([A.canonical(envelope)],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',descriptors))])
        else:connection.sendall(A.canonical(envelope))
        with connection.makefile('rb') as stream:value=A.strict(stream.readline(A.MAX+1))
    if 'error' in value:raise ValueError(value['error'])
    answer=value['answer'];A.verify(pin['public_key'],answer,value['signature'])
    if answer['instance']!=pin['instance'] or answer['request_digest']!=A.digest(request) or answer['schema_version']!=PROTOCOL:raise ValueError('replayed/stale keeper currentness response')
    return answer['result']


def rpc(pin,private,controller_id,generation,command,body):
    request={'schema_version':PROTOCOL,'instance':pin['instance'],'controller_id':controller_id,'generation':generation,
             'nonce':secrets.token_hex(32),'command':command,'body':body}
    envelope={'request':request,'signature':A.sign(Path(private),request)}
    return exchange(pin,envelope)


def signed_enrollment(pin,body):
    """Narrow trusted-launch signer; the admin key never leaves the keeper."""
    host(True)
    if set(body)!={'expected_generation','pid_namespace','namespace_identity','expected_control_generation','expected_control_digest'}:raise ValueError('only exact enrollment may be signed')
    rpc(pin,CURRENT/'keeper.private.pem','trusted-admin',0,'inspect',{})
    request={'schema_version':PROTOCOL,'instance':pin['instance'],'controller_id':'trusted-admin','generation':0,
             'nonce':secrets.token_hex(32),'command':'enroll','body':body}
    return {'request':request,'signature':A.sign(CURRENT/'keeper.private.pem',request)}


def forward_enrollment(pin,envelope):
    host(False)
    descriptor=os.open('/proc/self/ns/pid',os.O_RDONLY|os.O_CLOEXEC)
    try:
        proof=namespace_proof(descriptor);body=envelope['request']['body']
        if envelope['request']['command']!='enroll' or body['pid_namespace']!=proof['link'] or body['namespace_identity']!=proof['identity']:raise ValueError('signed launch subject does not match this actual intended controller')
        return exchange(pin,envelope,[descriptor])
    finally:os.close(descriptor)


class Executor:
    """The same transaction owner, with durable publication and live currentness."""
    def __init__(self,lease,pin,fault=None,unknown_mock=False):
        host(False);self.lease=copy.deepcopy(lease);self.pin=copy.deepcopy(pin);self.fault=fault;self.unknown_mock=unknown_mock
        if type(lease['generation']) is not int or lease['generation']<1:raise ValueError('unsupported controller generation')
        with Path('/proc/self/ns/pid').open('rb') as handle:proof=namespace_proof(handle.fileno())
        if proof['link']!=lease['pid_namespace'] or proof['identity']!=lease['namespace_identity']:raise ValueError('unenrolled replacement controller namespace')
        self.tx=None;self.observation=None;self.current_value=None;self.effects=[]

    def call(self,command,body={}):
        value=rpc(self.pin,self.lease['key_path'],self.lease['id'],self.lease['generation'],command,body)
        if command=='current' and any([Path(path).stat().st_dev,Path(path).stat().st_ino]!=value['storage_identity'][path] for path in ['/state','/ipc']):raise ValueError('controller durable storage binding changed')
        return value

    def checkpoint(self,name,path=None):
        if self.fault:self.fault(name,path)

    def current(self,root,subject,phase):
        value=self.call('current');self.current_value=value;context=value['context'];plan=context['plan'];record=context['record']
        profile(expected=value['profile']);V.inspect(root);V.admit_work_plan(root,plan);V.admit_recovery_record(root,record)
        bound=A.binding(root,plan,record)
        bound.update({key:context['binding'][key] for key in ['refresh','intent_digest','issuer_ref','delegation_refs','action_digest']})
        if bound!=context['binding'] or subject!=plan and A.lineage(subject)!=A.lineage(record):raise ValueError('exact original durable action/lineage mismatch')
        if self.tx.instruction_fingerprint(root)!=plan['governing_instruction_fingerprint']:raise ValueError('trusted instructions changed')
        mutable={row['path'] for row in record['paths']};expected={row['path']:row for row in plan['evidence_preimages']}
        for relative in set(V.protected_paths(root))|{'AGENTS.md'}:
            if relative not in mutable and self.tx.path_state(root,relative)!=expected.get(relative):raise ValueError('protected verifier/control baseline changed')
        for row in record['paths']:
            allowed=[row['before']] if phase=='prepare' else [row['before'],row['after']]
            if self.tx.path_state(root,row['path']) not in allowed:raise ValueError('changed postimage/expanded footprint')
        for relative,entry in value['references'].items():
            path=confined(root,relative)
            if entry['status']=='confirmed' and entry['kind']!='canonical' and (not path.is_file() or sha(path.read_bytes())!=entry['sha256']):
                raise ValueError('stale/missing durable canonical record')
            if entry['status']=='tombstone' and path.exists():raise ValueError('restored tombstoned record')
        issuer=value['issuers'][-1];self.context=copy.deepcopy(context)
        self.context.update(issuer_public_key=issuer['public_key'],issuer_key_digest=issuer['digest'])
        if subject.get('artifact_kind')=='transaction_receipt':
            groups=[row for row in subject['validation'] if row.get('schema_version')=='octon.fixture-admission-evidence.v1' and row.get('fixture_only') is True]
            if len(groups)!=1 or not groups[0]['decisions']:raise ValueError('missing historical receipt provenance')
            phases={A.validate_evidence(self.context,item,context['binding'])['phase'] for item in groups[0]['decisions']}
            if subject['status']=='applied' and not {'effect','validate'}.issubset(phases):raise ValueError('missing historical admission phases')
        history=root/'.octon/agent/transactions/evidence'/record['receipt_id']
        if history.exists():
            for path in history.glob('*.json'):
                observed=V.load(path);A.validate_observation(observed,record['receipt_id']);A.validate_evidence(self.context,observed['admission_evidence'],context['binding'])
        self.observation=self.call('admit',{'phase':phase})
        A.validate_evidence(self.context,self.observation,context['binding'])
        return self.observation

    def dispatch(self):
        # Transport, schema checks and recording happen BEFORE this final gate.
        value=self.call('current');self.current_value=value
        clock=value['clock'];deadline=min([A.timestamp(value['bundle']['controls']['fresh_until'])]+[A.timestamp(row['valid_until']) for row in value['bundle']['delegations']]+[A.timestamp(row['fresh_until']) for row in value['bundle']['controls']['obligation_results']]+[A.timestamp(row['period_accounting']['end']) for row in value['bundle']['controls']['budget_snapshots']])
        if effective_time(clock)>=deadline:raise ValueError('current durable authority expired at dispatch')

    def kind(self,path):
        relative=path.relative_to(ROOT).as_posix();identity=self.context['record']['receipt_id']
        if relative==f'.octon/agent/transactions/durable/{identity}/consumed.json':return 'consumption'
        for directory,kind in [('pending','journal'),('receipts','receipt'),('recovered','recovery')]:
            if relative==f'.octon/agent/transactions/{directory}/{identity}.json':return kind
        if relative.startswith(f'.octon/agent/transactions/evidence/{identity}/'):return 'observation'
        if relative.startswith(f'.octon/agent/transactions/durable/{identity}/archive/'):return 'archive'
        if relative.startswith(f'.octon/agent/transactions/durable/{identity}/'):return 'history'
        if relative in {row['path'] for row in self.context['record']['paths']}:return 'canonical'
        raise ValueError('publication outside original transaction')

    def prepare(self,path,data,delete=False):
        kind=self.kind(path);relative=path.relative_to(ROOT).as_posix()
        self.call('prepare',{'kind':kind,'relative':relative,'format':'bytes','data':__import__('base64').b64encode(data).decode(),'delete':delete})
        self.checkpoint('prepared',path)
        return kind,relative

    def confirm(self,path,reference):
        self.checkpoint('published-unacknowledged',path)
        self.call('confirm',{'kind':reference[0],'relative':reference[1]})
        if reference[0] in {'journal','receipt','recovery'} and path.is_file():self.archive(path)
        self.checkpoint('confirmed',path)

    def archive(self,path):
        kind=self.kind(path)
        if kind not in {'journal','receipt','recovery'}:return
        data=path.read_bytes();identity=self.context['record']['receipt_id']
        archived=ROOT/'.octon/agent/transactions/durable'/identity/'archive'/(kind+'-'+sha(data)+'.json')
        if archived.exists():
            if archived.read_bytes()!=data:raise ValueError('historical archive bytes changed')
            return
        self.publish_bytes(archived,data)

    def execute(self,command='apply'):
        if command not in {'apply','recover','reconcile','rollback'}:raise ValueError('unsupported durable command')
        import importlib.util
        self.checkpoint('before-lock')
        with (IPC/'fence.lock').open('rb') as fence:
            actual=os.fstat(fence.fileno())
            if [actual.st_dev,actual.st_ino]!=self.lease['fence_identity']:raise ValueError('controller fence binding changed')
            fcntl.flock(fence,fcntl.LOCK_EX)
            try:
                value=self.call('current');context=value['context'];self.context=context
                context_path=Path('/tmp/durable-executor-context.json');durable_json(context_path,context)
                os.environ['OCTON_FIXTURE_ADMISSION_CONTEXT']=str(context_path)
                sys.path[:0]=[str(ROOT/'.octon/runtime'),str(ROOT/'.octon/runtime/scripts')]
                spec=importlib.util.spec_from_file_location('durable_transaction',ROOT/'.octon/runtime/scripts/octon_transaction.py')
                self.tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.tx)
                old_guard=A.guarded;old_evidence=A.validate_evidence
                original_replace=os.replace;original_unlink=Path.unlink;original_rmdir=Path.rmdir;original_mkdir=Path.mkdir;original_json=self.tx.write_new_json
                identity=context['record']['receipt_id'];base='.octon/agent/transactions'
                directories=set(context['record']['created_directories'])|{base+'/'+kind for kind in ['durable','pending','receipts','recovered','evidence']}|{base+'/'+kind+'/'+identity for kind in ['durable','evidence']}|{base+'/durable/'+identity+'/archive'}
                def mkdir(path,*args,**kwargs):
                    if not canonical_path(path):return original_mkdir(path,*args,**kwargs)
                    if path.is_dir() and kwargs.get('exist_ok') is True:return None
                    if path.relative_to(ROOT).as_posix() not in directories:raise ValueError('directory creation footprint expansion')
                    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                    try:self.dispatch();result=original_mkdir(path,*args,**kwargs);sync_directory(path);os.fsync(parent);return result
                    finally:os.close(parent)
                A.guarded=self.current
                def evidence(ctx,item,expected):
                    current=self.current_value or value
                    for issuer in current['issuers']:
                        if issuer['digest']==item['issuer_key_digest']:
                            pinned=copy.deepcopy(ctx);pinned.update(issuer_public_key=issuer['public_key'],issuer_key_digest=issuer['digest'])
                            return old_evidence(pinned,item,expected)
                    raise ValueError('unenrolled historical issuer')
                A.validate_evidence=evidence
                def replace(source,destination,*args,**kwargs):
                    path=Path(destination);live=canonical_path(path)
                    if not live:return original_replace(source,destination,*args,**kwargs)
                    if path.exists() and self.kind(path) in {'journal','receipt','recovery'}:self.archive(path)
                    data=Path(source).read_bytes();reference=self.prepare(path,data)
                    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                    try:
                        self.checkpoint('before-effect',path);self.dispatch();original_replace(source,destination,*args,**kwargs)
                        self.checkpoint('published-before-directory-sync',path)
                        os.fsync(parent);self.effects.append(path.relative_to(ROOT).as_posix());self.checkpoint('after-effect',path)
                        self.confirm(path,reference)
                    finally:os.close(parent)
                def unlink(path,*args,**kwargs):
                    if not canonical_path(path) or not path.exists():return original_unlink(path,*args,**kwargs)
                    if self.kind(path) in {'journal','receipt','recovery'}:self.archive(path)
                    data=path.read_bytes();reference=self.prepare(path,data,True)
                    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                    try:
                        self.checkpoint('before-effect',path);self.dispatch();result=original_unlink(path,*args,**kwargs)
                        self.checkpoint('deleted-before-directory-sync',path)
                        os.fsync(parent);self.checkpoint('after-effect',path);self.confirm(path,reference);return result
                    finally:os.close(parent)
                def rmdir(path,*args,**kwargs):
                    if not canonical_path(path):return original_rmdir(path,*args,**kwargs)
                    # Only the original empty-directory cleanup footprint is accepted.
                    if path.relative_to(ROOT).as_posix() not in directories:
                        raise ValueError('directory footprint expansion')
                    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                    try:self.dispatch();result=original_rmdir(path,*args,**kwargs);os.fsync(parent);return result
                    finally:os.close(parent)
                def publish_bytes(path,data):
                    reference=self.prepare(path,data);make_directories(path.parent)
                    # Private staging is outside the evidence reader's canonical
                    # directory, on the same kernel volume as its publication.
                    staging=Path('/state/staging');make_directories(staging)
                    with tempfile.NamedTemporaryFile(dir=staging,delete=False) as handle:
                        temporary=Path(handle.name)
                        try:
                            handle.write(data);handle.flush();os.fsync(handle.fileno());os.chmod(temporary,0o600)
                            parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                            libc=ctypes.CDLL(None,use_errno=True);rename=libc.renameat2
                            source_bytes=os.fsencode(temporary);target_bytes=os.fsencode(path)
                            self.checkpoint('before-effect',path);self.dispatch()
                            if rename(-100,source_bytes,-100,target_bytes,1):raise OSError(ctypes.get_errno(),'durable exclusive publication refused')
                            self.checkpoint('published-before-directory-sync',path)
                            temporary=None;os.fsync(parent);sync_directory(staging);os.close(parent)
                            self.effects.append(path.relative_to(ROOT).as_posix());self.checkpoint('after-effect',path);self.confirm(path,reference)
                        finally:
                            if temporary is not None:original_unlink(temporary,missing_ok=True)
                self.publish_bytes=publish_bytes
                def new_json(path,item):
                    if not canonical_path(path):return original_json(path,item)
                    return publish_bytes(path,(json.dumps(item,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
                try:
                    consumed=ROOT/'.octon/agent/transactions/durable'/context['record']['receipt_id']/'consumed.json'
                    if command=='apply' and (consumed.exists() or any(row['kind']=='consumption' for row in value['references'].values())):raise ValueError('consumed identity cannot replay')
                    self.current(ROOT,context['plan'],'prepare' if command=='apply' else 'recover')
                    os.replace=replace;Path.unlink=unlink;Path.rmdir=rmdir;Path.mkdir=mkdir;self.tx.write_new_json=new_json
                    consumed=ROOT/'.octon/agent/transactions/durable'/context['record']['receipt_id']/'consumed.json'
                    unknown=ROOT/base/'durable'/identity/'unknown-external.json'
                    if unknown.exists():raise ValueError('unknown mock external outcome; reconciliation required, never replay')
                    if command=='apply':
                        if consumed.exists() or any(row['kind']=='consumption' for row in value['references'].values()):raise ValueError('consumed identity cannot replay')
                        new_json(consumed,{'schema_version':CONSUMPTION,'permission_grant':False,'binding':context['binding'],'lineage':A.lineage(context['record'])})
                        if self.unknown_mock:
                            attempt='MOCK-'+A.digest(A.lineage(context['record']))
                            new_json(unknown,{'schema_version':'octon.mock-external-outcome.v1','permission_grant':False,'receipt_ref':identity,'attempt_ref':attempt,'outcome':'unknown','replay_permitted':False})
                            self.call('mock-attempt',{'attempt_ref':attempt})
                        result=self.tx.apply_plan(ROOT,context['plan'],context['plan']['canonical_plan_digest'])[0]
                    else:
                        # Confirm only original prepared records, never invent missing data.
                        latest=self.call('current')
                        for relative,entry in latest['references'].items():
                            if entry['status']=='prepared':
                                self.call('confirm',{'kind':entry['kind'],'relative':relative})
                                restored=confined(ROOT,relative)
                                if entry['kind'] in {'receipt','journal','recovery'} and restored.is_file():self.archive(restored)
                        pending=ROOT/'.octon/agent/transactions/pending'/(context['record']['receipt_id']+'.json')
                        receipt=ROOT/'.octon/agent/transactions/receipts'/(context['record']['receipt_id']+'.json')
                        if not consumed.exists():raise ValueError('consumption publication missing; uncertainty preserved')
                        if command=='rollback':result=self.tx.rollback(ROOT,receipt)
                        elif pending.exists():result=self.tx.recover_pending(ROOT,pending)
                        elif receipt.exists():
                            result=V.load(receipt);self.current(ROOT,result,'finalize')
                            for row in result['paths']:
                                if self.tx.path_state(ROOT,row['path'])!=row['after' if result['status']=='applied' else 'before']:raise ValueError('receipt postimage changed')
                        else:raise ValueError('consumed identity without original journal/receipt remains unknown')
                    return result
                finally:
                    os.replace=original_replace;Path.unlink=original_unlink;Path.rmdir=original_rmdir;Path.mkdir=original_mkdir;self.tx.write_new_json=original_json
                    A.guarded=old_guard;A.validate_evidence=old_evidence;os.environ.pop('OCTON_FIXTURE_ADMISSION_CONTEXT',None)
                    del sys.path[:2]
            finally:fcntl.flock(fence,fcntl.LOCK_UN)


def launch_worker(mode,argument,output):
    client=Path('/tmp/durable-fixture-worker.py')
    if not client.exists():durable_bytes(client,(HERE/'durable_fixture_worker.py').read_bytes(),exclusive=True,mode=0o444)
    elif client.read_bytes()!=(HERE/'durable_fixture_worker.py').read_bytes() or client.stat().st_uid!=0 or stat.S_IMODE(client.stat().st_mode)!=0o444:raise ValueError('immutable non-secret worker client changed')
    pid=os.fork()
    if pid==0:
        P.drop_worker()
        os.environ['LC_CTYPE']='C.UTF-8'  # explicit clean-exec locale, no inherited environment
        os.execv(sys.executable,[sys.executable,'-I','-B',str(client),mode,str(argument),str(output)])
    return pid


def probe_worker():
    host(True)
    if os.getpid()!=1:raise ValueError('worker qualification requires dedicated PID1')
    import resource
    workspace=Path('/tmp/durable-worker');workspace.mkdir();workspace.chmod(0o755);os.chown(workspace,65534,65534)
    keys=list(Path('/state/controllers').glob('*/controller.private.pem'))
    targets=[AUTH/'issuer-1.private.pem',AUTH/'authority.json',AUTH/'bootstrap.json',CURRENT/'keeper.private.pem',CURRENT/'index.json',*keys,
             ROOT/'.octon/agent/policy.json',ROOT/'.octon/agent/state/focus.json',ROOT/'.octon/runtime/durable_fixture.py',ROOT/'.octon/runtime/fixture_admission.py']
    if not keys or not all(path.is_file() for path in targets):raise ValueError('actual persisted denial targets required')
    hashes={str(path):sha(path.read_bytes()) for path in targets}
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE);desired=70001 if hard==resource.RLIM_INFINITY else min(70001,hard)
    if soft<desired:resource.setrlimit(resource.RLIMIT_NOFILE,(desired,hard))
    after,_=resource.getrlimit(resource.RLIMIT_NOFILE);high=min(70000,after-1)
    descriptor=os.open(AUTH/'issuer-1.private.pem',os.O_RDONLY);os.dup2(descriptor,high);os.close(descriptor)
    argument=Path('/tmp/worker-probe.json');argument.write_text(json.dumps({'targets':[str(p) for p in targets],'owner_pid':os.getpid(),'inherited_fd':high}));argument.chmod(0o644)
    output=workspace/'proof.json';child=launch_worker('probe',argument,output)
    _,status=os.waitpid(child,0);os.close(high)
    if status!=0:raise ValueError('actual worker probe failed')
    result=V.load(output);result['cleanup']=P.kill_workers()
    if any(sha(path.read_bytes())!=hashes[str(path)] for path in targets):raise ValueError('worker changed protected target')
    if not all(result['denials'].values()) or not result['environment_clean'] or any(int(result['privileges'][key],16) for key in ['CapInh','CapPrm','CapEff','CapBnd','CapAmb']) or result['privileges']['Groups'] or result['privileges']['NoNewPrivs']!='1':raise ValueError('worker exclusion qualification failed: '+json.dumps(result))
    result['descriptor_limit']={'soft_before':soft,'soft_after':after,'hard':hard,'inherited_fd':high};result['unchanged_targets']=list(hashes)
    result['mounts']=host(True);return result


def producer_execute(configuration,fault):
    host(False)
    if os.getpid()!=1:raise ValueError('producer fixture requires dedicated controller PID1')
    workspace=Path('/tmp/producer');workspace.mkdir();workspace.chmod(0o755);os.chown(workspace,65534,65534)
    bound=configuration['lease']['context']['binding'];actor=configuration['lease']['context']['actor_ref']
    expected={'schema_version':'octon.durable-fixture-peer.v1','command':'apply','actor_ref':actor,'action_digest':bound['action_digest'],'intent_digest':bound['intent_digest'],'plan_digest':bound['plan_digest']}
    endpoint=Path('/tmp/producer.sock');output=workspace/'proof.json';argument=Path('/tmp/producer-request.json')
    argument.write_text(json.dumps({'socket':str(endpoint),'request':expected}));argument.chmod(0o644)
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(str(endpoint));endpoint.chmod(0o666);server.listen();server.settimeout(60)
        child=launch_worker('request',argument,output);last=None
        for _ in range(7):
            with server.accept()[0] as channel:
                channel.settimeout(60);_,uid,gid=struct.unpack('3i',channel.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                try:
                    with channel.makefile('rb') as stream:request=A.strict(stream.readline(A.MAX+1))
                    if (uid,gid)!=(65534,65534) or request!=expected:raise ValueError('unenrolled peer actor/action/intent/command')
                    last=Executor(configuration['lease'],configuration['pin'],fault).execute('apply');answer={'status':last['status'],'permission_grant':False}
                except Exception as error:answer={'error':str(error),'permission_grant':False}
                channel.sendall(A.canonical(answer))
        _,status=os.waitpid(child,0)
        cleanup=P.kill_workers()
    if status!=0 or last is None:raise ValueError('producer operation failed')
    proof=V.load(output)
    if not all('error' in row for row in proof['responses'][:5]) or proof['responses'][5].get('status')!='applied' or 'consumed identity' not in proof['responses'][6].get('error',''):raise ValueError('peer narrowing/replay failed')
    return {'status':last['status'],'peer':proof,'worker_cleanup':cleanup}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keeper',type=Path)
    parser.add_argument('--inspect-root',type=Path)
    parser.add_argument('--prepare-fixture',action='store_true')
    parser.add_argument('--admin',choices=['enroll','control','fault','inspect'])
    parser.add_argument('--keeper-pin',type=Path)
    parser.add_argument('--sign-enrollment',type=Path)
    parser.add_argument('--forward-enrollment',type=Path)
    parser.add_argument('--body',type=Path)
    parser.add_argument('--execute',type=Path)
    parser.add_argument('--await-launch',type=Path)
    parser.add_argument('--worker-probe',action='store_true')
    parser.add_argument('--command',choices=['apply','recover','reconcile','rollback'],default='apply')
    parser.add_argument('--fault-at')
    args=parser.parse_args()
    if args.inspect_root:print(json.dumps({'profile':profile(args.inspect_root),'permission_grant':False,'execution_authorized':False}))
    elif args.worker_probe:print(json.dumps(probe_worker(),sort_keys=True))
    elif args.prepare_fixture:
        ticket=sys.stdin.readline().strip();print(json.dumps(prepare_fixture(ticket)))
    elif args.keeper:Keeper(V.load(args.keeper),sys.stdin.readline().strip()).serve()
    elif args.sign_enrollment:
        if args.keeper_pin is None:raise ValueError('original trusted keeper pin required')
        print(json.dumps(signed_enrollment(V.load(args.keeper_pin),V.load(args.sign_enrollment)),sort_keys=True))
    elif args.forward_enrollment:
        if args.keeper_pin is None:raise ValueError('original trusted keeper pin required')
        print(json.dumps(forward_enrollment(V.load(args.keeper_pin),V.load(args.forward_enrollment)),sort_keys=True))
    elif args.admin:
        host(True)
        if args.keeper_pin is None:raise ValueError('original retained keeper pin required')
        result=rpc(V.load(args.keeper_pin),CURRENT/'keeper.private.pem','trusted-admin',0,args.admin,V.load(args.body) if args.body else {})
        print(json.dumps(result,sort_keys=True))
    elif args.execute or args.await_launch:
        if args.await_launch:
            host(False)
            if os.getpid()!=1:raise ValueError('trusted launch requires dedicated controller PID1')
            descriptor=os.open('/proc/self/ns/pid',os.O_RDONLY|os.O_CLOEXEC)
            try:proof=namespace_proof(descriptor)
            finally:os.close(descriptor)
            durable_json(Path('/tmp/launch-ready.json'),{'pid_namespace':proof['link'],'namespace_identity':proof['identity'],'permission_grant':False})
            while not args.await_launch.exists():time.sleep(.02)
            args.execute=args.await_launch
            while not Path('/tmp/launch-command.json').exists():time.sleep(.02)
            launch=V.load(Path('/tmp/launch-command.json'));args.command=launch['command'];args.fault_at=launch['fault']
        configuration=V.load(args.execute)
        descriptor=os.open('/proc/self/ns/pid',os.O_RDONLY|os.O_CLOEXEC)
        try:actual=namespace_proof(descriptor)
        finally:os.close(descriptor)
        print(json.dumps({'actual_namespace':actual,'permission_grant':False}),flush=True)
        def fault(name,path):
            if args.fault_at and name+':'+(path.relative_to(ROOT).as_posix() if path else '')==args.fault_at:
                durable_json(Path('/tmp/fault-ready.json'),{'schema_version':PROTOCOL,'permission_grant':False,'fault':args.fault_at})
                while not Path('/tmp/fault-release').exists():time.sleep(.02)
        try:
            result=producer_execute(configuration,fault) if args.await_launch and launch.get('peer') is True else Executor(configuration['lease'],configuration['pin'],fault,unknown_mock=args.fault_at=='mock-unknown').execute(args.command)
            print(json.dumps({'schema_version':PROTOCOL,'permission_grant':False,'status':result['status'],'receipt_digest':A.digest(result),**({'peer':result['peer'],'worker_cleanup':result['worker_cleanup']} if 'peer' in result else {})}))
        except Exception as error:
            print(json.dumps({'error':str(error),'permission_grant':False,'outcome':'reconciliation_required'}));raise SystemExit(2)
    else:raise SystemExit(2)
