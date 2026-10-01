#!/usr/bin/env python3
"""Fail-closed host qualification; run only in an owned Linux container as root."""
from __future__ import annotations
import argparse
import copy
import ctypes
import errno
from datetime import datetime, timedelta, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest


def source_revision():
    root=Path(__file__).resolve().parents[3]
    head=(root/'.git/HEAD').read_text().strip()
    if head.startswith('ref: '):
        relative=head[5:]
        if relative.startswith('/') or '..' in relative.split('/'):
            raise ValueError('unsafe source Git reference')
        path=root/'.git'/relative
        if path.is_file():head=path.read_text().strip()
        else:
            refs=dict((row.split()[1],row.split()[0]) for row in (root/'.git/packed-refs').read_text().splitlines() if row and not row.startswith(('#','^')))
            head=refs[relative]
    if len(head)!=40 or any(c not in '0123456789abcdef' for c in head):raise ValueError('invalid exact source commit')
    return head


def portable_refusal():
    """No Linux imports/capability claims on unsupported ordinary hosts."""
    if sys.platform!='linux' or os.geteuid()!=0:
        return {'qualified':False,'consequential_execution':'disabled',
                'reason':'requires explicit disposable Linux root/UID boundary'}
    return None


if portable_refusal() is None:
    import fcntl
    import protected_fixture as P
    import fixture_admission as A
    import installation_runtime_v2 as V
    from test_fixture_admission import AdmissionTests, seal


class ProtectedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        P.linux_owner()
        cls.results=[]
        AdmissionTests.setUpClass()
        cls.addClassCleanup(AdmissionTests.doClassCleanups)

    def setUp(self):
        self.fixture=AdmissionTests('test_01_native_dependency_and_portable_paths_early')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        f=self.fixture;f.stop_controller()
        f.area_path.chmod(0o755);self.root=f.root;self.root.chmod(0o700)
        historic_decision={'schema_version':'harness.decision.v1','id':'DEC-0001','status':'rejected','previous_status':'proposed',
                          'title':'Historical synthetic fixture decision','created_at':'2020-01-01',
                          'authority_source':'authority:historical-synthetic-fixture','owner':'fixture-owner',
                          'scope':'Fixture history only','supersedes':None,'successor':None,
                          'limitations':['Existing synthetic record; grants no execution authority.']}
        historic_evidence={'schema_version':'harness.evidence.v1','id':'EVD-0001','title':'Historical synthetic fixture evidence',
                           'task':'TASK-0001','recorded_at':'2020-01-01','authority_source':'authority:historical-synthetic-fixture',
                           'owner':'fixture-owner','scope':'Fixture history only','method':'Historical fixture seed',
                           'environment':'Disposable non-production fixture','subject_revision_or_fingerprint':'historical-fixture-v1',
                           'result':'not_run','fresh_until':None,'supersedes':None,'limitations':['No readiness or authority claim.']}
        self.historical={}
        for kind,record in [('decisions',historic_decision),('evidence',historic_evidence)]:
            path=self.root/'.octon/agent'/kind/(record['id']+'-historical.md');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('---\n'+json.dumps(record,indent=2)+'\n---\n\nHistorical synthetic fixture bytes.\n')
            self.historical[path]=path.read_bytes()
        P.install(self.root)
        # The successor overlay is part of the exact acceptance baseline before
        # action planning. Rebuild the same existing-task plan through its owner.
        f.plan_path=f.area_path/'protected-handoff.json'
        f.cli('work','handoff','--task-id','TASK-0001','--next-action','Continue admitted local work',
              '--summary','Authenticated fixture handoff','--operator','fixture-operator','--output',f.plan_path)
        f.plan=V.load(f.plan_path)
        decoded=f.tx._decode_operations(f.plan)
        staged,_,_=f.tx._staged_result(self.root,f.plan,decoded)
        outcomes=f.tx._planned_outcomes(f.plan,decoded,staged)
        paths=f.tx._receipt_paths(self.root,f.plan,outcomes)
        f.record={'receipt_id':f.plan['planned_receipt_id'],'operation':f.plan['operation'],
                  'plan_digest':f.plan['canonical_plan_digest'],'paths':paths,
                  'created_directories':f.tx._created_parent_directories(self.root,[row['path'] for row in paths])}
        f.bound=A.binding(self.root,f.plan,f.record);f.bound['refresh']=f.refresh
        action=f.bundle['action'];controls=f.bundle['controls']
        action.update(plan_digest=f.bound['plan_digest'],expected_state_digest=f.bound['expected_state_digest'],
                      policy_digest=f.bound['policy_digest'],work_contract_digest=f.bound['work_digest'])
        controls.update(state_digest=action['expected_state_digest'],policy_digest=action['policy_digest'])
        seal(f.bundle)
        f.bound.update(intent_digest=f.bundle['intent']['digest'],issuer_ref=f.bundle['intent']['principal_ref'],
                       delegation_refs=[__import__('governance_shadow').delegation_reference(row) for row in f.bundle['delegations']],action_digest=action['digest'])
        f.context.update(plan=f.plan,record=f.record,binding=f.bound)
        self.authority=P.Authority.enroll(f.area_path/'retained-authority',f.context,f.bundle)
        self.generation=1;self.saved=f.original_task
        self.worker=f.area_path/'worker';self.worker.mkdir(mode=0o755)
        actor=self.worker/'actor.private.pem';shutil.copy2(f.actor_private,actor)
        actor.chmod(0o600);self.actor_public=A.command(['pkey','-in',actor,'-pubout']).decode()
        os.chown(actor,P.WORKER_UID,P.WORKER_UID);os.chown(self.worker,P.WORKER_UID,P.WORKER_UID)
        self.addCleanup(lambda:os.chown(self.worker,0,0))
        self.actor=actor
        self.socket=f.area_path/'worker.sock'
        self.addCleanup(lambda:self.socket.unlink(missing_ok=True))
        self.context=self.authority.load()['context']
        self.output_area=Path('/evidence') if Path('/evidence/ownership.json').is_file() else f.area_path/'trusted-results'
        if not self.output_area.exists():self.output_area.mkdir(mode=0o755)
        self.output_probe=self.output_area/'trusted-result.json';P.put(self.output_probe,{'schema_version':P.EVENT,'permission_grant':False})
        self.addCleanup(self.assert_history_preserved)

    def assert_history_preserved(self):
        for path,data in self.historical.items():self.assertEqual(path.read_bytes(),data)
        self.assertEqual((self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes(),self.saved)

    def tearDown(self):
        artifacts=[]
        for kind in ['pending','receipts','recovered','protected','evidence']:
            for path in sorted((self.root/'.octon/agent/transactions'/kind).rglob('*.json')):
                value=V.load(path)
                artifacts.append({'path':path.relative_to(self.root).as_posix(),
                                  'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'schema_version':value.get('schema_version'),
                                  'status':value.get('status'),
                                  'lineage_digest':A.digest(A.lineage(value)) if 'paths' in value else None})
        self.results.append({'case':self._testMethodName,'record_ref':self.context['record']['receipt_id'],
                             'lineage_digest':A.digest(A.lineage(self.context['record'])),
                             'historical_bytes':[{'id':path.name.split('-historical')[0],
                                                   'sha256':hashlib.sha256(data).hexdigest(),
                                                   'retained_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                                                  for path,data in self.historical.items()],
                             'task_sha256':hashlib.sha256(self.saved).hexdigest(),
                             'retained_task_sha256':hashlib.sha256((self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes()).hexdigest(),
                             'artifacts':artifacts})

    def execute(self, command='apply', fault=None, generation=None):
        return P.Executor(self.authority,self.generation if generation is None else generation,fault).execute(command)

    def control(self, mutate):
        bundle=copy.deepcopy(self.authority.load()['bundle']);mutate(bundle);seal(bundle)
        self.authority.control(self.authority.snapshot(),bundle)

    def process(self, function):
        child=multiprocessing.get_context('fork').Process(target=function)
        child.start();self.addCleanup(lambda: self.stop(child))
        return child

    def stop(self, child):
        if child.is_alive():child.kill()
        child.join(15)
        self.assertFalse(child.is_alive(),'owned worker/controller must terminate before evidence export')

    def pending(self):
        return self.root/'.octon/agent/transactions/pending'/(self.context['record']['receipt_id']+'.json')

    def receipt(self):
        return self.root/'.octon/agent/transactions/receipts'/(self.context['record']['receipt_id']+'.json')

    def history(self):
        return self.root/'.octon/agent/transactions/protected'/self.context['record']['receipt_id']

    def crash_at(self, predicate):
        read,send=multiprocessing.Pipe(False)
        wait,release=multiprocessing.Pipe(False)
        def child():
            def fault(name,path):
                if predicate(name,path):send.send(True);wait.recv()
            self.execute(fault=fault)
        child=self.process(child)
        self.assertTrue(read.poll(120),'fault barrier unavailable');read.recv()
        os.kill(child.pid,signal.SIGKILL);child.join(15)
        self.assertEqual(child.exitcode,-signal.SIGKILL)
        self.generation=self.authority.replace_controller(self.authority.snapshot())

    def test_worker_real_exclusion_and_narrow_signed_request(self):
        ready,send=multiprocessing.Pipe(False)
        controller=self.process(lambda:P.serve(self.authority,1,self.socket,self.actor_public,ready=send))
        self.assertTrue(ready.poll(15));ready.recv()
        output=self.worker/'proof.json';owner_pid=os.getpid()
        inherited=os.open(self.authority.area/'issuer-1.private.pem',os.O_RDONLY)
        os.dup2(inherited,70000);os.close(inherited)
        self.addCleanup(lambda:os.close(70000))
        targets=[self.authority.anchor,self.authority.area/'issuer-1.private.pem',self.root/'.octon/runtime/fixture_admission.py',self.root/'.octon/agent/policy.json',self.root/'.octon/agent/state/focus.json',self.output_probe]
        self.assertTrue(all(path.is_file() for path in targets))
        def worker():
            P.drop_worker()
            denied={}
            denied['stdio disconnected']=all(os.readlink('/proc/self/fd/'+str(descriptor))=='/dev/null' for descriptor in [0,1,2])
            try:os.fstat(70000);denied['inherited issuer descriptor']=False
            except OSError as error:denied['inherited issuer descriptor']=error.errno==errno.EBADF
            for path in targets+[Path(f'/proc/{owner_pid}/{suffix}') for suffix in ['mem','environ','fd/0','root','cwd']]:
                for mode in ['read','write']:
                    try:
                        if mode=='read':path.open('rb').close()
                        else:path.open('ab').close()
                        denied[str(path)+' '+mode]=False
                    except OSError as error:denied[str(path)+' '+mode]=error.errno in {1,13,30}
            try:Path('/source/skills/octon-project-bootstrap/scripts/protected_fixture.py').open('ab').close();denied['read-only baseline write']=False
            except OSError as error:denied['read-only baseline write']=error.errno in {1,13,30}
            denied['docker socket absent']=not Path('/var/run/docker.sock').exists()
            for name,operation in [('signal',lambda:os.kill(owner_pid,signal.SIGCONT)),('setuid',lambda:os.setuid(0)),('groups',lambda:os.setgroups([0])),('clock',lambda: __import__('time').clock_settime(__import__('time').CLOCK_REALTIME,0))]:
                try:operation();denied[name]=False
                except OSError:denied[name]=True
            libc=ctypes.CDLL(None,use_errno=True)
            denied['ptrace']=libc.ptrace(16,owner_pid,0,0)==-1
            status={row.split(':',1)[0]:row.split(':',1)[1].strip() for row in Path('/proc/self/status').read_text().splitlines() if ':' in row}
            env_clean=set(os.environ)=={'PATH','PYTHONDONTWRITEBYTECODE'}
            (self.worker/'writable').write_text('worker proposal')
            first=P.request(self.socket,self.actor,self.context['actor_ref'],self.context['binding'],1,nonce='1'*64)
            replay=P.request(self.socket,self.actor,self.context['actor_ref'],self.context['binding'],1,nonce='1'*64)
            wrong=P.request(self.socket,self.actor,'agent:other',self.context['binding'],1)
            private,_=A.keypair(self.worker,'unenrolled')
            unenrolled=P.request(self.socket,private,self.context['actor_ref'],self.context['binding'],1)
            expanded=copy.deepcopy(self.context['binding']);expanded['action_digest']='0'*64
            scope=P.request(self.socket,self.actor,self.context['actor_ref'],expanded,1)
            bool_generation=P.request(self.socket,self.actor,self.context['actor_ref'],self.context['binding'],True)
            with socket.socket(socket.AF_UNIX) as channel:
                channel.connect(str(self.socket));channel.sendall(A.canonical({'response':{'admitted':True},'signature':'replayed admission response'}))
                with channel.makefile('rb') as stream:forged=A.strict(stream.readline(A.MAX+1))
            output.write_text(json.dumps({'denied':denied,'status':status,'environment_clean':env_clean,'first':first,'replay':replay,'wrong_actor':wrong,'unenrolled_issuer_actor':unenrolled,'expanded_scope':scope,'forged_response':forged,'boolean_generation':bool_generation}))
        worker=self.process(worker);worker.join(180);self.assertEqual(worker.exitcode,0)
        proof=json.loads(output.read_text());self.assertTrue(all(proof['denied'].values()),proof['denied'])
        for key in ['CapInh','CapPrm','CapEff','CapBnd','CapAmb']:self.assertEqual(int(proof['status'][key],16),0)
        self.assertEqual(proof['status']['Groups'],'');self.assertEqual(proof['status']['NoNewPrivs'],'1')
        self.assertTrue(proof['environment_clean']);self.assertEqual(proof['first']['status'],'applied')
        self.assertIn('error',proof['replay']);self.assertIn('error',proof['wrong_actor'])
        for key in ['unenrolled_issuer_actor','expanded_scope','forged_response','boolean_generation']:self.assertIn('error',proof[key])
        self.assertEqual((self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes(),self.saved)
        self.results.append({'case':self._testMethodName,'worker_uid':65534,'privilege_proof':{key:proof['status'][key] for key in ['Groups','CapInh','CapPrm','CapEff','CapBnd','CapAmb','NoNewPrivs','Seccomp']},'denials':proof['denied'],'effect_status':proof['first']['status']})

    def test_stop_before_admission_and_stale_snapshot_refuse(self):
        snapshot=self.authority.snapshot();old=copy.deepcopy(self.authority.load()['bundle'])
        self.control(lambda value:value['controls'].update(emergency_stop=True))
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse(self.history().exists());self.assertFalse(self.pending().exists())
        with self.assertRaises(ValueError):self.authority.control(snapshot,old)
        with self.assertRaises(ValueError):self.authority.control(self.authority.snapshot(),old)
        with self.assertRaises(ValueError):self.authority.replace_controller(snapshot)

    def test_control_race_orders_after_transaction_and_old_controller_fenced(self):
        read,send=multiprocessing.Pipe(False);wait,release=multiprocessing.Pipe(False)
        done,done_send=multiprocessing.Pipe(False)
        def transaction():
            hit=False
            def fault(name,path):
                nonlocal hit
                if name=='before-effect' and path==self.root/'.octon/agent/state/focus.json' and not hit:
                    hit=True;send.send(True);wait.recv()
            self.execute(fault=fault)
        child=self.process(transaction);self.assertTrue(read.poll(120));read.recv()
        contention,notify=multiprocessing.Pipe(False)
        def stop():
            with (self.authority.area/'fence.lock').open('r+b') as handle:
                try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);notify.send(False)
                except BlockingIOError:notify.send(True)
            self.control(lambda value:value['controls'].update(emergency_stop=True));done_send.send(True)
        updater=self.process(stop)
        self.assertTrue(contention.poll(15));self.assertTrue(contention.recv(),'updater did not observe live lock contention')
        self.assertFalse(done.poll(),'control update cannot pass held transaction fence')
        release.send(True);child.join(120);updater.join(30)
        self.assertEqual(child.exitcode,0);self.assertEqual(updater.exitcode,0);self.assertTrue(done.poll());done.recv()
        self.assertEqual(V.load(self.receipt())['status'],'applied')
        self.generation=self.authority.replace_controller(self.authority.snapshot())
        with self.assertRaisesRegex(ValueError,'stale controller'):self.execute('reconcile',generation=1)
        with self.assertRaises(ValueError):self.execute('reconcile')
        self.results.append({'case':self._testMethodName,'order':'transaction committed before stop; subsequent recovery denied'})

    def test_restart_before_effects_keeps_old_process_present(self):
        ready,send=multiprocessing.Pipe(False);wait,release=multiprocessing.Pipe(False)
        done,result=multiprocessing.Pipe(False)
        def old():
            send.send(True);wait.recv()
            try:self.execute();result.send('unexpected effect')
            except ValueError as error:result.send(str(error))
        child=self.process(old);self.assertTrue(ready.poll(15));ready.recv()
        self.generation=self.authority.replace_controller(self.authority.snapshot())
        release.send(True);self.assertTrue(done.poll(15));self.assertIn('stale controller',done.recv())
        self.assertEqual(self.execute()['status'],'applied')
        with self.assertRaises(ValueError):self.execute()

    def test_sigkill_after_journal_and_partial_writes_recover_exactly(self):
        self.crash_at(lambda name,path:name=='after-effect' and path==self.pending())
        self.assertTrue(self.pending().exists());self.assertTrue((self.history()/'consumed.json').exists())
        self.assertEqual(self.execute('recover')['status'],'recovered_to_preimage')
        with self.assertRaises(ValueError):self.execute()
        self.results.append({'case':self._testMethodName,'termination':'SIGKILL','outcome':'journal retained; new controller restored exact original footprint'})

    def test_sigkill_partial_local_write_and_changed_postimage_refuse(self):
        focus=self.root/'.octon/agent/state/focus.json'
        self.crash_at(lambda name,path:name=='after-effect' and path==focus)
        self.assertTrue(self.pending().exists());self.assertIn('Continue admitted',focus.read_text())
        focus.write_text('independent postimage')
        with self.assertRaises(ValueError):self.execute('recover')
        self.assertTrue(self.pending().exists());self.assertEqual(focus.read_text(),'independent postimage')

    def test_sigkill_partial_local_write_recovers_with_new_issuer(self):
        focus=self.root/'.octon/agent/state/focus.json'
        self.crash_at(lambda name,path:name=='after-effect' and path==focus)
        self.assertEqual(self.execute('recover')['status'],'recovered_to_preimage')
        for item in self.context['record']['paths']:
            self.assertEqual(self.fixture.tx.path_state(self.root,item['path']),item['before'])
        self.assertEqual(len(self.authority.load()['issuers']),2)

    def test_sigkill_completed_effect_before_receipt_does_not_replay(self):
        self.crash_at(lambda name,path:name=='before-effect' and path==self.receipt())
        self.assertTrue(self.pending().exists());self.assertFalse(self.receipt().exists())
        for item in self.context['record']['paths']:
            self.assertEqual(self.fixture.tx.path_state(self.root,item['path']),item['after'])
        self.assertEqual(self.execute('recover')['status'],'recovered_to_preimage')
        for item in self.context['record']['paths']:
            self.assertEqual(self.fixture.tx.path_state(self.root,item['path']),item['before'])
        with self.assertRaises(ValueError):self.execute()

    def test_lost_response_reconcile_preserves_receipt_and_history(self):
        self.execute()
        receipt_bytes=self.receipt().read_bytes()
        self.generation=self.authority.replace_controller(self.authority.snapshot())
        self.assertEqual(self.execute('reconcile')['status'],'applied')
        self.assertEqual(self.receipt().read_bytes(),receipt_bytes)
        self.assertEqual(len(self.authority.load()['issuers']),2)
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual((self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes(),self.saved)

    def test_revoked_during_recovery_and_footprint_expansion_refuse(self):
        self.crash_at(lambda name,path:name=='after-effect' and path==self.pending())
        self.control(lambda value:value['controls']['revoked_delegation_ids'].append(value['delegations'][0]['id']))
        before=self.pending().read_bytes()
        with self.assertRaises(ValueError):self.execute('recover')
        self.assertEqual(self.pending().read_bytes(),before)
        self.assertFalse(self.receipt().exists())

    def test_forged_pending_receipt_and_observation_refuse(self):
        self.crash_at(lambda name,path:name=='after-effect' and path==self.pending())
        pending=V.load(self.pending());pending['paths'][0]['path']='.octon/agent/policy.json';P.put(self.pending(),pending)
        with self.assertRaises(Exception):self.execute('recover')
        self.assertTrue(self.pending().exists())

    def test_receipt_and_signed_history_restoration_refuse(self):
        self.execute();original=self.receipt().read_bytes()
        postimages={item['path']:(self.root/item['path']).read_bytes() for item in self.context['record']['paths'] if item['after']['type']=='file'}
        value=V.load(self.receipt());value['validation'][-1]['decisions']=[];P.put(self.receipt(),value)
        with self.assertRaises(ValueError):self.execute('reconcile')
        self.receipt().write_bytes(original)
        self.execute('rollback')
        for item in self.context['record']['paths']:
            if item['after']['type']=='file':
                path=self.root/item['path'];path.write_bytes(postimages[item['path']]);path.chmod(item['after']['mode'])
        self.receipt().write_bytes(original)
        with self.assertRaises(ValueError):self.execute('reconcile')

    def test_signed_historical_observation_forgery_refuses(self):
        self.execute()
        path=next((self.root/'.octon/agent/transactions/evidence'/self.context['record']['receipt_id']).glob('*.json'))
        original=path.read_bytes();value=V.load(path)
        value['admission_evidence']['signed_decision']['response']['issuer_ref']='principal:forged'
        forged=path.parent/(A.digest(value)+'.json');P.put(forged,value);path.unlink()
        with self.assertRaises(ValueError):self.execute('reconcile')
        forged.unlink();path.write_bytes(original)
        self.assertEqual(self.execute('reconcile')['status'],'applied')

    def test_actual_controller_snapshot_restore_and_lock_replacement_refuse(self):
        original=self.authority.anchor.read_bytes()
        self.control(lambda value:value['controls'].update(emergency_stop=True))
        self.authority.anchor.write_bytes(original)
        with self.assertRaisesRegex(ValueError,'high-water'):self.execute()

    def test_actual_deadline_crossing_at_explicit_admission_barrier(self):
        deadline=datetime.now(timezone.utc)+timedelta(seconds=20)
        self.control(lambda value:value['controls'].update(fresh_until=deadline.isoformat()))
        read,send=multiprocessing.Pipe(False);wait,release=multiprocessing.Pipe(False)
        result,answer=multiprocessing.Pipe(False)
        def child():
            def fault(name,path):
                if name=='admitted':send.send(True);wait.recv()
            try:self.execute(fault=fault);answer.send('unexpected effect')
            except Exception:answer.send('refused')
        child=self.process(child);self.assertTrue(read.poll(15));read.recv()
        # Explicit admission barrier holds the operation; timer only advances
        # the real trusted clock against unchanged authority bytes.
        timer=multiprocessing.Event();timer.wait(max(0,(deadline-datetime.now(timezone.utc)).total_seconds())+.01)
        release.send(True);self.assertTrue(result.poll(30));self.assertEqual(result.recv(),'refused');child.join(15)
        self.assertFalse(self.pending().exists());self.assertFalse(self.receipt().exists())
        self.results.append({'case':self._testMethodName,'authority_bytes_unchanged_after_admission':True,'clock':'real kernel wall/monotonic','result':'expired before effect dispatch'})

    def test_actual_deadline_crossing_between_canonical_writes(self):
        deadline=datetime.now(timezone.utc)+timedelta(seconds=20)
        self.control(lambda value:value['controls'].update(fresh_until=deadline.isoformat()))
        read,send=multiprocessing.Pipe(False);wait,release=multiprocessing.Pipe(False)
        result,answer=multiprocessing.Pipe(False)
        focus=self.root/'.octon/agent/state/focus.json'
        def child():
            def fault(name,path):
                if name=='after-effect' and path==focus:send.send(True);wait.recv()
            try:self.execute(fault=fault);answer.send('unexpected completion')
            except Exception:answer.send('refused with journal')
        child=self.process(child);self.assertTrue(read.poll(15));read.recv()
        multiprocessing.Event().wait(max(0,(deadline-datetime.now(timezone.utc)).total_seconds())+.01)
        release.send(True);self.assertTrue(result.poll(30));self.assertEqual(result.recv(),'refused with journal');child.join(15)
        self.assertTrue(self.pending().exists());self.assertFalse(self.receipt().exists())
        self.assertIn('Continue admitted',focus.read_text())
        self.generation=self.authority.replace_controller(self.authority.snapshot())
        with self.assertRaises(ValueError):self.execute('recover')
        self.results.append({'case':self._testMethodName,'clock':'real kernel wall/monotonic','result':'first canonical write ordered before expiry; next gate and recovery refused; journal retained'})

    def test_protected_narrowing_accounting_and_enrollment_matrix(self):
        cases=[lambda v:v['delegations'][1]['scope']['resources'].append('resource:extra'),
               lambda v:v['controls'].update(accounting_observation='unknown'),
               lambda v:v['controls']['obligation_results'][0].update(outcome='unknown'),
               lambda v:v['action'].update(changes_sovereign_boundary=True),
               lambda v:v['delegations'][0].update(issuer_ref='principal:other'),
               lambda v:v['controls'].update(authority_epoch=2)]
        for index,mutate in enumerate(cases):
            bundle=copy.deepcopy(self.fixture.bundle);mutate(bundle);seal(bundle)
            owner=P.Authority.enroll(self.fixture.area_path/('denied-'+str(index)),self.fixture.context,bundle)
            with self.assertRaises(ValueError):P.Executor(owner,1).execute()
        owner=P.Authority.enroll(self.fixture.area_path/'apply-only',self.fixture.context,self.fixture.bundle,allowed_commands=['apply'])
        with self.assertRaisesRegex(ValueError,'enrollment'):P.Executor(owner,1).execute('recover')

    def test_independent_copied_executor_without_source_imports(self):
        result=subprocess.run([sys.executable,'-I','-B',self.root/'.octon/runtime/protected_fixture.py',
                               '--fixture-execute',self.authority.area,'--generation','1'],
                              cwd=self.worker,capture_output=True,text=True,
                              env={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','OCTON_OWNED_EPHEMERAL_CONTAINER':'protected-fixture-v1'})
        self.assertEqual(result.returncode,0,result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout)['status'],'applied')
        self.fixture.cli('check')

    def test_malicious_detached_worker_orphan_is_killed_and_reaped(self):
        ready=self.worker/'orphan-ready.json'
        def worker():
            P.drop_worker()
            pid=os.fork()
            if pid:
                os._exit(0)
            os.setsid()
            ready.write_text(json.dumps({'pid':os.getpid(),'uid':os.getuid(),
                                          'groups':os.getgroups(),'stdio':[os.readlink('/proc/self/fd/'+str(fd)) for fd in [0,1,2]]}))
            while True:signal.pause()
        child=self.process(worker);child.join(15);self.assertEqual(child.exitcode,0)
        deadline=time.monotonic()+15
        while not ready.is_file() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(ready.is_file(),'orphan readiness barrier unavailable')
        proof=json.loads(ready.read_text());self.assertEqual(proof['uid'],65534)
        self.assertEqual(proof['groups'],[]);self.assertEqual(proof['stdio'],['/dev/null']*3)
        self.assertIn(proof['pid'],P.worker_processes())
        disposition=P.kill_workers();self.assertIn(proof['pid'],disposition['killed'])
        self.assertEqual(P.worker_processes(),[])
        self.assertFalse(Path('/proc/'+str(proof['pid'])).exists())
        self.results.append({'case':self._testMethodName,'cleanup':disposition,'actual_detached_orphan_uid':proof['uid']})

    def test_namespace_cleanup_and_enrollment_reject_non_supervisor(self):
        read,send=multiprocessing.Pipe(False)
        def child():
            denied=[]
            for operation in [P.kill_workers,lambda:self.authority.replace_controller(self.authority.snapshot())]:
                try:operation();denied.append(False)
                except ValueError:denied.append(True)
            send.send(denied)
        child=self.process(child);self.assertTrue(read.poll(15));self.assertEqual(read.recv(),[True,True]);child.join(15)
        self.assertEqual(child.exitcode,0)

    def test_expiry_after_admission_and_midwrite_preserves_uncertainty(self):
        # Trusted fault advances the retained high-water/freshness, never the
        # worker's clock or sleep scheduling. Final dispatch gate must re-evaluate.
        def fault(name,path):
            if name=='before-effect' and path==self.root/'.octon/agent/state/focus.json':
                state=self.authority.load()
                controls=state['bundle']['controls']
                controls['fresh_until']='2000-01-01T00:00:00Z';seal(state['bundle'])
                state['control_digest']=A.digest(state['bundle']);state['control_generation']+=1
                self.authority.save(state)
        with self.assertRaises(Exception):self.execute(fault=fault)
        self.assertTrue(self.pending().exists());self.assertTrue((self.history()/'consumed.json').exists())
        with self.assertRaises(ValueError):self.execute('recover')

    def test_missing_anchor_mixed_profile_and_time_rewind_disable(self):
        profile=self.root/'.octon/protected-profile.json';value=V.load(profile)
        value['schema_version']='unsupported';P.put(profile,value)
        with self.assertRaises(ValueError):self.execute()
        state=self.authority.load();state['time_floor']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat();self.authority.save(state)
        with self.assertRaises(ValueError):P.Executor(self.authority,1).evaluate()
        self.authority.anchor.unlink()
        with self.assertRaises(ValueError):P.Authority(self.authority.area)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualify-linux-container',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--emit-evidence',action='store_true')
    parser.add_argument('tests',nargs='*')
    args=parser.parse_args()
    refusal=portable_refusal()
    if not args.qualify_linux_container or refusal:
        print(json.dumps(refusal or {'qualified':False,'consequential_execution':'disabled','reason':'explicit ephemeral qualification flag required'}))
        return 2 if args.qualify_linux_container else 0
    if os.getpid()!=1:
        print(json.dumps({'qualified':False,'consequential_execution':'disabled','reason':'top-level qualification requires private PID1 supervisor'}))
        return 2
    ownership=None
    if args.output:
        if not args.output.is_absolute() or args.output.parent!=Path('/evidence') or args.output.parent.is_symlink():
            raise ValueError('output must use the explicitly owned /evidence bind')
        if args.output.exists() or args.output.is_symlink():raise ValueError('qualification output already exists; preserve prior attempt')
        mounts=[line.split(' - ',1) for line in Path('/proc/self/mountinfo').read_text().splitlines()]
        if not any(left.split()[4]=='/evidence' and right.split()[0]=='tmpfs' for left,right in mounts):
            raise ValueError('qualification evidence requires private kernel tmpfs; writable host binds are unqualified')
        P.linux_owner()
        os.chown(args.output.parent,0,0);args.output.parent.chmod(0o755)
        ownership={'schema_version':'octon.protected-fixture-evidence-custody.v1','permission_grant':False,
                   'uid':args.output.parent.stat().st_uid,'mode':oct(args.output.parent.stat().st_mode & 0o777),'filesystem':'kernel-tmpfs'}
        P.put(args.output.parent/'ownership.json',ownership)
    names=args.tests or [name for name in ProtectedTests.__dict__ if name.startswith('test_')]
    suite=unittest.TestSuite(ProtectedTests(name) for name in names)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    cleanup=P.kill_workers()
    evidence={'schema_version':'octon.protected-fixture-qualification.v1','permission_grant':False,
              'supported_profile':'linux-disposable-container-distinct-uid-v1',
              'qualified':result.wasSuccessful(),'tests_run':result.testsRun,
              'failures':len(result.failures),'errors':len(result.errors),
              'source_revision':source_revision(),
              'host':{'system':os.uname().sysname,'release':os.uname().release,'machine':os.uname().machine,'python':sys.version,'uid':os.geteuid(),
                      'mount_custody':[{'path':left.split()[4],'filesystem':right.split()[0],'options':left.split()[5]}
                                       for left,right in [line.split(' - ',1) for line in Path('/proc/self/mountinfo').read_text().splitlines()]
                                       if left.split()[4] in {'/tmp','/evidence','/source'}]},
              'evidence_custody':ownership,
              'worker_cleanup_before_export':cleanup,
              'cases':ProtectedTests.results,
              'unqualified':['live authority','real external providers','storage/anchor rollback','power-loss durability','hard realtime deadline enforcement','macOS/Windows parity']}
    if args.output:args.output.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
    print(json.dumps({key:value for key,value in evidence.items() if key!='cases'},sort_keys=True))
    if args.emit_evidence:
        # Every owned worker/controller has joined and worker stdio was detached.
        # This is report transport, never a control/authorization input.
        print('OCTON_PROTECTED_EVIDENCE_BEGIN')
        print(json.dumps(evidence,sort_keys=True))
        print('OCTON_PROTECTED_EVIDENCE_END')
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
