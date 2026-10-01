#!/usr/bin/env python3
"""Linux-only protected disposable facet of existing admission/transaction owners.

The trusted fixture authority enrolls a worker and controller. Worker proposals
are never execution code. This source-only module has no ordinary target route.
"""
from __future__ import annotations
import copy
import ctypes
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import struct
import sys
import tempfile
import time
from contextlib import contextmanager

sys.path.insert(0,str(Path(__file__).resolve().parent/'authority/scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import fixture_admission as A
import governance_shadow as G
import installation_runtime_v2 as V

PROFILE = 'octon.protected-fixture-profile.v1'
REQUEST = 'octon.protected-fixture-request.v2'
EVENT = 'octon.protected-fixture-effect.v2'
WORKER_UID = 65534


def install(root):
    """Explicit fresh fixture overlay; never ordinary generation or live adoption."""
    root=Path(root)
    manifest=V.inspect(root)
    source_root=Path(__file__).resolve().parents[3]
    inventory_path=source_root/'shared/source-contracts/protected-fixture-inventory.json'
    inventory=V.load(inventory_path)
    expected={'schema_version':'octon.source.protected-fixture-inventory.v1','status':'source_only_disposable_qualification',
              'permission_grant':False,'profile_schema':PROFILE,'parent_installation_schema':V.ADMISSION_SCHEMA,
              'host_profile':'linux-disposable-container-distinct-uid-v1','request_schema':REQUEST,'effect_schema':EVENT,
              'required_dependencies':['python>=3.11','canonical-minimal-core','openssl-ed25519','linux-flock-renameat2-distinct-uid'],
              'assets':[{'source':'skills/octon-project-bootstrap/scripts/protected_fixture.py','target':'.octon/runtime/protected_fixture.py'},
                        {'source':'shared/source-contracts/protected-fixture-v1.schema.json','target':'.octon/runtime/protected-fixture-v1.schema.json'}]}
    if inventory!=expected:raise ValueError('unsupported canonical protected fixture inventory')
    destination=root/'.octon/runtime/protected_fixture.py'
    if destination.exists() or (root/'.octon/protected-profile.json').exists():
        raise ValueError('protected profile already exists; no in-place upgrade')
    for row in inventory['assets']:(root/row['target']).write_bytes((source_root/row['source']).read_bytes())
    value={'schema_version':PROFILE,'permission_grant':False,'status':'disposable_qualification_only',
           'host_profile':'linux-disposable-container-distinct-uid-v1',
           'parent_installation_schema':V.ADMISSION_SCHEMA,
           'source_revision':manifest['source_revision'],
           'installation_digest':hashlib.sha256((root/'.octon/manifest.json').read_bytes()).hexdigest(),
           'asset':'.octon/runtime/protected_fixture.py',
           'asset_digest':hashlib.sha256(destination.read_bytes()).hexdigest(),
           'inventory_digest':hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
           'source_inputs':[{'path':path.relative_to(source_root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                            for path in [inventory_path,*[source_root/row['source'] for row in inventory['assets']]]],
           'assets':[{'path':row['target'],'sha256':hashlib.sha256((root/row['target']).read_bytes()).hexdigest()} for row in inventory['assets']]}
    put(root/'.octon/protected-profile.json',value,exclusive=True)
    return value


def inspect_profile(root, expected):
    root=Path(root);value=V.load(root/'.octon/protected-profile.json')
    if value!=expected or set(value)!={'schema_version','permission_grant','status','host_profile','parent_installation_schema','source_revision','installation_digest','asset','asset_digest','inventory_digest','source_inputs','assets'}:
        raise ValueError('unsupported/mixed protected profile')
    if value['schema_version']!=PROFILE or value['permission_grant'] is not False or value['status']!='disposable_qualification_only' or value['host_profile']!='linux-disposable-container-distinct-uid-v1' or value['parent_installation_schema']!=V.ADMISSION_SCHEMA or value['asset']!='.octon/runtime/protected_fixture.py':
        raise ValueError('unsupported protected profile version')
    if value['installation_digest']!=hashlib.sha256((root/'.octon/manifest.json').read_bytes()).hexdigest() or value['asset_digest']!=hashlib.sha256(V.confined(root,value['asset']).read_bytes()).hexdigest():
        raise ValueError('protected installation/baseline mismatch')
    schema=V.load(root/'.octon/runtime/protected-fixture-v1.schema.json')
    if G.CONTRACTS.validate_schema(value,{'$ref':'#/$defs/profile'},root_schema=schema):raise ValueError('protected profile schema mismatch')
    for row in value['assets']:
        if row['sha256']!=hashlib.sha256(V.confined(root,row['path']).read_bytes()).hexdigest():raise ValueError('protected asset dependency missing or changed')
    return value


def linux_owner():
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('protected fixture requires a disposable Linux root owner')
    if os.environ.get('OCTON_OWNED_EPHEMERAL_CONTAINER')!='protected-fixture-v1' or not Path('/.dockerenv').is_file():
        raise ValueError('explicit owned ephemeral container marker required')
    mounts=[line.split(' - ',1) for line in Path('/proc/self/mountinfo').read_text().splitlines()]
    if not any(left.split()[4]=='/tmp' and right.split()[0]=='tmpfs' for left,right in mounts):
        raise ValueError('protected fixture requires kernel tmpfs custody; host-bind DAC unqualified')
    # A worker cannot read trusted executor memory even on permissive proc mounts.
    if ctypes.CDLL(None, use_errno=True).prctl(4, 0, 0, 0, 0):
        raise ValueError('cannot protect trusted process memory')
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0):
        raise ValueError('cannot adopt owned worker orphans')
    capabilities=next(line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:'))
    if not int(capabilities,16)&(1<<5):raise ValueError('trusted fixture needs scoped CAP_KILL for worker cleanup')


def drop_worker():
    """Called only in a child of an explicitly owned ephemeral environment."""
    libc = ctypes.CDLL(None, use_errno=True)
    os.setsid()  # also deny the POSIX same-session SIGCONT exception
    os.setgroups([])
    for capability in range(64):
        result = libc.prctl(24, capability, 0, 0, 0)  # PR_CAPBSET_DROP
        if result and ctypes.get_errno() != 22:
            raise ValueError('cannot drop worker capability bounding set')
    os.setgid(WORKER_UID)
    os.setuid(WORKER_UID)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(4, 0, 0, 0, 0):
        raise ValueError('cannot constrain worker process')
    # No issuer/control descriptors or producer-selected import environment.
    os.environ.clear()
    os.environ.update(PATH='/usr/local/bin:/usr/bin:/bin', PYTHONDONTWRITEBYTECODE='1')
    for descriptor in [int(name) for name in os.listdir('/proc/self/fd') if name.isdigit() and int(name)>2]:
        try:os.close(descriptor)
        except OSError:pass
    null=os.open('/dev/null',os.O_RDWR)
    try:
        for descriptor in [0,1,2]:os.dup2(null,descriptor)
    finally:
        if null>2:os.close(null)


def kernel_custody(path, *, private=False):
    path=Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(Path('/tmp')):
        raise ValueError('authority/canonical custody must stay on the owned kernel /tmp tmpfs')
    cursor=Path('/tmp')
    for part in path.relative_to('/tmp').parts:
        cursor=cursor/part
        if cursor.is_symlink():raise ValueError('custody symlink unsupported')
    if private and (not path.is_dir() or path.stat().st_uid!=0 or stat.S_IMODE(path.stat().st_mode)!=0o700):
        raise ValueError('private root-owned custody required')
    return path


def worker_processes():
    """This PID namespace is dedicated to one disposable qualification owner."""
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            lines=(path/'status').read_text().splitlines()
            uid=next(line for line in lines if line.startswith('Uid:')).split()[1:]
            if str(WORKER_UID) in uid:result.append(int(path.name))
        except (OSError,StopIteration):pass
    return result


def kill_workers():
    if os.getpid()!=1:raise ValueError('namespace-wide cleanup requires the dedicated PID1 fixture supervisor')
    linux_owner()
    deadline=time.monotonic()+5
    killed=set()
    while True:
        remaining=worker_processes()
        if not remaining:return {'killed':sorted(killed),'remaining':[],'orphan_reaping':True}
        for pid in remaining:
            try:os.kill(pid,9);killed.add(pid)
            except ProcessLookupError:continue
            # Linux subreaper/PID1 owns children adopted after parent exit.
            try:os.waitpid(pid,os.WNOHANG)
            except ChildProcessError:pass
        if time.monotonic()>=deadline:raise ValueError('owned worker descendants remain; evidence export refused')
        time.sleep(.01)


def trusted_time(state, *, wall=None, monotonic=None):
    wall=wall or datetime.now(timezone.utc)
    monotonic=time.monotonic() if monotonic is None else monotonic
    elapsed=monotonic-state['clock_origin_monotonic']
    if elapsed<0:raise ValueError('trusted monotonic clock continuity lost')
    effective=max(wall,A.timestamp(state['clock_origin_wall'])+A.timedelta(seconds=elapsed))
    if effective<A.timestamp(state['time_floor']):
        raise ValueError('trusted time moved backwards; recovery disabled')
    return effective


def put(path, value, *, exclusive=False):
    data=A.canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        fd=os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    else:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary=Path(handle.name)
            try:
                handle.write(data); handle.flush(); os.fsync(handle.fileno())
                os.chmod(temporary, 0o600); os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
    descriptor=os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


class Authority:
    """Retained authority anchor; controller snapshots are non-authorizing copies."""
    def __init__(self, area):
        linux_owner()
        self.area=kernel_custody(area,private=True)
        self.anchor=self.area/'anchor.json'
        if self.area.is_symlink() or not self.anchor.is_file():
            raise ValueError('retained authority anchor missing; no snapshot enrollment')

    @classmethod
    def enroll(cls, area, context, bundle, *, allowed_commands=('apply','recover','rollback','reconcile')):
        linux_owner()
        if os.getpid()!=1:raise ValueError('enrollment requires the dedicated fixture supervisor')
        area=Path(area)
        kernel_custody(area)
        kernel_custody(context['root'],private=True)
        if area.exists(): raise ValueError('trusted enrollment requires a fresh fixture area')
        area.mkdir(mode=0o700)
        put(area/'fence.lock',{},exclusive=True)
        lock_state=(area/'fence.lock').stat()
        private, public=A.keypair(area, 'issuer-1')
        state={'schema_version':PROFILE, 'permission_grant':False,
               'fixture_only':True, 'context':copy.deepcopy(context),
               'bundle':copy.deepcopy(bundle), 'control_digest':A.digest(bundle),
               'profile':V.load(Path(context['root'])/'.octon/protected-profile.json'),
               'generation':1, 'control_generation':1,
               'allowed_commands':list(allowed_commands),
               'lock_identity':[lock_state.st_dev,lock_state.st_ino],
               'transaction_history':{},
               'terminal_records':{},
               'issuers':[{'public_key':public, 'digest':hashlib.sha256(public.encode()).hexdigest(),
                           'private':str(private), 'generation':1}],
               'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
               'pid_namespace':os.readlink('/proc/self/ns/pid'),
               'time_floor':datetime.now(timezone.utc).isoformat(),
               'clock_origin_wall':datetime.now(timezone.utc).isoformat(),
               'clock_origin_monotonic':time.monotonic()}
        state['context'].update(issuer_public_key=public, issuer_key_digest=state['issuers'][0]['digest'])
        put(area/'anchor.json',state,exclusive=True)
        put(area/'supervisor-tip.json',{'anchor_digest':A.digest(state)},exclusive=True)
        return cls(area)

    @contextmanager
    def lock(self):
        # The lock inode lives with the retained anchor, never in worker snapshots.
        with (self.area/'fence.lock').open('r+b') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                identity=os.fstat(handle.fileno())
                if [identity.st_dev,identity.st_ino]!=self.load()['lock_identity']:
                    raise ValueError('split fencing lock domain')
                yield
            finally: fcntl.flock(handle, fcntl.LOCK_UN)

    def load(self):
        state=V.load(self.anchor)
        fields={'schema_version','permission_grant','fixture_only','context','bundle','control_digest','profile','generation','control_generation','allowed_commands','lock_identity','transaction_history','terminal_records','issuers','boot_id','pid_namespace','time_floor','clock_origin_wall','clock_origin_monotonic'}
        if set(state)!=fields or type(state['generation']) is not int or state['generation']<1 or type(state['control_generation']) is not int or state['control_generation']<1 or not isinstance(state['allowed_commands'],list) or len(set(state['allowed_commands']))!=len(state['allowed_commands']) or not set(state['allowed_commands']).issubset({'apply','recover','rollback','reconcile'}):
            raise ValueError('unsupported closed retained authority state')
        if state.get('schema_version')!=PROFILE or state.get('permission_grant') is not False or state.get('fixture_only') is not True:
            raise ValueError('unsupported retained authority anchor')
        if A.digest(state['bundle'])!=state['control_digest']:
            raise ValueError('restored or altered control snapshot')
        if V.load(self.area/'supervisor-tip.json')!={'anchor_digest':A.digest(state)}:
            raise ValueError('snapshot differs from retained supervisor high-water')
        lock_state=(self.area/'fence.lock').stat()
        if [lock_state.st_dev,lock_state.st_ino]!=state['lock_identity']:
            raise ValueError('retained fencing lock replaced')
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=state['boot_id']:
            raise ValueError('host restart/power-loss anchor continuity unqualified')
        if os.readlink('/proc/self/ns/pid')!=state['pid_namespace']:
            raise ValueError('fixture PID namespace ownership changed')
        return state

    def save(self,state):
        # A crash between the two writes is indeterminate and fails closed.
        # Controller snapshots exclude the independently retained supervisor tip.
        put(self.anchor,state)
        put(self.area/'supervisor-tip.json',{'anchor_digest':A.digest(state)})

    def snapshot(self):
        with self.lock():
            value=self.load()
            return {key:copy.deepcopy(value[key]) for key in ['generation','control_generation','control_digest']}

    def replace_controller(self, expected):
        if os.getpid()!=1:raise ValueError('replacement enrollment requires trusted fixture supervisor')
        with self.lock():
            state=self.load()
            if expected != {key:state[key] for key in expected} or set(expected)!={'generation','control_generation','control_digest'}:
                raise ValueError('stale controller enrollment snapshot')
            state['generation']+=1
            private,public=A.keypair(self.area,'issuer-'+str(state['generation']))
            # Key generation alone does not enroll: only this trusted CAS path.
            issuer={'public_key':public,'digest':hashlib.sha256(public.encode()).hexdigest(),
                    'private':str(private),'generation':state['generation']}
            state['issuers'].append(issuer)
            state['context'].update(issuer_public_key=public,issuer_key_digest=issuer['digest'])
            self.save(state)
            return state['generation']

    def control(self, expected, bundle):
        """Trusted supervisor path; never callable from the worker socket."""
        with self.lock():
            state=self.load()
            if expected != {key:state[key] for key in expected} or set(expected)!={'generation','control_generation','control_digest'}:
                raise ValueError('stale control update')
            # A control update cannot renew/replace intent, action or delegation.
            if any(bundle[key]!=state['bundle'][key] for key in ['intent','work_binding','delegations','action']):
                raise ValueError('control path cannot expand or renew fixture authority')
            old=state['bundle']['controls']; new=bundle['controls']
            if not set(old['revoked_delegation_ids']).issubset(new['revoked_delegation_ids']) or (old['emergency_stop'] and not new['emergency_stop']) or new['authority_epoch']<old['authority_epoch']:
                raise ValueError('control restoration would resurrect authority')
            state.update(bundle=copy.deepcopy(bundle),control_digest=A.digest(bundle),control_generation=state['control_generation']+1)
            self.save(state)


class Executor:
    """Trusted facet around the existing canonical transaction owner, one action."""
    def __init__(self, authority, generation, fault=None):
        if type(generation) is not int or generation<1:raise ValueError('unsupported controller generation')
        self.authority=authority; self.generation=generation
        self.fault=fault  # trusted qualification barriers only, no worker field
        self.state=None; self.tx=None; self.effects=[]

    def checkpoint(self, name, path=None):
        if self.fault: self.fault(name,path)

    def evaluate(self):
        state=self.authority.load()
        if state['generation']!=self.generation:
            raise ValueError('stale controller fencing generation')
        now=trusted_time(state)
        state['time_floor']=now.isoformat(); self.authority.save(state)
        current=copy.deepcopy(state['bundle']);current['evaluation_time']=now.isoformat()
        source_root=Path(G.__file__).resolve().parents[3]
        copied_root=Path(__file__).resolve().parent/'authority'
        result=G.evaluate(current,root=copied_root if copied_root.is_dir() else source_root)
        if result['coverage']!='covered':
            raise ValueError('current protected fixture authority '+result['coverage'])
        self.state=state
        # Half-open grant/obligation/accounting freshness at effect dispatch.
        # This final check follows evaluator/storage work. The caller immediately
        # invokes the primitive; arbitrary host suspension is not a real-time guarantee.
        deadline=min([A.timestamp(current['controls']['fresh_until'])]+[A.timestamp(row['valid_until']) for row in current['delegations']]+[A.timestamp(row['fresh_until']) for row in current['controls']['obligation_results']]+[A.timestamp(row['period_accounting']['end']) for row in current['controls']['budget_snapshots']])
        if trusted_time(state)>=deadline:raise ValueError('fixture authority expired at effect dispatch')
        return current,result,now

    def current(self, root, subject, phase):
        context=self.state['context']; plan=context['plan']; record=context['record']
        inspect_profile(root,self.state['profile'])
        V.inspect(root)
        expected=A.binding(root,plan,record)
        expected.update({key:context['binding'][key] for key in ['refresh','intent_digest','issuer_ref','delegation_refs','action_digest']})
        if expected!=context['binding'] or (subject!=plan and A.lineage(subject)!=A.lineage(record)):
            raise ValueError('exact protected action/transaction binding mismatch')
        V.admit_work_plan(root,plan);V.admit_recovery_record(root,record)
        if self.tx.instruction_fingerprint(root)!=plan['governing_instruction_fingerprint']:
            raise ValueError('governing instructions changed')
        mutable={item['path'] for item in record['paths']}
        states={item['path']:item for item in plan['evidence_preimages']}
        for relative in set(V.protected_paths(root)) | {'AGENTS.md'}:
            if relative not in mutable and self.tx.path_state(root,relative)!=states.get(relative):
                raise ValueError('protected acceptance baseline changed')
        for item in record['paths']:
            allowed=[item['before']] if phase=='prepare' else [item['before'],item['after']]
            if self.tx.path_state(root,item['path']) not in allowed:
                raise ValueError('changed postimage or expanded recovery footprint')
        if subject.get('artifact_kind')=='transaction_receipt':
            evidence=[row for row in subject['validation'] if row.get('schema_version')=='octon.fixture-admission-evidence.v1' and row.get('fixture_only') is True]
            if len(evidence)!=1 or not evidence[0]['decisions']:raise ValueError('receipt lacks original admitted provenance')
            phases={self.evidence(context,row,expected)['phase'] for row in evidence[0]['decisions']}
            if not {'effect','validate'}.issubset(phases):raise ValueError('receipt lacks effect/validation phases')
        observations=root/'.octon/agent/transactions/evidence'/record['receipt_id']
        if observations.exists():
            for path in observations.glob('*.json'):
                value=V.load(path);A.validate_observation(value,record['receipt_id'])
                self.evidence(context,value['admission_evidence'],expected)
        history=root/'.octon/agent/transactions/protected'/record['receipt_id']
        actual={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in history.glob('*.json')} if history.exists() else {}
        if actual!=self.state['transaction_history']:
            raise ValueError('retained transaction history restored or changed')
        current,result,now=self.evaluate()
        action=current['action']; bound=context['binding']
        for key,target in [('plan_digest','plan_digest'),('operation','operation'),('work_ref','work_ref'),('work_contract_digest','work_digest'),('expected_state_digest','expected_state_digest'),('policy_digest','policy_digest')]:
            if action[key]!=bound[target]:raise ValueError('current exact action binding changed')
        if action['digest']!=bound['action_digest'] or current['intent']['digest']!=bound['intent_digest'] or current['intent']['principal_ref']!=bound['issuer_ref'] or [G.delegation_reference(row) for row in current['delegations']]!=bound['delegation_refs']:
            raise ValueError('current intent/issuer/lineage changed')
        nonce=secrets.token_hex(32)
        request={'schema_version':A.SCHEMA,'nonce':nonce,'actor_ref':context['actor_ref'],'phase':phase,'binding':bound}
        expires=min([now+A.timedelta(seconds=10),A.timestamp(current['controls']['fresh_until'])]+[A.timestamp(row['valid_until']) for row in current['delegations']]+[A.timestamp(row['fresh_until']) for row in current['controls']['obligation_results']]+[A.timestamp(row['period_accounting']['end']) for row in current['controls']['budget_snapshots']])
        response={'schema_version':A.SCHEMA,'request_digest':A.digest(request),'nonce':nonce,
                  'fixture_only':True,'live_authorization':False,'permission_grant':False,
                  'admitted':True,'expires_at':expires.isoformat(),'coverage':'covered',
                  'controls_digest':current['controls']['digest'],'issuer_ref':bound['issuer_ref'],
                  'actor_ref':context['actor_ref'],'binding':bound,'phase':phase,'shadow_result':result}
        issuer=self.state['issuers'][-1]
        return {'schema_version':'octon.fixture-admission-evidence.v1','fixture_only':True,
                'issuer_key_digest':issuer['digest'],'signed_decision':{'response':response,'signature':A.sign(Path(issuer['private']),response)}}

    def evidence(self, context, evidence, expected):
        for issuer in self.state['issuers']:
            if issuer['digest']==evidence['issuer_key_digest']:
                old=copy.deepcopy(context)
                old.update(issuer_public_key=issuer['public_key'],issuer_key_digest=issuer['digest'])
                return self.original_evidence(old,evidence,expected)
        raise ValueError('unenrolled issuer evidence')

    def event(self, kind, **details):
        value={'schema_version':EVENT,'permission_grant':False,'fixture_only':True,
               'generation':self.generation,'control_generation':self.state['control_generation'],
               'control_digest':self.state['control_digest'],
               'binding':self.state['context']['binding'],'profile_digest':A.digest(self.state['profile']),
               'sequence':len(self.state['transaction_history'])+1,
               'observed_at':trusted_time(self.state).isoformat(),
               'event':kind, **details}
        issuer=self.state['issuers'][-1]
        signed={'schema_version':EVENT,'permission_grant':False,'event':value,'issuer_key_digest':issuer['digest'],'signature':A.sign(Path(issuer['private']),value)}
        path=self.history/(A.digest(signed)+'.json')
        put(path,signed,exclusive=True)
        self.retain_history()
        return signed

    def retain_history(self):
        self.state=self.authority.load()
        self.state['transaction_history']={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in self.history.glob('*.json')}
        self.authority.save(self.state)

    def terminal_records(self,root):
        return {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
                for kind in ['receipts','recovered']
                for path in (root/'.octon/agent/transactions'/kind).glob('*.json')}

    def execute(self, command='apply'):
        if command not in {'apply','recover','rollback','reconcile'}:raise ValueError('unsupported protected command')
        with self.authority.lock():
            self.state=self.authority.load()
            if self.state['generation']!=self.generation:raise ValueError('stale controller fencing generation')
            if command not in self.state['allowed_commands']:raise ValueError('command outside trusted fixture enrollment')
            context=self.state['context'];root=Path(context['root']);record=context['record']
            kernel_custody(root,private=True)
            if self.terminal_records(root)!=self.state['terminal_records']:
                raise ValueError('terminal transaction record differs from retained high-water')
            context_path=self.authority.area/'executor-context.json';put(context_path,context)
            os.environ['OCTON_FIXTURE_ADMISSION_CONTEXT']=str(context_path)
            for path in [root/'.octon/runtime',root/'.octon/runtime/scripts']:
                sys.path.insert(0,str(path))
            spec=importlib.util.spec_from_file_location('protected_transaction',root/'.octon/runtime/scripts/octon_transaction.py')
            self.tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.tx)
            self.history=root/'.octon/agent/transactions/protected'/record['receipt_id']
            self.original_evidence=A.validate_evidence; original_guard=A.guarded
            original_replace=os.replace;original_unlink=Path.unlink;original_rmdir=Path.rmdir
            original_json=self.tx.write_new_json
            A.guarded=self.current;A.validate_evidence=self.evidence
            def replace(source,destination,*args,**kwargs):
                path=Path(destination)
                live=path.resolve().is_relative_to(root.resolve())
                if live:
                    self.checkpoint('before-effect',path)
                    # Effect dispatch linearizes here. No callback or blocking
                    # transport occurs between this check and protected rename.
                    self.evaluate()
                original_replace(source,destination,*args,**kwargs)
                if live:
                    if path.parent.name in {'receipts','recovered'}:
                        self.state=self.authority.load();self.state['terminal_records']=self.terminal_records(root);self.authority.save(self.state)
                    self.effects.append(path.relative_to(root).as_posix())
                    self.checkpoint('after-effect',path)
            def unlink(path,*args,**kwargs):
                live=path.resolve().is_relative_to(root.resolve()) and path.exists()
                if live:
                    self.checkpoint('before-effect',path);self.evaluate()
                result=original_unlink(path,*args,**kwargs)
                if live:self.checkpoint('after-effect',path)
                return result
            def rmdir(path,*args,**kwargs):
                live=path.resolve().is_relative_to(root.resolve()) and path.exists()
                if live:self.checkpoint('before-effect',path);self.evaluate()
                return original_rmdir(path,*args,**kwargs)
            def new_json(path,value):
                if not path.resolve().is_relative_to(root.resolve()):return original_json(path,value)
                relative=path.resolve().relative_to(root.resolve()).as_posix()
                metadata={'.octon/agent/transactions/'+kind+'/'+record['receipt_id']+'.json' for kind in ['pending','receipts','recovered']}
                if relative in metadata:
                    if value.get('permission_grant') is not False or A.lineage(value)!=A.lineage(record):
                        raise ValueError('metadata outside admitted transaction lineage')
                elif relative.startswith('.octon/agent/transactions/evidence/'+record['receipt_id']+'/'):
                    A.validate_observation(value,record['receipt_id']);self.evidence(context,value['admission_evidence'],context['binding'])
                    if path.name!=A.digest(value)+'.json':raise ValueError('observation content address mismatch')
                else:raise ValueError('new record outside admitted transaction')
                data=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
                path.parent.mkdir(parents=True,exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as handle:
                    temporary=Path(handle.name)
                    try:
                        handle.write(data);handle.flush();os.fsync(handle.fileno());os.chmod(temporary,0o600)
                        self.checkpoint('before-effect',path)
                        # Linux RENAME_NOREPLACE preserves existing owner's O_EXCL
                        # meaning while publishing complete metadata after the gate.
                        libc=ctypes.CDLL(None,use_errno=True)
                        rename=libc.renameat2
                        source_bytes= os.fsencode(temporary);target_bytes=os.fsencode(path)
                        self.evaluate()
                        result=rename(-100,source_bytes,-100,target_bytes,1)
                        if result:raise OSError(ctypes.get_errno(),'protected exclusive metadata publication refused')
                        temporary=None
                        if path.parent.name in {'receipts','recovered'}:
                            self.state=self.authority.load();self.state['terminal_records']=self.terminal_records(root);self.authority.save(self.state)
                        self.effects.append(relative);self.checkpoint('after-effect',path)
                    finally:
                        if temporary is not None:original_unlink(temporary,missing_ok=True)
            try:
                self.current(root,context['plan'], 'prepare' if command=='apply' else 'recover')
                self.checkpoint('admitted',None)
                consumed=self.history/'consumed.json'
                if command=='apply':
                    if consumed.exists():raise ValueError('consumed transaction identity; reconcile before retry')
                    self.event('identity-consumed')
                    put(consumed,{'schema_version':EVENT,'binding':context['binding'],'lineage':A.lineage(record)},exclusive=True)
                    self.retain_history()
                elif not consumed.is_file() or V.load(consumed)!= {'schema_version':EVENT,'binding':context['binding'],'lineage':A.lineage(record)}:
                    raise ValueError('missing original consumed identity or forged recovery path')
                os.replace=replace;Path.unlink=unlink;Path.rmdir=rmdir;self.tx.write_new_json=new_json
                pending=root/'.octon/agent/transactions/pending'/(record['receipt_id']+'.json')
                receipt=root/'.octon/agent/transactions/receipts'/(record['receipt_id']+'.json')
                if command=='apply':
                    result=self.tx.apply_plan(root,context['plan'],context['plan']['canonical_plan_digest'])[0]
                elif command=='rollback':result=self.tx.rollback(root,receipt)
                elif pending.exists():result=self.tx.recover_pending(root,pending)
                elif receipt.exists():
                    result=V.load(receipt)
                    self.current(root,result,'finalize')
                    if A.lineage(result)!=A.lineage(record) or result['status'] not in {'applied','rolled_back'}:
                        raise ValueError('receipt/recovery lineage mismatch')
                    for item in result['paths']:
                        if self.tx.path_state(root,item['path'])!=item['after' if result['status']=='applied' else 'before']:
                            raise ValueError('receipt postimage changed; no replay')
                else:
                    raise ValueError('consumed identity without retained journal/receipt; outcome uncertain')
                self.event('reconciled' if command!='apply' else 'applied',effects=list(self.effects),receipt_digest=A.digest(result))
                self.state=self.authority.load();self.state['terminal_records']=self.terminal_records(root);self.authority.save(self.state)
                return result
            finally:
                os.replace=original_replace;Path.unlink=original_unlink;Path.rmdir=original_rmdir
                self.tx.write_new_json=original_json
                A.guarded=original_guard;A.validate_evidence=self.original_evidence
                os.environ.pop('OCTON_FIXTURE_ADMISSION_CONTEXT',None)
                for _ in range(2):sys.path.pop(0)


def request(socket_path, actor_private, actor_ref, binding, generation, command='apply', nonce=None):
    value={'schema_version':REQUEST,'actor_ref':actor_ref,'binding':binding,
           'generation':generation,'command':command,'nonce':nonce or secrets.token_hex(32)}
    envelope={'request':value,'signature':A.sign(Path(actor_private),value)}
    with socket.socket(socket.AF_UNIX) as connection:
        connection.connect(str(socket_path));connection.sendall(A.canonical(envelope))
        with connection.makefile('rb') as stream:return A.strict(stream.readline(A.MAX+1))


def serve(authority, generation, socket_path, actor_public, *, ready=None):
    """Only worker data requests; no enrollment, control, key or code requests."""
    linux_owner()
    state=authority.load();context=state['context']
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(socket_path));os.chmod(socket_path,0o666);listener.listen(4)
        if ready:ready.send(True)
        while True:
            connection,_=listener.accept()
            with connection:
                connection.settimeout(5)
                try:
                    _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    if uid!=WORKER_UID:raise ValueError('unenrolled process identity')
                    with connection.makefile('rb') as stream:envelope=A.strict(stream.readline(A.MAX+1))
                    if set(envelope)!={'request','signature'}:raise ValueError('unsupported request')
                    value=envelope['request']
                    if set(value)!={'schema_version','actor_ref','binding','generation','command','nonce'} or value['schema_version']!=REQUEST or value['actor_ref']!=context['actor_ref'] or value['binding']!=context['binding'] or type(value['generation']) is not int or value['generation']!=generation:
                        raise ValueError('unenrolled actor/action/generation')
                    A.verify(actor_public,value,envelope['signature'])
                    nonce=value['nonce']
                    if not isinstance(nonce,str) or len(nonce)!=64 or any(c not in '0123456789abcdef' for c in nonce):raise ValueError('unsupported nonce')
                    with authority.lock():
                        state=authority.load()
                        if state['generation']!=generation:raise ValueError('stale controller')
                        put(authority.area/'nonces'/nonce,{'request_digest':A.digest(value)},exclusive=True)
                    result=Executor(authority,generation).execute(value['command'])
                    connection.sendall(A.canonical({'schema_version':REQUEST,'fixture_only':True,'permission_grant':False,'receipt_digest':A.digest(result),'status':result['status']}))
                except Exception:
                    connection.sendall(A.canonical({'error':'protected fixture refused; reconcile unknown outcome before retry'}))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-execute',type=Path,required=True)
    parser.add_argument('--generation',type=int,required=True)
    parser.add_argument('--command',choices=['apply','recover','rollback','reconcile'],default='apply')
    args=parser.parse_args()
    try:
        result=Executor(Authority(args.fixture_execute),args.generation).execute(args.command)
        print(json.dumps({'schema_version':EVENT,'permission_grant':False,'fixture_only':True,
                          'status':result['status'],'receipt_digest':A.digest(result)}))
    except Exception as error:
        print(json.dumps({'error':str(error),'permission_grant':False,'outcome':'reconciliation_required'}))
        raise SystemExit(2)
