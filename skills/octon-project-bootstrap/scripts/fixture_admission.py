#!/usr/bin/env python3
"""Qualification-only admission facet of the standing authorization concern.

No live issuer enrollment or grants. Ed25519 authenticates a cooperative fixture
issuer and actor; same-UID processes are NOT a malicious-worker boundary.
"""
from __future__ import annotations
import base64
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import time

SCHEMA = 'octon.fixture-admission.v1'
CONTEXT = 'octon.fixture-admission-context.v1'
MAX = 1024 * 1024
PHASES = {'prepare','effect','validate','finalize','recover','rollback'}


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def openssl():
    candidates = [shutil.which('openssl')]
    if sys.platform == 'darwin':
        candidates += ['/opt/homebrew/opt/openssl@3/bin/openssl','/usr/local/opt/openssl@3/bin/openssl']
    if os.name == 'nt':
        candidates += [str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/usr/bin/openssl.exe')]
    for path in candidates:
        if path and Path(path).is_file():
            # Never substitute an algorithm or a different dependency.
            result=subprocess.run([path,'list','-public-key-methods'],capture_output=True,check=False)
            if result.returncode == 0 and b'ED25519' in result.stdout.upper():
                return path
    raise ValueError('required OpenSSL Ed25519 dependency unavailable')


def command(argv):
    result=subprocess.run([openssl(),*map(str,argv)],capture_output=True,check=False,shell=False)
    if result.returncode:
        raise ValueError('OpenSSL Ed25519 operation refused')
    return result.stdout


def keypair(area,name):
    private=area/(name+'.private.pem'); public=area/(name+'.public.pem')
    command(['genpkey','-algorithm','ED25519','-out',private])
    private.chmod(0o600)
    command(['pkey','-in',private,'-pubout','-out',public])
    return private,public.read_text()


def sign(private,value):
    with tempfile.TemporaryDirectory(prefix='octon-sign-data-') as temporary:
        area=Path(temporary); data=area/'data'; signature=area/'signature'
        data.write_bytes(canonical(value))
        command(['pkeyutl','-sign','-rawin','-inkey',private,'-in',data,'-out',signature])
        return base64.b64encode(signature.read_bytes()).decode()


def verify(public,value,signature):
    with tempfile.TemporaryDirectory(prefix='octon-verify-data-') as temporary:
        area=Path(temporary); key=area/'public'; data=area/'data'; sig=area/'signature'
        key.write_text(public); data.write_bytes(canonical(value))
        sig.write_bytes(base64.b64decode(signature,validate=True))
        command(['pkeyutl','-verify','-rawin','-pubin','-inkey',key,'-in',data,'-sigfile',sig])


def strict(raw):
    from installation_runtime import pairs
    if len(raw)>MAX:
        raise ValueError('fixture message exceeds bound')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def lineage(record):
    return {key:record[key] for key in ('receipt_id','operation','plan_digest','paths','created_directories')}


def binding(root,plan,record):
    from installation_runtime import digest as bytes_digest
    return {'root':str(root.resolve()),'source_revision':strict((root/'.octon/manifest.json').read_bytes())['source_revision'],
            'installation_digest':bytes_digest((root/'.octon/manifest.json').read_bytes()),
            'plan_digest':plan['canonical_plan_digest'],'plan_bytes_digest':digest(plan),
            'operation':plan['operation'],'work_ref':'TASK-0001','work_digest':bytes_digest((root/'.octon/agent/tasks/TASK-0001.md').read_bytes()),'expected_state_digest':digest(plan['targets']),'policy_digest':bytes_digest((root/'.octon/agent/policy.json').read_bytes()),'lineage_digest':digest(lineage(record))}


def current_time():
    return datetime.now(timezone.utc)

def timestamp(value):
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    if stamp.tzinfo is None:raise ValueError('fixture decision timestamp requires timezone')
    return stamp.astimezone(timezone.utc)


def server(pipe,initial,actor_public,shadow_root):
    """Independent controller process; private issuer key never leaves its scope."""
    import governance_shadow as shadow
    bundle=copy.deepcopy(initial['bundle']); bound=initial['binding']; nonces=set()
    action=bundle['action']
    for key,target in [('plan_digest','plan_digest'),('operation','operation'),('work_ref','work_ref'),('work_contract_digest','work_digest'),('expected_state_digest','expected_state_digest'),('policy_digest','policy_digest')]:
        if action[key]!=bound[target]: raise ValueError('fixture action does not bind actual operation')
    with tempfile.TemporaryDirectory(prefix='octon-ephemeral-issuer-') as temporary:
        private,public=keypair(Path(temporary),'issuer')
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.request.settimeout(2)
                try:
                    envelope=strict(self.rfile.readline(MAX+1)); request=envelope['request']
                    if set(envelope)!={'request','signature'} or set(request)!={'schema_version','nonce','actor_ref','phase','binding'}:
                        raise ValueError('unsupported request fields')
                    verify(actor_public,request,envelope['signature'])
                    if request['schema_version'] != SCHEMA or request['actor_ref'] != bundle['action']['actor_ref'] or request['binding'] != bound:
                        raise ValueError('actor or action binding mismatch')
                    if request['phase'] not in PHASES or request['phase'] not in initial['allowed_phases']:
                        raise ValueError('phase outside fixture authority')
                    nonce=request['nonce']
                    if not isinstance(nonce,str) or len(nonce)!=64 or nonce in nonces:
                        raise ValueError('invalid or replayed nonce')
                    nonces.add(nonce)
                    current=copy.deepcopy(bundle)
                    current['evaluation_time']=current_time().isoformat()
                    action=current['action']
                    for key,target in [('plan_digest','plan_digest'),('operation','operation'),('work_ref','work_ref'),('work_contract_digest','work_digest'),('expected_state_digest','expected_state_digest'),('policy_digest','policy_digest')]:
                        if action[key]!=bound[target]: raise ValueError('current action binding mismatch')
                    if action['digest']!=bound['action_digest']:raise ValueError('current full action binding mismatch')
                    if current['intent']['digest']!=bound['intent_digest'] or current['intent']['principal_ref']!=bound['issuer_ref'] or [shadow.delegation_reference(row) for row in current['delegations']]!=bound['delegation_refs']:
                        raise ValueError('current governing intent or issuer mismatch')
                    result=shadow.evaluate(current,root=Path(shadow_root))
                    # Shadow remains non-authorizing. Direct bounded fixture invocation
                    # plus authenticated current observations permits this fixture only.
                    admitted=result['coverage']=='covered'
                    expires=min([current_time()+timedelta(seconds=10),timestamp(current['controls']['fresh_until'])]+[timestamp(row['valid_until']) for row in current['delegations']]+[timestamp(row['fresh_until']) for row in current['controls']['obligation_results']]+[timestamp(row['period_accounting']['end']) for row in current['controls']['budget_snapshots']])
                    response={'schema_version':SCHEMA,'request_digest':digest(request),'nonce':nonce,
                              'fixture_only':True,'live_authorization':False,'permission_grant':False,
                              'admitted':admitted,'expires_at':expires.isoformat(),'coverage':result['coverage'],'controls_digest':current['controls']['digest'],
                              'issuer_ref':current['intent']['principal_ref'],'actor_ref':request['actor_ref'],
                              'binding':bound,'phase':request['phase'],'shadow_result':result}
                    self.wfile.write(canonical({'response':response,'signature':sign(private,response)}))
                except Exception:
                    self.wfile.write(canonical({'error':'fixture admission refused'}))
        with socketserver.TCPServer(('127.0.0.1',0),Handler) as listener:
            listener.timeout=.05
            pipe.send({'port':listener.server_address[1],'public_key':public})
            while True:
                if pipe.poll():
                    update=pipe.recv()
                    if update is None: break
                    bundle=copy.deepcopy(update); pipe.send(True)
                listener.handle_request()


def validate_evidence(context,evidence,expected):
    fields={'schema_version','fixture_only','issuer_key_digest','signed_decision'}
    if set(evidence)!=fields or evidence['schema_version']!='octon.fixture-admission-evidence.v1' or evidence['fixture_only'] is not True or evidence['issuer_key_digest']!=context['issuer_key_digest']:
        raise ValueError('unsupported fixture admission evidence')
    answer=evidence['signed_decision']
    if set(answer)!={'response','signature'}:raise ValueError('unsupported signed evidence fields')
    response=answer['response']
    fields={'schema_version','request_digest','nonce','fixture_only','live_authorization','permission_grant','admitted','expires_at','coverage','controls_digest','issuer_ref','actor_ref','binding','phase','shadow_result'}
    if set(response)!=fields or response['schema_version']!=SCHEMA or response['binding']!=expected or response['phase'] not in PHASES or response['issuer_ref']!=expected['issuer_ref'] or response['actor_ref']!=context['actor_ref'] or response['admitted'] is not True or response['coverage']!='covered' or response['fixture_only'] is not True or response['live_authorization'] is not False or response['permission_grant'] is not False:
        raise ValueError('historical signed observation is not admitted fixture authority')
    request={'schema_version':SCHEMA,'nonce':response['nonce'],'actor_ref':response['actor_ref'],'phase':response['phase'],'binding':expected}
    shadow=response['shadow_result']
    if response['request_digest']!=digest(request) or shadow['schema_version']!='octon.governance-shadow-result.v2' or shadow['action_digest']!=expected['action_digest'] or shadow['coverage']!='covered' or shadow['execution_authorized'] is not False or shadow['permission_grant'] is not False or shadow['reservations_created'] is not False or response['controls_digest']!=shadow['control_snapshot_digest']:
        raise ValueError('historical fixture observation binding mismatch')
    verify(context['issuer_public_key'],response,answer['signature'])
    return response


def validate_observation(value, expected_receipt=None):
    fields={'schema_version','permission_grant','receipt_ref','lineage_digest','phase','admission_evidence'}
    if not isinstance(value,dict) or set(value)!=fields or value['schema_version']!='octon.fixture-transaction-authority-observation.v1' or value['permission_grant'] is not False or value['phase'] not in PHASES:
        raise ValueError('unsupported transaction authority observation')
    import re
    if not re.fullmatch(r'RCPT-[a-f0-9]{24}',value['receipt_ref']) or not re.fullmatch(r'[a-f0-9]{64}',value['lineage_digest']):raise ValueError('invalid observation subject')
    if expected_receipt is not None and value['receipt_ref']!=expected_receipt:raise ValueError('observation receipt mismatch')
    evidence=value['admission_evidence'];response=evidence['signed_decision']['response']
    if response['phase']!=value['phase'] or response['binding']['lineage_digest']!=value['lineage_digest'] or evidence['schema_version']!='octon.fixture-admission-evidence.v1' or evidence['fixture_only'] is not True or response['admitted'] is not True or response['permission_grant'] is not False or response['live_authorization'] is not False:raise ValueError('observation is not an admitted fixture decision')
    return value


def guarded(root,subject,phase):
    """Read current controller state with fresh actor proof at every boundary."""
    from installation_runtime_v2 import load, inspect, protected_paths, confined
    inspect(root)
    path=os.environ.get('OCTON_FIXTURE_ADMISSION_CONTEXT')
    if not path:
        raise ValueError('explicit bounded fixture admission context required')
    context=load(Path(path))
    fields={'schema_version','fixture_authority','root','issuer_public_key','issuer_key_digest','actor_ref','actor_private_key','port','plan','record','binding','refresh'}
    if set(context)!=fields or context['schema_version']!=CONTEXT or context['fixture_authority']!='current-user-disposable-admission-only':
        raise ValueError('unsupported fixture admission context')
    if str(root.resolve()) != context['root'] or Path(path).resolve().is_relative_to(root.resolve()):
        raise ValueError('fixture anchor must be outside exact disposable target')
    if hashlib.sha256(context['issuer_public_key'].encode()).hexdigest()!=context['issuer_key_digest']:
        raise ValueError('fixture issuer anchor mismatch')
    plan=context['plan']; record=context['record']
    expected=binding(root,plan,record)
    expected['refresh']=context['refresh']
    expected['intent_digest']=context['binding']['intent_digest']
    expected['issuer_ref']=context['binding']['issuer_ref']
    expected['delegation_refs']=context['binding']['delegation_refs']
    expected['action_digest']=context['binding']['action_digest']
    if plan['operation'] != 'work.handoff': raise ValueError('admission fixture supports one existing-task handoff only')
    if expected!=context['binding']:
        raise ValueError('installation/source/plan binding changed')
    if phase=='prepare':
        if subject != plan:
            raise ValueError('exact authenticated plan required')
        if any((root/'.octon/agent/transactions'/kind/(record['receipt_id']+'.json')).exists() for kind in ['receipts','recovered']):
            raise ValueError('original transaction identity already has terminal history')
    elif 'paths' in subject:
        if lineage(subject)!=lineage(record):
            raise ValueError('forged recovery or receipt lineage')
        if subject.get('artifact_kind')=='transaction_receipt':
            evidence=[row for row in subject['validation'] if row.get('schema_version')=='octon.fixture-admission-evidence.v1' and row.get('fixture_only') is True]
            if len(evidence)!=1 or not evidence[0]['decisions']:raise ValueError('receipt has no authenticated fixture provenance')
            phases=set()
            for item in evidence[0]['decisions']:
                phases.add(validate_evidence(context,item,expected)['phase'])
            if not {'effect','validate'}.issubset(phases):raise ValueError('applied receipt lacks effect and validation admission provenance')
    else:
        if subject != plan:
            raise ValueError('exact effect plan required')
    from installation_runtime import admit_work_plan, admit_recovery_record
    admit_work_plan(root,plan); admit_recovery_record(root,record)
    # Check exact control/verifier/acceptance baseline, including instructions.
    mutable={item['path'] for item in record['paths']}
    expected_states={item['path']:item for item in plan['evidence_preimages']}
    import stat
    def state(relative):
        path=confined(root,relative)
        if not path.exists(): return {'path':relative,'type':'absent','mode':None,'sha256':None}
        return {'path':relative,'type':'file','mode':stat.S_IMODE(path.stat().st_mode),
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    for relative in set(protected_paths(root)) | {'AGENTS.md'}:
        if relative not in mutable and state(relative)!=expected_states.get(relative):
            raise ValueError('current control/verifier baseline mismatch')
    for item in record['paths']:
        current=state(item['path'])
        allowed=[item['before']] if phase=='prepare' else [item['before'],item['after']]
        if current not in allowed:
            raise ValueError('expected state changed outside exact transaction: '+item['path'])
    history=root/'.octon/agent/transactions/evidence'/record['receipt_id']
    if history.exists():
        for observation_path in history.glob('*.json'):
            observation=load(observation_path);validate_observation(observation,record['receipt_id'])
            validate_evidence(context,observation['admission_evidence'],expected)
    request={'schema_version':SCHEMA,'nonce':secrets.token_hex(32),'actor_ref':context['actor_ref'],
             'phase':phase,'binding':expected}
    envelope={'request':request,'signature':sign(Path(context['actor_private_key']),request)}
    with socket.create_connection(('127.0.0.1',context['port']),timeout=10) as connection:
        connection.sendall(canonical(envelope))
        with connection.makefile('rb') as stream:
            answer=strict(stream.readline(MAX+1))
    if set(answer)!={'response','signature'}:
        raise ValueError('authenticated controller refused fixture admission')
    response=answer['response']; verify(context['issuer_public_key'],response,answer['signature'])
    if response['schema_version']!=SCHEMA or response['request_digest']!=digest(request) or response['nonce']!=request['nonce'] or response['binding']!=expected or response['phase']!=phase or response['actor_ref']!=context['actor_ref'] or response['fixture_only'] is not True or response['live_authorization'] is not False or response['permission_grant'] is not False or response['admitted'] is not True:
        raise ValueError('current fixture admission uncovered or indeterminate')
    if not timestamp(response['shadow_result']['evaluation_time']) <= current_time() < timestamp(response['expires_at']):
        raise ValueError('fixture admission decision expired or future')
    evidence={'schema_version':'octon.fixture-admission-evidence.v1','fixture_only':True,'issuer_key_digest':context['issuer_key_digest'],'signed_decision':answer}
    validate_evidence(context,evidence,expected)
    return evidence

if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    # Fixture controller transport only; no ordinary dispatcher route or live issuer.
    if len(sys.argv)!=3 or sys.argv[1]!='--fixture-controller':
        raise SystemExit(2)
    import queue
    import threading
    updates=queue.Queue()
    def read_updates():
        for line in sys.stdin.buffer:
            updates.put(strict(line))
        updates.put(None)
    threading.Thread(target=read_updates,daemon=True).start()
    class Pipe:
        def poll(self): return not updates.empty()
        def recv(self): return updates.get()
        def send(self,value): print(json.dumps(value),flush=True)
    config=strict(Path(sys.argv[2]).read_bytes())
    sys.path.insert(0,str(Path(__file__).resolve().parent/'authority/scripts'))
    server(Pipe(),config['initial'],config['actor_public'],str(Path(__file__).resolve().parent/'authority'))
