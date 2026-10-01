#!/usr/bin/env python3
"""Actual local handoff, separate authenticated fixture controller, adversarial recovery."""
from __future__ import annotations
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path,PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import fixture_admission as A
import governance_shadow as G
import installation_runtime as R
import installation_runtime_v2 as V2
import qualify_disposable_runtime as Q
from test_disposable_runtime import module,snapshot,write


def seal(value):
    value['intent']['digest']=G.record_digest(value['intent'])
    ref=G.intent_reference(value['intent'])
    value['work_binding']['intent_ref']=ref;value['action']['intent_ref']=ref
    for index,grant in enumerate(value['delegations']):
        grant['intent_ref']=ref
        if index:grant['parent_ref']=G.delegation_reference(value['delegations'][index-1])
        grant['digest']=G.record_digest(grant)
        value['controls']['budget_snapshots'][index]['delegation_ref']=G.delegation_reference(grant)
    value['action']['digest']=G.record_digest(value['action'])
    for item in value['controls']['obligation_results']:item['action_digest']=value['action']['digest']
    value['controls']['digest']=G.record_digest(value['controls'])
    return value


class AdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.area=tempfile.TemporaryDirectory(prefix='octon-admission-suite-')
        cls.addClassCleanup(cls.area.cleanup)
        area=Path(cls.area.name); old=area/'old'; cls.base=area/'base'
        Q.generate(old)
        def cli(root,*args):
            result=subprocess.run([sys.executable,'-B',root/'octon',*map(str,args)],cwd=root,capture_output=True,text=True)
            if result.returncode: raise ValueError(result.stderr or result.stdout)
        path=area/'start.json'
        cli(old,'work','start','--title','Admission fixture task','--scope','One bounded local handoff',
            '--authority-basis','authority:current-user-bounded-disposable-fixture','--owner','fixture-owner',
            '--operator','fixture-operator','--acceptance','Exact task and receipt preservation',
            '--validation','Read-only target check','--next-action','Qualify admission','--output',path)
        plan=R.load(path);cli(old,'transaction','apply','--plan',path,'--accept-digest',plan['canonical_plan_digest'])
        Q.generate(cls.base,admission=True)
        for relative in ['tasks/TASK-0001.md','state/focus.json']:
            destination=cls.base/'.octon/agent'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(old/'.octon/agent'/relative,destination)
        result=subprocess.run([sys.executable,'-B',cls.base/'.octon/runtime/scripts/refresh.py','--refresh'],cwd=cls.base,capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr)

    def setUp(self):
        self.area_case=tempfile.TemporaryDirectory(prefix='octon-admission-case-');self.addCleanup(self.area_case.cleanup)
        self.area_path=Path(self.area_case.name);self.root=self.area_path/'target';shutil.copytree(self.base,self.root)
        self.context_path=self.area_path/'context.json'
        self.env=mock.patch.dict(os.environ,{'OCTON_FIXTURE_ADMISSION_CONTEXT':str(self.context_path)})
        self.env.start();self.addCleanup(self.env.stop)
        # Planning is read-only and consumes no issuer permission.
        self.plan_path=self.area_path/'handoff.json'
        self.cli('work','handoff','--task-id','TASK-0001','--next-action','Continue admitted local work',
                 '--summary','Authenticated fixture handoff','--operator','fixture-operator','--output',self.plan_path)
        self.plan=R.load(self.plan_path)
        sys.path.insert(0,str(self.root/'.octon/runtime/scripts'))
        self.addCleanup(lambda:sys.path.remove(str(self.root/'.octon/runtime/scripts')))
        for name in ['octon_continuation','octon_doctor']:sys.modules.pop(name,None)
        self.tx=module(self.root/'.octon/runtime/scripts/octon_transaction.py','admission_transaction_case')
        self.refresh={'time':datetime.now(timezone.utc).isoformat(),'id':os.urandom(16).hex()}
        write(self.context_path,{'root':str(self.root.resolve()),'refresh':self.refresh})
        decoded=self.tx._decode_operations(self.plan)
        staged,_,_=self.tx._staged_result(self.root,self.plan,decoded)
        outcomes=self.tx._planned_outcomes(self.plan,decoded,staged)
        paths=self.tx._receipt_paths(self.root,self.plan,outcomes)
        created=self.tx._created_parent_directories(self.root,[row['path'] for row in paths])
        self.record={'receipt_id':self.plan['planned_receipt_id'],'operation':self.plan['operation'],
                     'plan_digest':self.plan['canonical_plan_digest'],'paths':paths,'created_directories':created}
        self.bound=A.binding(self.root,self.plan,self.record);self.bound['refresh']=self.refresh
        self.bundle=R.load(Q.SCRIPTS.parent/'fixtures/governance-shadow/covered-v2.json')
        now=datetime.now(timezone.utc);start=(now-timedelta(minutes=1)).isoformat();end=(now+timedelta(hours=1)).isoformat()
        self.bundle['evaluation_time']=now.isoformat()
        self.bundle['intent']['original_expression']='Qualify one bounded local fixture handoff.'
        self.bundle['intent']['interpretation']='This invocation permits synthetic fixture qualification only.'
        for grant in self.bundle['delegations']:
            grant['valid_from']=start;grant['valid_until']=end;grant['scope']['operations']=['work.handoff']
        action=self.bundle['action'];controls=self.bundle['controls']
        action.update(decision_class='work.local_handoff',operation='work.handoff',plan_digest=self.bound['plan_digest'],expected_state_digest=self.bound['expected_state_digest'],
                      policy_digest=self.bound['policy_digest'],work_contract_digest=self.bound['work_digest'])
        self.bundle['work_binding']['contract_digest']=self.bound['work_digest']
        controls.update(observed_at=start,fresh_until=end,state_digest=action['expected_state_digest'],policy_digest=action['policy_digest'])
        controls['policy_scope']['operations']=['work.handoff']
        controls['policy_scope']['decision_classes']=['work.local_handoff']
        for grant in self.bundle['delegations']:grant['scope']['decision_classes']=['work.local_handoff']
        for budget in controls['budget_snapshots']:budget['period_accounting'].update(start=start,end=end)
        for obligation in controls['obligation_results']:obligation.update(observed_at=start,fresh_until=end)
        seal(self.bundle)
        self.bound.update(intent_digest=self.bundle['intent']['digest'],issuer_ref=self.bundle['intent']['principal_ref'],delegation_refs=[G.delegation_reference(row) for row in self.bundle['delegations']],action_digest=self.bundle['action']['digest'])
        self.actor_private,actor_public=A.keypair(self.area_path,'actor')
        configuration=self.area_path/'controller.json'
        write(configuration,{'initial':{'bundle':self.bundle,'binding':self.bound,'allowed_phases':sorted(A.PHASES)},'actor_public':actor_public})
        self.controller=subprocess.Popen([sys.executable,'-I','-B',self.root/'.octon/runtime/fixture_admission.py','--fixture-controller',configuration],
                                         cwd=self.root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(self.stop_controller)
        line=self.controller.stdout.readline()
        if not line: raise ValueError('fixture controller unavailable: '+self.controller.stderr.read())
        initial=json.loads(line)
        self.context={'schema_version':A.CONTEXT,'fixture_authority':'current-user-disposable-admission-only','root':str(self.root.resolve()),
                      'issuer_public_key':initial['public_key'],'issuer_key_digest':hashlib.sha256(initial['public_key'].encode()).hexdigest(),
                      'actor_ref':action['actor_ref'],'actor_private_key':str(self.actor_private),'port':initial['port'],
                      'plan':self.plan,'record':self.record,'binding':self.bound,'refresh':self.refresh}
        write(self.context_path,self.context)
        self.original_task=(self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes()

    def stop_controller(self):
        if self.controller.poll() is None:
            self.controller.stdin.write('null\n');self.controller.stdin.flush()
            self.controller.communicate(timeout=15)

    def update(self,value):
        self.controller.stdin.write(json.dumps(value)+'\n');self.controller.stdin.flush()
        self.assertEqual(self.controller.stdout.readline().strip(),'true')

    def cli(self,*args,code=0):
        result=subprocess.run([sys.executable,'-I','-B',self.root/'octon',*map(str,args)],cwd=self.root,capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,code,result.stderr or result.stdout)
        return result

    def apply(self,code=0):
        return self.cli('transaction','apply','--plan',self.plan_path,'--accept-digest',self.plan['canonical_plan_digest'],code=code)

    def test_01_native_dependency_and_portable_paths_early(self):
        self.assertTrue(Path(A.openssl()).is_file())
        inspected=json.loads(self.cli('installation','inspect').stdout)
        self.assertEqual(inspected['schema_version'],V2.ADMISSION_SCHEMA)
        public=self.context['issuer_public_key']
        with self.assertRaises(ValueError):A.verify(public,{'altered':True},A.sign(self.actor_private,{'altered':True}))
        for path in ['../escape','C:/escape','.octon\\agent\\state','/absolute','.octon/CON.txt','x/..','x//z','x:stream','x./z']:
            with self.subTest(path=path),self.assertRaises(ValueError):R.confined(self.root,path)
        self.assertEqual(PureWindowsPath(r'.octon\agent\state').as_posix(),'.octon/agent/state')

    def test_02_actual_handoff_and_current_rollback_preserve_task(self):
        before=(self.root/'.octon/agent/state/focus.json').read_bytes()
        self.apply()
        self.assertIn('Continue admitted local work',(self.root/'.octon/agent/state/focus.json').read_text())
        receipt=self.root/'.octon/agent/transactions/receipts'/f"{self.plan['planned_receipt_id']}.json"
        saved=R.load(receipt);self.assertEqual(A.lineage(saved),A.lineage(self.record))
        evidence=saved['validation'][-1]
        self.assertEqual(evidence['schema_version'],'octon.fixture-admission-evidence.v1')
        for decision in evidence['decisions']:
            envelope=decision['signed_decision']
            A.verify(self.context['issuer_public_key'],envelope['response'],envelope['signature'])
            self.assertEqual(envelope['response']['binding']['lineage_digest'],A.digest(A.lineage(saved)))
        self.assertEqual((self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes(),self.original_task)
        self.cli('transaction','rollback','--receipt',receipt)
        self.assertEqual((self.root/'.octon/agent/state/focus.json').read_bytes(),before)
        self.assertEqual(R.load(receipt)['status'],'rolled_back')

    def test_03_authentication_wrong_actor_issuer_tampering_and_version(self):
        for key,value in [('actor_ref','agent:other'),('schema_version','unsupported'),('issuer_public_key',self.context['issuer_public_key'].replace('A','B',1)),('fixture_authority','real-grant')]:
            changed=copy.deepcopy(self.context);changed[key]=value;write(self.context_path,changed)
            self.apply(code=2)
        other,_=A.keypair(self.area_path,'wrong-actor');changed=copy.deepcopy(self.context);changed['actor_private_key']=str(other)
        write(self.context_path,changed);self.apply(code=2)
        _,wrong_issuer_public=A.keypair(self.area_path,'wrong-issuer')
        changed=copy.deepcopy(self.context);changed['issuer_public_key']=wrong_issuer_public;changed['issuer_key_digest']=hashlib.sha256(wrong_issuer_public.encode()).hexdigest()
        write(self.context_path,changed);self.apply(code=2)
        write(self.context_path,self.context)
        with mock.patch.object(A,'current_time',return_value=datetime.now(timezone.utc)+timedelta(hours=2)):
            with self.assertRaisesRegex(ValueError,'decision expired'):A.guarded(self.root,self.plan,'prepare')
        with mock.patch.object(A,'verify',side_effect=ValueError('tampered response')):
            with self.assertRaises(ValueError):A.guarded(self.root,self.plan,'prepare')

    def test_03a_signed_request_tamper_and_nonce_replay_refuse(self):
        import socket
        def query(envelope):
            with socket.create_connection(('127.0.0.1',self.context['port']),timeout=10) as connection:
                connection.sendall(A.canonical(envelope))
                with connection.makefile('rb') as stream:return A.strict(stream.readline(A.MAX+1))
        request={'schema_version':A.SCHEMA,'nonce':'a'*64,'actor_ref':self.context['actor_ref'],'phase':'prepare','binding':self.bound}
        envelope={'request':request,'signature':A.sign(self.actor_private,request)}
        first=query(envelope);self.assertTrue(first['response']['admitted'])
        self.assertIn('error',query(envelope))
        changed=copy.deepcopy(envelope);changed['request']['nonce']='b'*64
        self.assertIn('error',query(changed))
        with socket.create_connection(('127.0.0.1',self.context['port']),timeout=10) as partial:
            partial.sendall(b'{')
            self.update(self.bundle)
        A.verify(self.context['issuer_public_key'],first['response'],first['signature'])
        first['response']['binding']['source_revision']='0'*40
        with self.assertRaises(ValueError):A.verify(self.context['issuer_public_key'],first['response'],first['signature'])

    def test_04_narrowing_current_controls_and_obligations_matrix(self):
        cases=[('issuer',lambda v:v['delegations'][0].update(issuer_ref='principal:other')),
               ('actor',lambda v:v['action'].update(actor_ref='agent:other')),
               ('scope',lambda v:v['delegations'][1]['scope']['resources'].append('resource:extra')),
               ('duration',lambda v:v['delegations'][1].update(valid_until='2100-01-01T00:00:00Z')),
               ('limit',lambda v:v['delegations'][1]['period_limits'].update(actions=100)),
               ('obligations',lambda v:v['delegations'][1].update(required_obligations=[])),
               ('intent',lambda v:v['action']['intent_ref'].update(revision=999)),
               ('expired',lambda v:v['delegations'][1].update(valid_until='2000-01-01T00:00:00Z')),
               ('revoked',lambda v:v['controls']['revoked_delegation_ids'].append(v['delegations'][0]['id'])),
               ('stop',lambda v:v['controls'].update(emergency_stop=True)),
               ('stale',lambda v:v['controls'].update(fresh_until='2000-01-01T00:00:00Z')),
               ('accounting',lambda v:v['controls'].update(accounting_observation='unknown')),
               ('required evidence',lambda v:v['controls']['obligation_results'][0].update(outcome='unknown')),
               ('qualified human',lambda v:v['controls'].update(qualified_human_obligations=['obligation:tests'])),
               ('wrong plan',lambda v:v['action'].update(plan_digest='0'*64)),
               ('wrong action',lambda v:v['action'].update(operation='work.start')),
               ('wrong source',lambda v:v['action'].update(work_contract_digest='0'*64)),
               ('state',lambda v:v['controls'].update(state_digest='0'*64)),
               ('policy',lambda v:v['controls'].update(policy_digest='0'*64)),
               ('epoch',lambda v:v['controls'].update(authority_epoch=2)),
               ('unsupported',lambda v:v.update(schema_version='unsupported'))]
        for label,mutate in cases:
            with self.subTest(case=label):
                value=copy.deepcopy(self.bundle);mutate(value)
                if label!='intent':seal(value)
                else:value['action']['digest']=G.record_digest(value['action']);value['controls']['digest']=G.record_digest(value['controls'])
                self.update(value);self.apply(code=2)
        self.update(self.bundle)

    def test_05_exact_plan_source_action_expected_state_and_verifier_bindings(self):
        before=snapshot(self.root)
        for part in ['plan','source','action','expected','verifier','control','validation']:
            with self.subTest(part=part):
                if part in {'source','action'}:
                    context=copy.deepcopy(self.context);context['binding']['source_revision' if part=='source' else 'operation']='f'*40 if part=='source' else 'work.start'
                    write(self.context_path,context);self.apply(code=2);write(self.context_path,self.context)
                elif part in {'plan','validation'}:
                    plan=copy.deepcopy(self.plan)
                    if part=='validation':plan['validation']['post_apply_argv']=[[sys.executable,'-c','print("forged")']]
                    else:plan['operations'][0]['path']='.octon/agent/policy.json'
                    plan['canonical_plan_digest']=self.tx.plan_digest(plan);write(self.plan_path,plan)
                    self.cli('transaction','apply','--plan',self.plan_path,'--accept-digest',plan['canonical_plan_digest'],code=2);write(self.plan_path,self.plan)
                else:
                    path=self.root/('.octon/agent/state/focus.json' if part=='expected' else '.octon/agent/policy.json' if part=='control' else '.octon/runtime/scripts/validate.py')
                    data=path.read_bytes();path.write_bytes(data+b'\n');self.apply(code=2);path.write_bytes(data)
        self.assertEqual(before,snapshot(self.root))

    def test_06_interruption_before_effect_and_after_effect_revalidates_recovery(self):
        # Existing transaction stages and journals exact paths before effects.
        decoded=self.tx._decode_operations(self.plan)
        pending,pending_path=self.tx._write_pending(self.root,self.plan['planned_receipt_id'],self.plan,self.record['paths'],self.record['created_directories'])
        self.tx._apply_static(self.root,self.plan,decoded)
        revoked=copy.deepcopy(self.bundle);revoked['controls']['revoked_delegation_ids'].append(revoked['delegations'][0]['id']);seal(revoked);self.update(revoked)
        before=snapshot(self.root);self.cli('transaction','recover','--pending',pending_path,code=2);self.assertEqual(before,snapshot(self.root))
        self.update(self.bundle)
        self.cli('transaction','recover','--pending',pending_path)
        recovered=self.root/'.octon/agent/transactions/recovered'/pending_path.name
        self.assertEqual(A.lineage(R.load(recovered)),A.lineage(self.record));self.assertFalse(pending_path.exists())
        observations=list((self.root/'.octon/agent/transactions/evidence'/self.record['receipt_id']).glob('*.json'))
        self.assertTrue(any(R.load(path)['phase']=='recover' for path in observations))
        for path in observations:
            event=R.load(path);A.validate_observation(event,self.record['receipt_id']);A.validate_evidence(self.context,event['admission_evidence'],self.bound)
        self.apply(code=2)  # recovered transaction identity cannot replay
        # Original task/intent IDs and history survive recovery; no old grant revived.
        self.assertEqual((self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes(),self.original_task)

    def test_07_revocation_between_admission_and_effect_implicit_restore_refuses(self):
        self.tx.qualification_current(self.root,self.plan,'prepare')
        stopped=copy.deepcopy(self.bundle);stopped['controls']['emergency_stop']=True;seal(stopped);self.update(stopped)
        with self.assertRaises(self.tx.TransactionError):self.tx.apply_plan(self.root,self.plan,self.plan['canonical_plan_digest'])
        self.update(self.bundle)
        pending,pending_path=self.tx._write_pending(self.root,self.plan['planned_receipt_id'],self.plan,self.record['paths'],self.record['created_directories'])
        self.tx._apply_static(self.root,self.plan,self.tx._decode_operations(self.plan))
        self.update(stopped)
        with self.assertRaises(self.tx.TransactionError):self.tx._restore(self.root,self.record['paths'],self.record['created_directories'])
        self.assertTrue(pending_path.exists())
        self.update(self.bundle);self.cli('transaction','recover','--pending',pending_path)

    def test_07a_changes_during_staging_refuse_before_first_effect(self):
        original=self.tx._staged_result
        focus=self.root/'.octon/agent/state/focus.json';before=focus.read_bytes()
        import base64
        postimage=base64.b64decode(self.plan['operations'][0]['content_base64'])
        for change in ['stop','arbitrary_state','exact_postimage','nested_instruction']:
            with self.subTest(change=change):
                nested=self.root/'fixture-instructions/AGENTS.md'
                def staged(*args):
                    value=original(*args)
                    if change=='stop':
                        bundle=copy.deepcopy(self.bundle);bundle['controls']['emergency_stop']=True;seal(bundle);self.update(bundle)
                    elif change=='nested_instruction':
                        nested.parent.mkdir(exist_ok=True);nested.write_text('New fixture instruction after planning.\n')
                    else:focus.write_bytes(postimage if change=='exact_postimage' else before+b'Independent state change\n')
                    return value
                with mock.patch.object(self.tx,'_staged_result',staged):
                    with self.assertRaises(self.tx.TransactionError):self.tx.apply_plan(self.root,self.plan,self.plan['canonical_plan_digest'])
                pending=self.root/'.octon/agent/transactions/pending'/f"{self.record['receipt_id']}.json"
                self.assertFalse(pending.exists())
                focus.write_bytes(before)
                if nested.exists():nested.unlink();nested.parent.rmdir()
                self.update(self.bundle)
        self.assertEqual((self.root/'.octon/agent/tasks/TASK-0001.md').read_bytes(),self.original_task)

    def test_08_forged_recovery_and_changed_lineage_refuse(self):
        pending,path=self.tx._write_pending(self.root,self.plan['planned_receipt_id'],self.plan,self.record['paths'],self.record['created_directories'])
        for part in ['path','preimage','directory','receipt_id']:
            forged=copy.deepcopy(pending)
            if part=='path':forged['paths'][0]['path']='.octon/agent/policy.json'
            elif part=='preimage':forged['paths'][0]['before_content_base64']='Zm9yZ2Vk'
            elif part=='directory':forged['created_directories']=['.octon/runtime']
            else:forged['receipt_id']='forged'
            write(path,forged);self.cli('transaction','recover','--pending',path,code=2)
        write(path,pending);self.cli('transaction','recover','--pending',path)

    def test_09a_actual_apply_interrupts_before_effects_and_before_receipt(self):
        pending=self.root/'.octon/agent/transactions/pending'/f"{self.plan['planned_receipt_id']}.json"
        original=self.tx._write_pending
        def interrupted(*args):
            value=original(*args)
            raise KeyboardInterrupt('controlled journal-before-effect interruption')
        before=(self.root/'.octon/agent/state/focus.json').read_bytes()
        with mock.patch.object(self.tx,'_write_pending',interrupted):
            with self.assertRaises(KeyboardInterrupt):self.tx.apply_plan(self.root,self.plan,self.plan['canonical_plan_digest'])
        self.assertEqual((self.root/'.octon/agent/state/focus.json').read_bytes(),before)
        self.assertTrue(pending.exists())
        self.cli('transaction','recover','--pending',pending)
        # Recovery creates immutable history, so a new exact plan/fixture is required.
        self.assertTrue((self.root/'.octon/agent/transactions/recovered'/pending.name).exists())
        before=snapshot(self.root);self.apply(code=2);self.assertEqual(before,snapshot(self.root))

    def test_09b_post_effect_pre_receipt_stop_keeps_unknown_journal(self):
        original=self.tx.write_new_json
        stopped=copy.deepcopy(self.bundle);stopped['controls']['emergency_stop']=True;seal(stopped)
        def interrupted(path,value):
            if '/receipts/' in path.as_posix():
                self.update(stopped)
                raise KeyboardInterrupt('controlled post-effect/pre-receipt interruption')
            return original(path,value)
        with mock.patch.object(self.tx,'write_new_json',interrupted):
            with self.assertRaises(self.tx.TransactionError) as caught:
                self.tx.apply_plan(self.root,self.plan,self.plan['canonical_plan_digest'])
        self.assertTrue(caught.exception.report['mutation']['occurred'])
        self.assertIn('journal remains',caught.exception.report['mutation']['statement'])
        pending=self.root/'.octon/agent/transactions/pending'/f"{self.plan['planned_receipt_id']}.json"
        self.assertTrue(pending.exists())
        for row in self.record['paths']:self.assertEqual(self.tx.path_state(self.root,row['path']),row['after'])
        self.apply(code=2)  # unresolved attempted transaction cannot replay
        self.cli('transaction','recover','--pending',pending,code=2)
        self.update(self.bundle);self.cli('transaction','recover','--pending',pending)
        for row in self.record['paths']:self.assertEqual(self.tx.path_state(self.root,row['path']),row['before'])

    def test_08a_receipt_provenance_tampering_and_forged_helper_paths_refuse(self):
        self.apply()
        receipt=self.root/'.octon/agent/transactions/receipts'/f"{self.plan['planned_receipt_id']}.json"
        original=receipt.read_bytes();value=R.load(receipt)
        value['validation'][-1]['decisions'][0]['signed_decision']['response']['admitted']=False
        write(receipt,value);self.cli('transaction','rollback','--receipt',receipt,code=2)
        receipt.write_bytes(original)
        event_path=next((self.root/'.octon/agent/transactions/evidence'/self.record['receipt_id']).glob('*.json'))
        event_bytes=event_path.read_bytes();event=R.load(event_path)
        event['admission_evidence']['signed_decision']['response']['issuer_ref']='principal:forged'
        forged_event=event_path.parent/(A.digest(event)+'.json');write(forged_event,event);event_path.unlink()
        self.cli('transaction','rollback','--receipt',receipt,code=2)
        forged_event.unlink();event_path.write_bytes(event_bytes)
        for relative in ['.octon/agent/policy.json','.octon/agent/transactions/receipts/forged.json']:
            with self.subTest(path=relative),self.assertRaises(self.tx.TransactionError):self.tx._atomic_write(self.root/relative,b'{}',0o600)
        focus=self.root/'.octon/agent/state/focus.json'
        with self.assertRaises(self.tx.TransactionError):self.tx._atomic_write(focus,focus.read_bytes(),0o444)
        self.cli('transaction','rollback','--receipt',receipt)

    def test_08b_authentic_denial_and_prepare_only_receipt_provenance_refuse(self):
        import socket
        self.apply()
        receipt=self.root/'.octon/agent/transactions/receipts'/f"{self.plan['planned_receipt_id']}.json"
        original=receipt.read_bytes();value=R.load(receipt)
        prepare=next(row for row in value['validation'][-1]['decisions'] if row['signed_decision']['response']['phase']=='prepare')
        value['validation'][-1]['decisions']=[prepare];write(receipt,value)
        self.cli('transaction','rollback','--receipt',receipt,code=2)
        receipt.write_bytes(original)
        stopped=copy.deepcopy(self.bundle);stopped['controls']['emergency_stop']=True;seal(stopped);self.update(stopped)
        request={'schema_version':A.SCHEMA,'nonce':os.urandom(32).hex(),'actor_ref':self.context['actor_ref'],'phase':'rollback','binding':self.bound}
        envelope={'request':request,'signature':A.sign(self.actor_private,request)}
        with socket.create_connection(('127.0.0.1',self.context['port']),timeout=10) as connection:
            connection.sendall(A.canonical(envelope))
            with connection.makefile('rb') as stream:denial=A.strict(stream.readline(A.MAX+1))
        self.assertFalse(denial['response']['admitted']);A.verify(self.context['issuer_public_key'],denial['response'],denial['signature'])
        self.update(self.bundle)
        value=R.load(receipt);value['validation'][-1]['decisions']=[{'schema_version':'octon.fixture-admission-evidence.v1','fixture_only':True,'issuer_key_digest':self.context['issuer_key_digest'],'signed_decision':denial}]
        write(receipt,value);before=snapshot(self.root);self.cli('transaction','rollback','--receipt',receipt,code=2);self.assertEqual(before,snapshot(self.root))
        receipt.write_bytes(original);self.cli('transaction','rollback','--receipt',receipt)
        events=[R.load(path) for path in (self.root/'.octon/agent/transactions/evidence'/self.record['receipt_id']).glob('*.json')]
        self.assertTrue(any(event['phase']=='rollback' for event in events))
        self.assertTrue(any(event['phase']=='recover' for event in events))

    def test_09_missing_context_shadow_only_and_legacy_disposition(self):
        with mock.patch.dict(os.environ,{'OCTON_FIXTURE_ADMISSION_CONTEXT':''}):self.apply(code=2)
        self.assertFalse(G.evaluate(self.bundle)['execution_authorized'])
        manifest=R.load(self.root/'.octon/manifest.json');self.assertEqual(manifest['schema_version'],V2.ADMISSION_SCHEMA)
        # No active consumer version/DEC/grant migration or implicit legacy generalization.
        self.assertEqual(R.load(self.root/'.octon/agent/project.json')['autonomous_delivery']['status'],'available_not_activated')
        self.assertFalse((self.root/'.octon/agent/capabilities').exists())

if __name__=='__main__':unittest.main(verbosity=2)
