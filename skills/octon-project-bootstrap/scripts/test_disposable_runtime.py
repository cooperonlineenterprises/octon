#!/usr/bin/env python3
"""Real target runtime, strict dependencies, work/recovery and exact fixture conversion."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import installation_runtime as reader
import qualify_disposable_runtime as qualifier
import scaffold_project as scaffold
import upgrade_project as upgrade
import test_identity_transition as identity


def snapshot(root):
    return {p.relative_to(root).as_posix():reader.digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def write(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class DisposableRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.area=tempfile.TemporaryDirectory(prefix='octon-disposable-suite-')
        cls.base=Path(cls.area.name)/'base'
        qualifier.generate(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.area.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='octon-disposable-case-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'target'
        shutil.copytree(self.base,self.root)

    def cli(self,*args,code=0):
        result=subprocess.run([sys.executable,'-I','-B',self.root/'octon',*args],cwd=self.root,capture_output=True,text=True,
                              env={**os.environ,'PYTHONPATH':'','PYTHONDONTWRITEBYTECODE':'1'},check=False)
        self.assertEqual(result.returncode,code,result.stderr or result.stdout)
        return result

    def plan(self,name='start'):
        path=Path(self.temp.name)/(name+'.json')
        self.cli('work','start','--title','Disposable existing work owner','--scope','Prove local lifecycle',
                 '--authority-basis','authority:current-user-bounded-disposable-fixture','--owner','fixture-owner',
                 '--operator','fixture-operator','--acceptance','Actual target state, recovery and rollback observed',
                 '--validation','Read-only target check','--next-action','Exercise recovery','--output',path)
        return path,reader.load(path)

    def apply(self,path,plan,**kwargs):
        return self.cli('transaction','apply','--plan',path,'--accept-digest',plan['canonical_plan_digest'],**kwargs)

    def engine(self):
        sys.path.insert(0,str(self.root/'.octon/runtime/scripts'))
        self.addCleanup(lambda:sys.path.remove(str(self.root/'.octon/runtime/scripts')))
        # Each case needs its own ROOT; do not retain a previous dispatcher import.
        for name in ['octon_continuation','octon_doctor']:
            sys.modules.pop(name,None)
        return module(self.root/'.octon/runtime/scripts/octon_transaction.py','disposable_case_transaction')

    def test_independent_actual_target_check_readonly_optional_absence(self):
        self.assertTrue(all('\\' not in item['path'] for item in reader.load(self.root/'.octon/manifest.json')['inputs']))
        self.assertFalse((self.root/'.agent').exists())
        self.assertFalse((self.root/'project-dossier').exists())
        self.assertFalse((self.root/'.octon/agent/capabilities').exists())
        before=snapshot(self.root)
        result=self.cli('installation','inspect')
        self.assertFalse(json.loads(result.stdout)['execution_authority'])
        self.cli('check')
        self.cli('work','resume')
        self.assertEqual(before,snapshot(self.root))
        self.assertFalse(list(self.root.rglob('__pycache__')))

    def test_manifest_versions_paths_dependencies_assets_refuse(self):
        path=self.root/'.octon/manifest.json';original=path.read_bytes()
        for key,value in [('schema_version','unknown'),('required_dependencies',['unknown']),('permission_grant',True)]:
            data=json.loads(original);data[key]=value;write(path,data)
            self.cli('check',code=2)
        path.write_bytes(original)
        data=reader.load(path);data['assets'][0]['path']='../escape';write(path,data)
        self.cli('check',code=2);path.write_bytes(original)
        asset=self.root/'.octon/runtime/scripts/validate.py';content=asset.read_bytes();asset.write_bytes(content+b'\n')
        self.cli('check',code=2);asset.write_bytes(content);asset.unlink()
        self.cli('check',code=2)

    def test_unknown_equal_dependencies_and_runtime_inventory_refuse(self):
        path=self.root/'.octon/runtime/profile-inventory.json';data=reader.load(path)
        data['disposable_runtime']['required_dependencies']=['unknown-required']
        write(path,data)
        manifest=self.root/'.octon/manifest.json';data2=reader.load(manifest)
        data2['inventory_sha256']=reader.digest(path.read_bytes());data2['required_dependencies']=['unknown-required'];write(manifest,data2)
        self.cli('check',code=2)

    def test_real_task_apply_stale_control_verifier_scope_refusals(self):
        path,plan=self.plan()
        policy=self.root/'.octon/agent/policy.json';before=policy.read_bytes();policy.write_bytes(before+b'\n')
        self.apply(path,plan,code=2);policy.write_bytes(before)
        verifier=self.root/'.octon/runtime/scripts/validate.py';verifier_bytes=verifier.read_bytes()
        manifest=self.root/'.octon/manifest.json';manifest_bytes=manifest.read_bytes()
        verifier.write_bytes(verifier_bytes+b'\n# independently changed verifier\n')
        changed=reader.load(manifest)
        for binding in changed['assets']:
            if binding['path']=='.octon/runtime/scripts/validate.py':binding['sha256']=reader.digest(verifier.read_bytes())
        write(manifest,changed)
        reader.inspect(self.root)
        self.apply(path,plan,code=2)
        verifier.write_bytes(verifier_bytes);manifest.write_bytes(manifest_bytes)
        schema=self.root/'.octon/agent/schemas/harness-record.schema.json'
        schema_bytes=schema.read_bytes();schema.write_bytes(schema_bytes+b'\n')
        changed=reader.load(manifest)
        for binding in changed['assets']:
            if binding['path']=='.octon/agent/schemas/harness-record.schema.json':binding['sha256']=reader.digest(schema.read_bytes())
        write(manifest,changed);reader.inspect(self.root)
        self.apply(path,plan,code=2)
        schema.write_bytes(schema_bytes);manifest.write_bytes(manifest_bytes)
        transaction=self.engine()
        for effect in ['static','derived','argv','alias']:
            forged=copy.deepcopy(plan)
            if effect=='static' or effect=='alias':
                forged['operations'][0]['path']='.octon/agent/policy.json'
            elif effect=='derived':
                forged['validation']['declared_write_paths'].append('.octon/runtime/scripts/validate.py')
            else:
                forged['validation']['staged_argv']=[[sys.executable,'-c','print("forged")']]
            forged['canonical_plan_digest']=transaction.plan_digest(forged);write(path,forged)
            if effect=='alias':
                self.cli('work','start','--apply-plan',path,'--accept-digest',forged['canonical_plan_digest'],code=2)
            else:
                self.apply(path,forged,code=2)
        write(path,plan);self.apply(path,plan)
        task=(self.root/'.octon/agent/tasks/TASK-0001.md').read_text()
        self.assertIn('"status": "in_progress"',task)
        block_path=Path(self.temp.name)/'block.json'
        self.cli('work','block','TASK-0001','--reason','Unstructured cause alone cannot block','--output',block_path)
        block=reader.load(block_path);self.apply(block_path,block,code=2)
        handoff_path=Path(self.temp.name)/'handoff.json'
        self.cli('work','handoff','--task-id','TASK-0001','--next-action','Continue after bounded handoff',
                 '--summary','Actual existing-task handoff transition','--operator','fixture-operator','--output',handoff_path)
        handoff=reader.load(handoff_path);self.apply(handoff_path,handoff)
        self.assertIn('Continue after bounded handoff',(self.root/'.octon/agent/state/focus.json').read_text())
        handoff_receipt=self.root/'.octon/agent/transactions/receipts'/f"{handoff['planned_receipt_id']}.json"
        self.cli('transaction','rollback','--receipt',handoff_receipt)
        self.assertIn('"status": "in_progress"',(self.root/'.octon/agent/tasks/TASK-0001.md').read_text())
        receipt=self.root/'.octon/agent/transactions/receipts'/f"{plan['planned_receipt_id']}.json"
        self.cli('transaction','rollback','--receipt',receipt)
        self.assertFalse((self.root/'.octon/agent/tasks/TASK-0001.md').exists())
        self.assertEqual(reader.load(receipt)['status'],'rolled_back')

    def test_pending_partial_write_unknown_local_reconcile_and_divergence(self):
        path,plan=self.plan();transaction=self.engine()
        decoded=transaction._decode_operations(plan)
        derived,_,_=transaction._staged_result(self.root,plan,decoded)
        outcomes=transaction._planned_outcomes(plan,decoded,derived)
        receipt_paths=transaction._receipt_paths(self.root,plan,outcomes)
        created=transaction._created_parent_directories(self.root,[item['path'] for item in receipt_paths])
        pending,pending_path=transaction._write_pending(self.root,plan['planned_receipt_id'],plan,receipt_paths,created)
        # Process stops after durable pending journal and one local effect, before receipt.
        first=copy.deepcopy(plan);first['operations']=first['operations'][:1]
        transaction._apply_static(self.root,first,decoded)
        task=self.root/'.octon/agent/tasks/TASK-0001.md';content=task.read_bytes();task.write_bytes(content+b'Independent edit\n')
        self.cli('transaction','recover','--pending',pending_path,code=2)
        task.write_bytes(content)
        self.cli('transaction','recover','--pending',pending_path)
        self.assertFalse(task.exists());self.assertFalse(pending_path.exists())
        recovered=self.root/'.octon/agent/transactions/recovered'/pending_path.name
        self.assertTrue(recovered.is_file());self.assertEqual(reader.load(recovered)['plan_digest'],plan['canonical_plan_digest'])

    def test_recovery_and_rollback_refuse_forged_control_scope(self):
        path,plan=self.plan();transaction=self.engine()
        decoded=transaction._decode_operations(plan)
        derived,_,_=transaction._staged_result(self.root,plan,decoded)
        outcomes=transaction._planned_outcomes(plan,decoded,derived)
        receipt_paths=transaction._receipt_paths(self.root,plan,outcomes)
        created=transaction._created_parent_directories(self.root,[item['path'] for item in receipt_paths])
        pending,pending_path=transaction._write_pending(self.root,plan['planned_receipt_id'],plan,receipt_paths,created)
        policy=transaction.path_state(self.root,'.octon/agent/policy.json')
        forged=copy.deepcopy(pending);forged['paths'][0]['path']=policy['path']
        forged['paths'][0]['before']=policy;forged['paths'][0]['after']=policy
        write(pending_path,forged);before=snapshot(self.root)
        self.cli('transaction','recover','--pending',pending_path,code=2)
        self.assertEqual(before,snapshot(self.root))
        forged=copy.deepcopy(pending);forged['created_directories']=['.octon/runtime']
        write(pending_path,forged);before=snapshot(self.root)
        self.cli('transaction','recover','--pending',pending_path,code=2)
        self.assertEqual(before,snapshot(self.root))
        write(pending_path,pending);self.cli('transaction','recover','--pending',pending_path)
        # A fresh exact plan follows reconciliation, with original history retained.
        path,plan=self.plan('start-after-reconciliation');self.apply(path,plan)
        receipt=self.root/'.octon/agent/transactions/receipts'/f"{plan['planned_receipt_id']}.json"
        original=receipt.read_bytes();forged=reader.load(receipt)
        forged['paths'][0]['path']=policy['path'];forged['paths'][0]['before']=policy;forged['paths'][0]['after']=policy
        write(receipt,forged);before=snapshot(self.root)
        self.cli('transaction','rollback','--receipt',receipt,code=2)
        self.assertEqual(before,snapshot(self.root));receipt.write_bytes(original)
        self.cli('transaction','rollback','--receipt',receipt)

    def test_post_receipt_finalization_and_interrupted_rollback(self):
        path,plan=self.plan();transaction=self.engine()
        pending=self.root/'.octon/agent/transactions/pending'/f"{plan['planned_receipt_id']}.json"
        unlink=Path.unlink
        def stop(path,*args,**kwargs):
            if path.resolve()==pending.resolve():
                raise KeyboardInterrupt('controlled post-receipt interruption')
            return unlink(path,*args,**kwargs)
        with mock.patch.object(Path,'unlink',stop):
            with self.assertRaises(KeyboardInterrupt):
                transaction.apply_plan(self.root,plan,plan['canonical_plan_digest'])
        self.cli('transaction','recover','--pending',pending)
        receipt=self.root/'.octon/agent/transactions/receipts'/pending.name
        restore=transaction._restore
        def stop_restore(root,paths,created):
            restore(root,paths[:1],[])
            raise KeyboardInterrupt('controlled partial rollback')
        with mock.patch.object(transaction,'_restore',stop_restore):
            with self.assertRaises(KeyboardInterrupt):
                transaction.rollback(self.root,receipt)
        self.assertEqual(reader.load(receipt)['status'],'rollback_in_progress')
        self.cli('transaction','rollback','--receipt',receipt)
        self.assertFalse((self.root/'.octon/agent/tasks/TASK-0001.md').exists())

    def test_host_mode_binding_preserves_windows_readonly_boundary(self):
        self.assertEqual(qualifier.supported_mode(0o666,'nt'),qualifier.supported_mode(0o600,'nt'))
        self.assertNotEqual(qualifier.supported_mode(0o666,'nt'),qualifier.supported_mode(0o444,'nt'))
        self.assertNotEqual(qualifier.supported_mode(0o600,'posix'),qualifier.supported_mode(0o644,'posix'))
        with self.assertRaises(ValueError):reader.confined(self.root,r'.octon\agent\policy.json')
        self.assertEqual(qualifier.project_path(PureWindowsPath(r'.agent\decisions\DEC-0042-long-running-work.md').as_posix()),
                         '.octon/agent/decisions/DEC-0042-long-running-work.md')

    def test_profile_v2_schema_preserved_and_mixed_versions_refuse(self):
        prior=json.loads(subprocess.check_output(['git','show','8871095f51a02e12a569d9260a51d0ff55fc1eef:shared/source-contracts/profile-manifest.json'],cwd=qualifier.ROOT,text=True))
        current=scaffold.load_generation_policy()
        self.assertEqual(prior['rules'],current['rules'])
        self.assertEqual(prior['installation_bindings'],current['installation_bindings'])
        for bad in [dict(current,schema_version='octon-mini.source.profile-manifest.v2'),dict(prior,disposable_runtime=current['disposable_runtime'])]:
            with mock.patch.object(scaffold,'load_json',return_value=bad),self.assertRaises(ValueError):
                scaffold.load_generation_policy()
        with mock.patch.object(scaffold,'load_json',return_value=prior):
            self.assertEqual(scaffold.load_generation_policy(),prior)


class FixtureConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        identity.IdentityTransitionTests.setUpClass()
        cls.addClassCleanup(identity.IdentityTransitionTests.tearDownClass)
        cls.area=tempfile.TemporaryDirectory(prefix='octon-disposable-conversion-')
        cls.addClassCleanup(cls.area.cleanup)
        cls.root=Path(cls.area.name)/'predecessor'
        case=identity.IdentityTransitionTests('test_published_schemas_unchanged')
        case.generate(cls.root,old=True)
        cls.records={Path(path).as_posix():data for path,data in case.project_records(cls.root).items()}
        cls.old_origin=(cls.root/'.octon-mini-origin.json').read_bytes()
        cls.old_only=Path(cls.area.name)/'old-only'
        shutil.copytree(cls.root,cls.old_only)
        path,plan=case.plan(cls.root,Path(cls.area.name));case.apply(cls.root,path,plan)

    def test_exact_supported_conversion_preserves_history_interrupts_and_rollback(self):
        target=Path(self.area.name)/'convert';shutil.copytree(self.root,target)
        before=snapshot(target)
        plan=qualifier.fixture_conversion_plan(target)
        tx=upgrade.TRANSACTION
        decoded=tx._decode_operations(plan)
        derived,_,_=tx._staged_result(target,plan,decoded)
        outcomes=tx._planned_outcomes(plan,decoded,derived)
        receipt_paths=tx._receipt_paths(target,plan,outcomes)
        created=tx._created_parent_directories(target,[x['path'] for x in receipt_paths])
        pending,pending_path=tx._write_pending(target,plan['planned_receipt_id'],plan,receipt_paths,created)
        tx._apply_static(target,dict(plan,operations=plan['operations'][:1]),decoded)
        tx.recover_pending(target,pending_path)
        self.assertEqual(before,{k:v for k,v in snapshot(target).items() if k in before})
        # Recovery history persists, so derive a fresh exact plan before retry.
        plan=qualifier.fixture_conversion_plan(target)
        receipt,receipt_path=tx.apply_plan(target,plan,plan['canonical_plan_digest'])
        for value,data in self.records.items():
            if value == 'project-dossier/machine-readable/artifact-registry.json':
                projected=json.loads(data)
                for representation in projected['representations']:
                    representation['path']=qualifier.project_path(representation['path'])
                self.assertEqual(reader.load(target/qualifier.project_path(value)),projected)
            else:
                self.assertEqual((target/qualifier.project_path(value)).read_bytes(),data,value)
        for value,digest in before.items():
            self.assertEqual(reader.digest((target/'.octon/archive/predecessor'/value).read_bytes()),digest,value)
        result=subprocess.run([sys.executable,'-I','-B',target/'octon','check'],cwd=target,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((target/'.agent/state').exists() and any((target/'.agent/state').iterdir()))
        tx.rollback(target,receipt_path)
        self.assertEqual(before,{k:v for k,v in snapshot(target).items() if k in before})
        self.assertEqual(reader.load(receipt_path)['status'],'rolled_back')

    def test_proposal_reconstruction_crosses_date_and_stale_subject_refuses(self):
        import argparse
        target=Path(self.area.name)/'date-boundary';shutil.copytree(self.old_only,target)
        proposal_path=Path(self.area.name)/'date-proposal.json'
        args=argparse.Namespace(target=target,project_blueprint_seed=None,output=proposal_path,
            setup_session=None,authority_source='authority:current-user-bounded-disposable-fixture',
            evidence_ref=['EVD-0001'],prior_plan=None,proposal=None,review=None,json=False)
        with mock.patch.object(upgrade.TRANSACTION,'utc_timestamp',return_value='2026-09-30T23:59:59Z'):
            self.assertEqual(upgrade.plan_command(args),3)
        proposal=reader.load(proposal_path);decisions=[]
        for row in proposal['classifications']:
            if row['automatic']:continue
            choices=row['allowed_dispositions']
            if row['path']=='.agent/project.json':choice='merge_version_only'
            elif row['path']=='.octon-mini-origin.json':choice='delete'
            elif row['path']=='project-dossier/machine-readable/artifact-registry.json':choice='preserve_current'
            elif row['classification']=='project_modified' and row['current']['sha256']!=(row['old_baseline'] or {}).get('sha256'):choice='preserve_current'
            else:choice='accept_candidate' if 'accept_candidate' in choices else 'preserve_current'
            decisions.append({'id':row['id'],'disposition':choice,'rationale':'Exact bounded fixture review.'})
        review=Path(self.area.name)/'date-review.json'
        write(review,{'schema_version':'octon.bootstrap.upgrade-review.v1','permission_grant':False,
                      'proposal_digest':proposal['canonical_proposal_digest'],'dispositions':decisions,
                      'limitations':['Disposable date reconstruction only.']})
        args.proposal=proposal_path;args.review=review;args.output=Path(self.area.name)/'date-plan.json'
        with mock.patch.object(upgrade.TRANSACTION,'utc_timestamp',return_value='2026-10-01T00:00:01Z'):
            self.assertEqual(upgrade.plan_command(args),0)
        plan=reader.load(args.output)
        self.assertEqual(plan['operation'],'upgrade.project')
        instructions=target/'AGENTS.md';instructions.write_bytes(instructions.read_bytes()+b'Changed after review\n')
        with self.assertRaises(upgrade.UpgradeError):upgrade.plan_command(args)

    def test_collision_mixed_unsupported_pending_and_custom_controls_refuse(self):
        for case in ['collision','case-collision','mixed','unsupported','pending','unknown-effect','git','extra-app','mode','known-gate','known-evidence','known-schema','known-implementation','control']:
            target=Path(self.area.name)/case;shutil.copytree(self.root,target)
            if case=='collision':(target/'.octon').mkdir()
            elif case=='case-collision':(target/'.OCTON').mkdir()
            elif case=='extra-app':(target/'app.py').write_text('project-owned implementation\n')
            elif case=='known-gate':
                path=target/'project-dossier/validation/QUALITY_GATES.json';value=reader.load(path)
                value['gates'][0]['title']='Project-owned qualification gate title'
                write(path,value)
            elif case=='known-evidence':
                path=target/'.agent/project-checks/evidence.json';value=reader.load(path);value['limitations']=['Project-owned retained evidence limitation'];write(path,value)
            elif case=='known-schema':
                path=target/'.agent/schemas/harness-record.schema.json';path.write_bytes(path.read_bytes()+b'\n')
            elif case=='known-implementation':
                path=target/'.agent/diagnostics/diagnostic-catalog.json';path.write_bytes(path.read_bytes()+b'\n')
            elif case=='mode':(target/'.agent/tasks/TASK-0001.md').chmod(0o444)
            elif case=='mixed':(target/'.octon-mini-origin.json').write_bytes(self.old_origin)
            elif case=='unsupported':
                value=reader.load(target/'.octon-origin.json');value['profile']='standard';write(target/'.octon-origin.json',value)
            elif case=='pending':
                path=target/'.agent/transactions/pending/x.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}\n')
            elif case=='unknown-effect':
                path=target/'.agent/transactions/receipts/unknown.json';write(path,{'state':'outcome_unknown'})
            elif case=='git':(target/'.git').mkdir()
            else:
                path=target/'.agent/policy.json';path.write_bytes(path.read_bytes()+b'\n')
            before=snapshot(target)
            with self.assertRaises(ValueError):qualifier.fixture_conversion_plan(target)
            self.assertEqual(before,snapshot(target))
            if case=='mode':
                self.assertFalse((target/'.agent/tasks/TASK-0001.md').stat().st_mode & 0o200)
                (target/'.agent/tasks/TASK-0001.md').chmod(0o644)

if __name__=='__main__':
    unittest.main(verbosity=2)
