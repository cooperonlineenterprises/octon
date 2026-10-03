#!/usr/bin/env python3
"""Owned runtime-binding qualification; public evidence is never authority."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import contextlib
import io
import stat

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
import runtime_binding as R
import qualify_disposable_runtime as Q


# Trusted test-owned runner, outside target custody. It traces the actual known
# entry/dispatcher/validator child chain and denies any source/sibling reads.
# This is a qualification audit boundary, not a malicious-host execution fence.
COLD_PROBE = r'''import json, os, pathlib, runpy, subprocess, sys, time
area=pathlib.Path(sys.argv[1]).resolve(); target=pathlib.Path(sys.argv[2]).resolve()
source=pathlib.Path(sys.argv[3]).resolve(); script=pathlib.Path(sys.argv[4]).resolve()
arguments=sys.argv[5:]; probe=pathlib.Path(__file__).resolve(); original=subprocess.run
observed=[]; denied=[]
blocked=next((parent for parent in source.parents if parent.name=="Projects"),source.parent)
def outside_allowed(path):
    value=pathlib.Path(path).resolve()
    return value.is_relative_to(source) or (value.is_relative_to(blocked) and not value.is_relative_to(area))
def audit(event,args):
    if event in {'open','os.listdir','os.scandir'} and args and isinstance(args[0],(str,bytes,os.PathLike)):
        value=os.fsdecode(args[0])
        if outside_allowed(value):denied.append(event);raise RuntimeError('source/sibling access denied in cold qualification')
        if pathlib.Path(value).is_absolute() and pathlib.Path(value).resolve().is_relative_to(target):observed.append(event)
    if event in {'socket.connect','socket.bind'}:raise RuntimeError('network unavailable in cold qualification')
sys.addaudithook(audit)
def child(command,*args,**kwargs):
    if not isinstance(command,(list,tuple)) or pathlib.Path(command[0]).resolve()!=pathlib.Path(sys.executable).resolve():raise RuntimeError('only pinned Python target child allowed')
    selected=next((i for i,value in enumerate(command[1:],1) if not str(value).startswith('-')),None)
    if selected is None or not pathlib.Path(command[selected]).resolve().is_relative_to(target):raise RuntimeError('only copied target programs allowed')
    return original([sys.executable,'-I','-B',str(probe),str(area),str(target),str(source),str(command[selected]),*command[selected+1:]],*args,**kwargs)
subprocess.run=child
sys.argv=[str(script),*arguments];sys.path.insert(0,str(script.parent));sys.dont_write_bytecode=True
started=time.monotonic();code=0
try:runpy.run_path(str(script),run_name='__main__')
except SystemExit as end:code=end.code if isinstance(end.code,int) else 1
except RuntimeError as error:code=2; print(str(error),file=sys.stderr)
finally:
    modules=[]
    for name,module in sorted(sys.modules.items()):
        path=getattr(module,'__file__',None)
        if path and pathlib.Path(path).resolve().is_relative_to(target):modules.append({'module':name,'path':pathlib.Path(path).resolve().relative_to(target).as_posix()})
    record={'argv':[str(script),*arguments],'exit':code,'elapsed_seconds':time.monotonic()-started,'target_modules':modules,'source_sibling_reads':len(denied),'target_read_events':len(observed),'isolation':'Python isolated/bytecode-disabled; source/sibling reads and network audit-denied; nested actual target Python children wrapped'}
    (area/('cold-'+str(os.getpid())+'.json')).write_bytes((json.dumps(record,sort_keys=True)+'\n').encode())
raise SystemExit(code)
'''


class RuntimeBindingTests(unittest.TestCase):
    evidence=[]
    @classmethod
    def setUpClass(cls):
        cls.owned=tempfile.TemporaryDirectory(prefix='octon-owned-runtime-binding-')
        cls.addClassCleanup(cls.owned.cleanup)
        cls.area=Path(cls.owned.name).resolve();cls.seed=cls.area/'seed'
        cls.snapshot=cls.area/'trusted-source-v4.json';cls.snapshot.write_bytes((ROOT/'shared/source-contracts/profile-manifest.json').read_bytes())
        cls.source_sha=R.sha256(cls.snapshot.read_bytes())
        cls.reader=cls.area/'trusted-reader.py';cls.reader.write_bytes((HERE/'runtime_binding.py').read_bytes())
        cls.refresh_receipt={}
        Q.generate(cls.seed,runtime_binding=True,qualification_evidence=cls.refresh_receipt)
        cls.runtime_sha=R.sha256((cls.seed/R.TARGET_PATHS['runtime.manifest']).read_bytes())
        cls.policy=R.strict_json(cls.snapshot.read_bytes())
    def setUp(self):
        self.case_area=self.area/self._testMethodName;self.case_area.mkdir()
        self.target=self.case_area/'target';shutil.copytree(self.seed,self.target)
        self.initial=R.tree_inventory(self.target)
    def inspect(self,**kwargs):
        return R.inspect_runtime_binding(self.target,self.snapshot,
            expected_source_sha256=kwargs.get('source_sha',self.source_sha),
            expected_runtime_sha256=kwargs.get('runtime_sha',self.runtime_sha),
            layout_id=kwargs.get('layout','oep1_target'),state_owner=kwargs.get('state_owner','embedded'))
    def facet(self):return R.strict_json((self.target/R.TARGET_PATHS['runtime.manifest']).read_bytes())
    def write_facet(self,value):
        data=R.canonical_json(value);(self.target/R.TARGET_PATHS['runtime.manifest']).write_bytes(data);return R.sha256(data)
    def assert_refusal_readonly(self,reason=None,**kwargs):
        before=R.tree_inventory(self.target)
        with self.assertRaises((ValueError,OSError,KeyError,TypeError,SyntaxError)) as failure:self.inspect(**kwargs)
        if reason:self.assertIn(reason,str(failure.exception))
        self.assertEqual(before,R.tree_inventory(self.target))
        self.evidence.append({'case':self._testMethodName,'outcome':'refused','reason':str(failure.exception),'target_readonly':True})
    def test_positive_exact_external_pins_and_inventory(self):
        result=self.inspect();self.assertEqual(result['modules'],9);self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_code_executed']);self.assertEqual(self.initial,R.tree_inventory(self.target))
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','result':result,'target_readonly':True})
    def test_missing_independent_pins_refuse(self):
        for values in [{'source_sha':None},{'runtime_sha':None}]:self.assert_refusal_readonly('both independent',**values)
    def test_wrong_external_source_pin_refuse(self):self.assert_refusal_readonly('external source',source_sha='0'*64)
    def test_wrong_external_runtime_pin_refuse(self):self.assert_refusal_readonly('independent output',runtime_sha='0'*64)
    def test_selfconsistent_target_hashes_cannot_nominate_baseline(self):
        path=self.target/'.octon/runtime/scripts/octon.py';path.write_bytes(path.read_bytes()+b'\n# changed\n');facet=self.facet()
        for row in facet['modules']+facet['dependency_assets']:
            if row['path']=='.octon/runtime/scripts/octon.py':row['sha256']=R.sha256(path.read_bytes())
        self.write_facet(facet);self.assert_refusal_readonly('independent output')
    def test_facet_version_permission_owner_and_raw_substitution_refuse(self):
        for kind in ['version','permission','state','source','raw','recipe','self_hash']:
            shutil.rmtree(self.target);shutil.copytree(self.seed,self.target);facet=self.facet()
            if kind=='version':facet['schema_version']='octon.runtime-distribution-manifest.v99'
            elif kind=='permission':facet['permission_grant']=True
            elif kind=='state':facet['state_binding']['owner']='external'
            elif kind=='source':facet['source_inventory']['source']='wrong-profile.json'
            elif kind=='raw':facet['modules'][0]['raw_sha256']=facet['modules'][0]['sha256']
            elif kind=='recipe':facet['recipe']['version']='target-nominated'
            else:facet['digest']=R.sha256(R.canonical_json(facet))
            forged=self.write_facet(facet);self.assert_refusal_readonly(runtime_sha=forged)
    def test_missing_required_module_refuse(self):
        (self.target/'.octon/runtime/scripts/octon_continuation.py').unlink();self.assert_refusal_readonly('missing path')
    def test_target_module_verifier_canary_never_executes(self):
        marker=self.case_area/'canary-executed';canary=self.target/'.octon/runtime/fixture_admission.py';canary.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("executed")\n')
        self.assert_refusal_readonly('unreviewed executable');self.assertFalse(marker.exists())
    def test_changed_bound_program_canary_never_executes(self):
        marker=self.case_area/'changed-program-executed';path=self.target/'.octon/runtime/scripts/validate.py';path.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("executed")\n')
        self.assert_refusal_readonly('dependency');self.assertFalse(marker.exists())
    def test_unsafe_portable_paths_refuse(self):
        for path in ['../outside','/tmp/outside','C:/outside',r'\\server\share','a\\b','a//b','a/./b','NUL.json','a/COM1.txt','a./b']:
            with self.assertRaises(ValueError):R.portable_path(path)
        self.assertEqual(self.initial,R.tree_inventory(self.target));self.evidence.append({'case':self._testMethodName,'outcome':'refused unsafe paths','actual_native':os.name})
    def test_casefold_alias_or_collision_refuse(self):
        path=self.target/'.octon/runtime/scripts/octon.py'
        upper=path.with_name('OCTON.py')
        aliases=upper.exists() and upper.samefile(path)
        if aliases:path.rename(upper)
        else:upper.write_bytes(path.read_bytes())
        self.assert_refusal_readonly('component spelling/case')
        self.evidence.append({'case':self._testMethodName,'native_case_sensitive':not aliases,
                              'negative_strategy':'case-only rename' if aliases else 'two actual casefold-colliding files',
                              'actual_refusal':True})
    def test_native_symlink_or_explicit_unsupported(self):
        path=self.target/'.octon/runtime/scripts/octon.py';saved=path.read_bytes();path.unlink();outside=self.case_area/'outside.py';outside.write_bytes(saved)
        try:path.symlink_to(outside)
        except OSError as error:
            path.write_bytes(saved);self.evidence.append({'case':self._testMethodName,'outcome':'unsupported creation','host_capability':'symlink','error':str(error),'protection_claim':False});return
        self.assert_refusal_readonly('symlink');self.evidence.append({'case':self._testMethodName,'host_capability':'symlink','available':True,'actual_refusal':True})
    def test_native_windows_junction_or_nonwindows_disposition(self):
        if os.name!='nt':self.evidence.append({'case':self._testMethodName,'outcome':'not applicable','host_capability':'windows junction','actual_host':os.name,'protection_claim':False});return
        directory=self.target/'.octon/runtime/scripts';outside=self.case_area/'outside-scripts';directory.rename(outside)
        argv=['cmd','/c','mklink','/J',str(directory),str(outside)];value=subprocess.run(argv,capture_output=True,text=True)
        if value.returncode:
            outside.rename(directory);self.evidence.append({'case':self._testMethodName,'outcome':'unsupported creation','host_capability':'windows junction','exit':value.returncode,'error':value.stderr,'protection_claim':False});return
        try:self.assert_refusal_readonly('reparse');self.evidence.append({'case':self._testMethodName,'host_capability':'windows junction','available':True,'actual_refusal':True})
        finally:directory.rmdir();outside.rename(directory)
    def test_special_file_type_refuse(self):
        path=self.target/'.octon/runtime/scripts/octon.py';path.unlink();path.mkdir();self.assert_refusal_readonly('component type')
    def test_external_snapshot_and_explicit_root_relocation(self):
        moved=self.case_area/'moved';self.target.rename(moved);self.target=moved;self.assertEqual(self.inspect()['modules'],9);self.assertEqual(self.initial,R.tree_inventory(self.target))
        inside=self.target/'target-nominated-source.json';inside.write_bytes(self.snapshot.read_bytes());before=R.tree_inventory(self.target)
        with self.assertRaisesRegex(ValueError,'external regular'):R.inspect_runtime_binding(self.target,inside,expected_source_sha256=self.source_sha,expected_runtime_sha256=self.runtime_sha,layout_id='oep1_target',state_owner='embedded')
        self.assertEqual(before,R.tree_inventory(self.target))
    def test_duplicate_json_and_mixed_parent_refuse(self):
        path=self.target/'.octon/runtime/manifest.json';path.write_bytes(b'{"schema_version":"a","schema_version":"b"}')
        self.assert_refusal_readonly('duplicate',runtime_sha=R.sha256(path.read_bytes()))
        shutil.rmtree(self.target);shutil.copytree(self.seed,self.target);parent=self.target/'.octon/manifest.json';p=R.strict_json(parent.read_bytes());p['schema_version']='octon.disposable-installation.v2';parent.write_bytes(R.canonical_json(p));self.assert_refusal_readonly('mixed retained parent')
    def test_native_lf_and_mode_and_readonly_inspection(self):
        facet=self.facet()
        for row in facet['modules']+[facet['entry']]:
            data=(self.target/row['path']).read_bytes();self.assertNotIn(b'\r',data);self.assertEqual(row['sha256'],R.sha256(data));self.assertEqual(row['mode'],R.native_mode((self.target/row['path']).lstat()))
        self.inspect();self.assertEqual(self.initial,R.tree_inventory(self.target));self.evidence.append({'case':self._testMethodName,'outcome':'passed','raw_source_lf':True,'emitted_utf8_lf':True,'mode_model':'windows_writable' if os.name=='nt' else 'posix_bits','target_readonly':True})
    def test_independent_copied_reader_and_entry_basic_without_source_siblings(self):
        argv=[sys.executable,'-I','-B',str(self.reader),'--project-root',str(self.target),'--source-snapshot',str(self.snapshot),'--expected-source-sha256',self.source_sha,'--expected-runtime-sha256',self.runtime_sha,'--layout-id','oep1_target','--state-owner','embedded']
        steps=[]
        for command in [argv,[sys.executable,'-I','-B',str(self.target/'octon'),'installation','inspect'],[sys.executable,'-I','-B',str(self.target/'octon'),'check'],[sys.executable,'-I','-B',str(self.target/'octon'),'work','start','--help']]:
            v=subprocess.run(command,cwd=self.case_area,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);steps.append({'argv':command,'exit':v.returncode,'stdout_sha256':R.sha256(v.stdout.encode())})
        refused=subprocess.run([sys.executable,'-I','-B',str(self.target/'octon'),'--help'],cwd=self.case_area,capture_output=True,text=True);self.assertEqual(refused.returncode,2);self.assertIn('command outside disposable',refused.stderr)
        self.assertEqual(self.initial,R.tree_inventory(self.target));self.evidence.append({'case':self._testMethodName,'outcome':'passed','steps':steps,'source_checkout_not_imported':True,'sibling_or_plectarium_dependencies':False,'target_readonly':True,'top_level_help_preserved_refusal':2})
    def test_no_new_target_generation_or_authority(self):
        p=Q.scaffold.load_generation_policy();target=Q.scaffold.target_installation_contract(p)
        self.assertEqual(target['generation_status'],'design_only_not_selectable');self.assertEqual(sum(row['source_rule_id'] is None for row in target['file_inventory']),20)
        for args in [{'admission':True},{'protected':True},{'durable':True}]:
            dest=self.case_area/('refused-'+next(iter(args)))
            with self.assertRaisesRegex(ValueError,'plain Minimal'):Q.generate(dest,runtime_binding=True,**args)
            self.assertFalse(dest.exists())
    def test_semantic_compatibility_refuses_unexplained_drift(self):
        raw=(ROOT/R.HISTORICAL_SOURCE).read_bytes()
        for mutation in ['rule','layout','ownership','dependency','modulepath']:
            p=copy.deepcopy(self.policy)
            if mutation=='rule':p['rules'][0]['disposition']='source_only'
            elif mutation=='layout':p['layouts'][0]['id']='other'
            elif mutation=='ownership':p['installation_bindings']['target']['root_bindings']['runtime']['owner']='project'
            elif mutation=='dependency':p['disposable_runtime']['required_dependencies'].append('plectarium')
            else:p['disposable_runtime']['runtime_paths'][0]='.octon/runtime/scripts/other.py'
            with self.assertRaises(ValueError):R.historical_compatibility_policy(p,raw)

    def rebind_parent(self, parent):
        data=R.canonical_json(parent);(self.target/'.octon/manifest.json').write_bytes(data)
        facet=self.facet();facet['parent_installation']['sha256']=R.sha256(data)
        facet['non_null_outputs']=[row for row in parent['output_inventory'] if row['sha256'] is not None]
        return self.write_facet(facet)
    def restore(self):
        shutil.rmtree(self.target);shutil.copytree(self.seed,self.target)
    def test_complete_render_inputs_and_json_scalar_types_refuse(self):
        for field,value in [('DERIVED_OPERATIONAL_FILES_JSON','[]'),('PROFILE_OPERATIONAL_FILES_JSON','[]')]:
            self.restore();facet=self.facet();facet['render_inputs']['template_variables'][field]=value
            self.assert_refusal_readonly('render inputs',runtime_sha=self.write_facet(facet))
        for field,value in [('permission_grant',0),('execution_authorized',0)]:
            self.restore();facet=self.facet();facet[field]=value;self.assert_refusal_readonly('role/version',runtime_sha=self.write_facet(facet))
        self.restore();facet=self.facet();facet['render_inputs']['projected_dispatcher_parent_index']=3.0
        self.assert_refusal_readonly('render/projection',runtime_sha=self.write_facet(facet))
    def test_full_parent_paths_nulls_and_duplicate_records_refuse(self):
        for change in ['duplicate','casefold','remove','non_null_to_null','derived_to_non_null','input_remove','input_duplicate','input_extra']:
            self.restore();parent=R.strict_json((self.target/'.octon/manifest.json').read_bytes())
            rows=parent['inputs'] if change.startswith('input_') else parent['output_inventory']
            if change in {'duplicate','input_duplicate'}:rows.append(copy.deepcopy(rows[0]))
            elif change=='casefold':rows[0]['path']=rows[0]['path'].upper()
            elif change in {'remove','input_remove'}:rows.pop()
            elif change=='input_extra':rows.append({'path':'unreviewed.py','sha256':'0'*64})
            elif change=='non_null_to_null':next(row for row in rows if row['sha256'] is not None)['sha256']=None
            else:next(row for row in rows if row['sha256'] is None)['sha256']='0'*64
            self.assert_refusal_readonly(runtime_sha=self.rebind_parent(parent))
    def test_schema_reader_rule_and_source_drift_refuse(self):
        for kind in ['schema','reader','rule','required','module','byte_contract']:
            p=copy.deepcopy(self.policy)
            if kind=='schema':p['runtime_binding']['schema_inputs'][0]['sha256']='0'*64
            elif kind=='reader':p['runtime_binding']['reader']['sha256']='0'*64
            elif kind=='rule':p['runtime_binding']['modules'][0]['source_rule_id']='source-contracts'
            elif kind=='required':p['runtime_binding']['modules'][0]['required']=1
            elif kind=='module':p['runtime_binding']['modules'][0]['source']=p['runtime_binding']['modules'][1]['source']
            else:p['runtime_binding']['source_newline']='crlf'
            with self.assertRaises(ValueError):R.validate_source_binding(p,source_root=ROOT)
        facet=self.facet();facet['schema_inputs'][0]['sha256']='0'*64
        self.assert_refusal_readonly('recipe/reader',runtime_sha=self.write_facet(facet))
    def test_parent_and_all_non_null_bindings_survive_final_refresh(self):
        proof=self.refresh_receipt['refresh_proof'];self.assertEqual(proof['parent_sha256'],R.sha256((self.target/'.octon/manifest.json').read_bytes()))
        self.assertEqual(proof['facet_sha256'],self.runtime_sha);self.assertEqual(proof['after'],self.initial)
        self.assertEqual(set(proof['changed_paths']),R.DERIVED_REFRESH_PATHS)
        parent=R.strict_json((self.target/'.octon/manifest.json').read_bytes())
        self.assertEqual(proof['immutable_bindings'],R.verify_parent_bindings(self.target,parent))
        self.assertEqual(len(parent['output_inventory']),114);self.assertEqual(len(self.facet()['non_null_outputs']),109)
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','refresh_proof':proof})
    def test_real_final_refresh_parent_non_null_and_residual_faults_refuse_publish(self):
        original=Q.run
        for fault in ['parent','non_null','facet','residual','derived_delete','derived_mode']:
            dest=self.case_area/('unpublished-'+fault);count=0
            def injected(argv,cwd):
                nonlocal count
                result=original(argv,cwd)
                if str(argv[2]).endswith('/scripts/refresh.py'):
                    count+=1
                    if count==3:
                        path=cwd/({'parent':'.octon/manifest.json','non_null':'AGENTS.md','facet':'.octon/runtime/manifest.json','residual':'.octon/agent/refresh-residual.txt','derived_delete':'.octon/agent/state/current.json','derived_mode':'.octon/agent/state/current.json'}[fault])
                        if fault=='derived_delete':path.unlink()
                        elif fault=='derived_mode':path.chmod(stat.S_IREAD if os.name=='nt' else 0o600)
                        else:path.write_bytes(path.read_bytes()+b'\n# injected refresh fault\n' if path.exists() else b'residual')
                return result
            with mock.patch.object(Q,'run',side_effect=injected):
                with self.assertRaisesRegex(ValueError,'postfacet'):Q.generate(dest,runtime_binding=True)
            self.assertEqual(count,3);self.assertFalse(dest.exists())
            self.assertFalse(any(path.name.startswith('octon-disposable-stage-') for path in self.case_area.iterdir()))
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','actual_refresh_faults':['parent','non_null','facet','residual','derived_delete','derived_mode'],'target_published':False,'temporary_stages_reconciled':True})
    def test_facet_tamper_stales_full_fingerprint_refresh_cannot_replace_pin(self):
        path=self.target/R.TARGET_PATHS['runtime.manifest'];path.write_bytes(path.read_bytes()+b' ')
        command=[sys.executable,'-I','-B',str(self.target/'octon'),'check']
        value=subprocess.run(command,cwd=self.case_area,capture_output=True,text=True);self.assertNotEqual(value.returncode,0)
        stale_hash=R.sha256((value.stdout+value.stderr).encode());self.assert_refusal_readonly('independent output')
        refreshed=subprocess.run([sys.executable,'-I','-B',str(self.target/'.octon/runtime/scripts/refresh.py'),'--refresh'],cwd=self.case_area,capture_output=True,text=True);self.assertEqual(refreshed.returncode,0,refreshed.stderr)
        value=subprocess.run(command,cwd=self.case_area,capture_output=True,text=True);self.assertEqual(value.returncode,0,value.stderr)
        self.assert_refusal_readonly('independent output')
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','stale_check_exit_nonzero':True,'stale_diagnostic_sha256':stale_hash,'explicit_refresh_exit':refreshed.returncode,'after_refresh_check_exit':value.returncode,'external_pin_still_refused':True})
    def test_forbidden_high_assurance_mixed_state_and_unregistered_native_binary_refuse(self):
        for name in R.FORBIDDEN_DERIVED+['.agent/policy.json','.octon/runtime/unreviewed.pyd']:
            self.restore();path=self.target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'{}')
            self.assert_refusal_readonly()
        for owner in ['external','both',None]:self.assert_refusal_readonly(state_owner=owner)
    def test_actual_native_readonly_bytes_and_mode_mutation_refuse(self):
        path=self.target/'.octon/runtime/scripts/octon.py';old=path.stat().st_mode
        path.chmod(stat.S_IREAD if os.name=='nt' else 0o444)
        try:self.assert_refusal_readonly('mode')
        finally:path.chmod(old)
        data=path.read_bytes();path.write_bytes(data.replace(b'\n',b'\r\n'));self.assert_refusal_readonly('dependency')
        self.restore();path=self.target/R.TARGET_PATHS['runtime.entry'];path.write_bytes(path.read_bytes().replace(b'\n',b'\r\n'));self.assert_refusal_readonly('dependency')
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','native_readonly_attribute_exercised':os.name=='nt','posix_permission_bits_exercised':os.name!='nt','crlf_raw_byte_tampering_refused':True})
    def test_pinned_program_ast_local_import_and_schema_closure(self):
        facet=self.facet();R.validate_import_closure(facet['dependency_assets'])
        local=[row for row in facet['dependency_assets'] if row['path'].endswith('.py') or row['path'] in {'octon',R.TARGET_PATHS['runtime.entry']}]
        self.assertEqual(len(local),12);self.assertTrue(any(row['path'].endswith('installation_runtime.py') for row in local))
        forged=copy.deepcopy(facet['dependency_assets']);forged[-1]['imports']=['unbound_network_package']
        with self.assertRaisesRegex(ValueError,'unbound'):R.validate_import_closure(forged)
        schemas=[row for row in facet['dependency_assets'] if '/schemas/' in row['path']]
        self.assertGreater(len(schemas),30)
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','all_python_assets':local,'schema_asset_count':len(schemas),'target_programs_imported':False})
    def test_native_protocol_missing_duplicate_nonfinite_terminal_evidence_refuse(self):
        valid={'schema_version':'octon.runtime-binding-qualification.v1','permission_grant':False,'candidate_qualified':False,'source_subject':{'revision':'a'*40,'status':[],'files':{'octon':'0'*64}},'case_names':['test_one'],'source_revision':'a'*40,'source_status':[],'source_unchanged':True,'test_suite_passed':True,'complete_suite':True,'tests_run':1,'failures':0,'errors':0,'cases':[{'case':'test_one','terminal':True,'outcome':'passed'}],'native_unsupported':[],'platform':{'system':platform.system(),'machine':platform.machine(),'version':platform.version(),'os_name':os.name},'python':sys.version,'executable':sys.executable,'qualified':True}
        wrap=lambda value:'OCTON_RUNTIME_BINDING_EVIDENCE_BEGIN\n'+json.dumps(value)+'\nOCTON_RUNTIME_BINDING_EVIDENCE_END'
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(R.forward_native_evidence(wrap(valid)),valid)
        for kind in ['missing','terminal','duplicate_terminal','source','false_qualified','failure','numeric']:
            value=copy.deepcopy(valid)
            if kind=='missing':value.pop('tests_run')
            elif kind=='terminal':value['cases']=[]
            elif kind=='duplicate_terminal':value['cases']*=2
            elif kind=='source':value['source_subject']['revision']='b'*40
            elif kind=='false_qualified':value['native_unsupported']=[{'case':'test_one','protection_claim':False}]
            elif kind=='failure':value['errors']=1
            else:value['permission_grant']=0
            with self.assertRaises(ValueError):R.forward_native_evidence(wrap(value))
        for raw in ['{"schema_version":"a","schema_version":"b"}','{"x":NaN}']:
            with self.assertRaises(ValueError):R.forward_native_evidence('OCTON_RUNTIME_BINDING_EVIDENCE_BEGIN\n'+raw+'\nOCTON_RUNTIME_BINDING_EVIDENCE_END')

    def test_cold_actual_entry_chain_denies_source_and_optional_payload_reads(self):
        # Independent caller-pin inspection precedes this separate known-entry execution.
        self.inspect();probe=self.case_area/'trusted-cold-probe.py';probe.write_bytes(COLD_PROBE.encode())
        steps=[]
        for arguments in [['installation','inspect'],['work','start','--help'],['check']]:
            argv=[sys.executable,'-I','-B',str(probe),str(self.case_area),str(self.target),str(ROOT),str(self.target/'octon'),*arguments]
            value=subprocess.run(argv,cwd=self.case_area,capture_output=True,text=True)
            self.assertEqual(value.returncode,0,value.stderr);steps.append({'argv':arguments,'exit':value.returncode,'stdout_sha256':R.sha256(value.stdout.encode())})
        traces=[R.strict_json(path.read_bytes()) for path in sorted(self.case_area.glob('cold-*.json'))]
        self.assertEqual(len(traces),5);self.assertEqual(sum(Path(row['argv'][0]).name=='octon' and 'scripts' not in Path(row['argv'][0]).parts for row in traces),3);self.assertTrue(all(row['source_sibling_reads']==0 and row['exit']==0 for row in traces))
        modules={row['module'] for trace in traces for row in trace['target_modules']}
        self.assertNotIn('octon_work_completion',modules);self.assertFalse(any('/packages/' in row['path'] for trace in traces for row in trace['target_modules']))
        denial=self.case_area/'denial-canary.py';denial.write_bytes(('from pathlib import Path\nPath('+repr(str(ROOT/'VERSION'))+').read_bytes()\n').encode())
        value=subprocess.run([sys.executable,'-I','-B',str(probe),str(self.case_area),str(self.target),str(ROOT),str(denial)],cwd=self.case_area,capture_output=True,text=True)
        self.assertEqual(value.returncode,2);self.assertIn('source/sibling access denied',value.stderr)
        denied=[R.strict_json(path.read_bytes()) for path in self.case_area.glob('cold-*.json') if R.strict_json(path.read_bytes())['source_sibling_reads']==1]
        self.assertEqual(len(denied),1)
        self.assertEqual(self.initial,R.tree_inventory(self.target))
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','source_access_denial_canary':denied,'actual_child_chain':traces,'steps':steps,'source_sibling_access_unavailable_by_audit':True,'optional_payload_imported':False,'target_readonly':True,'cold_start_measurement':'fresh interpreter observation, no OS cache eviction claim'})
    def test_native_readonly_target_success_with_independent_mode_pin(self):
        facet=self.facet();saved={}
        for row in facet['dependency_assets']:
            path=self.target/row['path'];saved[path]=path.stat().st_mode;path.chmod(stat.S_IREAD if os.name=='nt' else 0o444)
            row['mode']=R.native_mode(path.lstat())
        for row in facet['modules']+[facet['entry']]:row['mode']=R.native_mode((self.target/row['path']).lstat())
        pin=self.write_facet(facet);before=R.tree_inventory(self.target)
        try:self.assertEqual(self.inspect(runtime_sha=pin)['modules'],9);self.assertEqual(before,R.tree_inventory(self.target))
        finally:
            for path,mode in saved.items():path.chmod(mode)
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','target_assets_readonly':True,'mode_model':'windows_writable' if os.name=='nt' else 'posix_bits','target_readonly':True})

    def test_occupied_readonly_resolver_preserves_generation_collision_refusal(self):
        self.assertEqual(R.ReadOnlyTargetBinding(self.target,layout_id='oep1_target',state_owner='embedded').path(R.TARGET_PATHS['runtime.entry']),self.target/R.TARGET_PATHS['runtime.entry'])
        with self.assertRaisesRegex(ValueError,'reserved-path disposition'):Q.scaffold.InstallationBinding.target(self.target,self.policy)
        with self.assertRaises(ValueError):Q.generate(self.target,runtime_binding=True)
        self.assertEqual(self.initial,R.tree_inventory(self.target))
    def test_native_fifo_refusal_or_nonposix_disposition(self):
        if not hasattr(os,'mkfifo'):
            self.evidence.append({'case':self._testMethodName,'outcome':'not applicable','host_capability':'POSIX FIFO','actual_host':os.name,'protection_claim':False});return
        path=self.target/'.octon/runtime/scripts/octon.py';path.unlink();os.mkfifo(path)
        self.assert_refusal_readonly('component type')
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','native_fifo_type_refused_before_read':True})
    def test_closed_facet_schema_and_acyclic_binding_graph(self):
        import validate_source_contracts as contracts
        facet=self.facet();schema=R.strict_json((ROOT/R.SCHEMA_SOURCES[1]).read_bytes())
        self.assertEqual(contracts.schema_issues(facet,schema,'facet'),[])
        value=copy.deepcopy(facet);value.pop('schema_inputs');self.assertTrue(contracts.schema_issues(value,schema,'facet'))
        value=copy.deepcopy(facet);value['sha256']=self.runtime_sha;self.assertTrue(contracts.schema_issues(value,schema,'facet'))
        self.assertNotIn('source_inventory',self.policy['runtime_binding']);self.assertNotIn('sha256',facet)
        self.assertEqual(facet['parent_installation']['sha256'],R.sha256((self.target/'.octon/manifest.json').read_bytes()))
        self.assertEqual(facet['source_inventory']['sha256'],self.source_sha)
        raw=(self.target/R.TARGET_PATHS['runtime.manifest']).read_bytes()
        (self.target/R.TARGET_PATHS['runtime.manifest']).write_bytes(raw.rstrip(b'\n'))
        self.assert_refusal_readonly('serialization',runtime_sha=R.sha256(raw.rstrip(b'\n')))
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','graph':['raw recipe/templates/reader/schema','source_v4','emitted modules/entry','parent','facet','derived fingerprint'],'facet_raw_receipt_external':True,'self_digest_absent':True})

    def test_current_v4_target_inventory_ownership_duplicate_and_rule_semantics_refuse(self):
        stages={
            'bindings_missing':'current source shape', 'bindings_type':'current installation bindings shape',
            'target_missing':'current installation bindings shape', 'target_type':'current target shape',
            'runtime_binding_type':'source runtime binding: object', 'roots_type':'inventory/root shape',
            'rows_type':'inventory/root shape', 'row_type':'current target row shape',
            'row_missing':'current target row shape', 'row_scalar':'current target row scalar shape',
            'count_type':'current target count/digest shape',
            'version':'inactive target-design successor', 'count':'legacy generation/dependency/ownership/layout semantics',
            'status':'legacy generation/dependency/ownership/layout semantics',
            'root_escape':'legacy generation/dependency/ownership/layout semantics',
            'file_escape':'legacy generation/dependency/ownership/layout semantics',
            'digest':'inventory payload digest', 'root':'legacy generation/dependency/ownership/layout semantics',
            'required':'legacy generation/dependency/ownership/layout semantics',
            'owner':'legacy generation/dependency/ownership/layout semantics',
            'duplicate_state':'legacy generation/dependency/ownership/layout semantics',
            'duplicate_identity':'legacy generation/dependency/ownership/layout semantics',
            'source_rule':'only the two bounded runtime rows', 'source_rule_missing':'only the two bounded runtime rows'}
        for kind,stage in stages.items():
            value=copy.deepcopy(self.policy);target=value['installation_bindings']['target']
            if kind=='bindings_missing':del value['installation_bindings']
            elif kind=='bindings_type':value['installation_bindings']=[]
            elif kind=='target_missing':del value['installation_bindings']['target']
            elif kind=='target_type':value['installation_bindings']['target']=None
            elif kind=='runtime_binding_type':value['runtime_binding']=[]
            elif kind=='roots_type':target['root_bindings']=[]
            elif kind=='rows_type':target['file_inventory']={}
            elif kind=='row_type':target['file_inventory'][0]=None
            elif kind=='row_missing':del target['file_inventory'][0]['owner']
            elif kind=='row_scalar':target['file_inventory'][0]['owner']=False
            elif kind=='count_type':target['inventory_count']=True
            elif kind=='version':target['schema_version']='unknown'
            elif kind=='count':target['inventory_count']-=1
            elif kind=='status':target['generation_status']='active'
            elif kind=='root_escape':target['root_bindings']['agent']['path']='../escape'
            elif kind=='file_escape':target['file_inventory'][0]['path']='../escape'
            elif kind=='digest':target['inventory_sha256']='0'*64
            elif kind=='root':del target['root_bindings']['agent']
            elif kind=='required':target['file_inventory']=[row for row in target['file_inventory'] if row['id']!='harness.policy']
            elif kind=='owner':next(row for row in target['file_inventory'] if row['id']=='harness.policy')['owner']='runtime_release'
            elif kind=='duplicate_state':target['file_inventory'].append({**next(row for row in target['file_inventory'] if row['id']=='harness.state.focus'),'id':'harness.state.second-focus','path':'.octon/agent/state/second-focus.json'})
            elif kind=='duplicate_identity':target['file_inventory'].append(copy.deepcopy(target['file_inventory'][0]))
            elif kind=='source_rule':next(row for row in target['file_inventory'] if row['id']=='harness.policy')['source_rule_id']='templates-core'
            else:next(row for row in target['file_inventory'] if row['id']=='runtime.entry')['source_rule_id']=None
            if kind not in {'bindings_missing','bindings_type','target_missing','target_type','runtime_binding_type','roots_type','rows_type','row_type','row_missing','row_scalar','count_type','count','digest'}:
                target['inventory_count']=len(target['file_inventory']);target['inventory_sha256']=R.inventory_digest(target['file_inventory'])
            before=R.canonical_json(value)
            with self.assertRaisesRegex(ValueError,stage):Q.scaffold.target_installation_contract(value)
            self.assertEqual(before,R.canonical_json(value));self.assertEqual(self.initial,R.tree_inventory(self.target))
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','actual_current_v4_mutation_stages':stages,'input_policy_readonly':True,'target_readonly':True})
    def test_root_native_spelling_and_reserved_space_name_refuse(self):
        with self.assertRaisesRegex(ValueError,'reserved native'):R.portable_path('a/CON .txt')
        alias=self.target.with_name('TARGET')
        aliases=alias.exists() and alias.samefile(self.target)
        if aliases:
            with self.assertRaisesRegex(ValueError,'root component spelling/case'):R.ReadOnlyTargetBinding(alias,layout_id='oep1_target',state_owner='embedded')
        else:
            with self.assertRaises(OSError):R.ReadOnlyTargetBinding(alias,layout_id='oep1_target',state_owner='embedded')
        self.assertEqual(self.initial,R.tree_inventory(self.target))
        self.evidence.append({'case':self._testMethodName,'outcome':'passed','native_root_case_alias_available':aliases,'actual_native_alias_refused':aliases,'reserved_CON_space_refused':True})


class EvidenceResult(unittest.TextTestResult):
    def addSuccess(self,test):
        super().addSuccess(test)
        name=test._testMethodName
        details=[row for row in RuntimeBindingTests.evidence if row.get('case')==name]
        outcome='unsupported' if any(row.get('outcome')=='unsupported creation' for row in details) else 'not_applicable' if any(row.get('outcome')=='not applicable' for row in details) else 'passed'
        RuntimeBindingTests.evidence.append({'case':name,'terminal':True,'outcome':outcome})


def main():
    files=sorted(set(path for command in [
        ['git','--no-optional-locks','ls-files','-z'],
        ['git','--no-optional-locks','ls-files','--others','--exclude-standard','-z']]
        for path in subprocess.check_output(command,cwd=ROOT).decode('utf-8').split('\0') if path))
    def subject():
        return {'revision':subprocess.check_output(['git','--no-optional-locks','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'status':subprocess.check_output(['git','--no-optional-locks','status','--porcelain=v1'],cwd=ROOT,text=True).splitlines(),
            'files':{name:R.sha256((ROOT/name).read_bytes()) for name in files}}
    initial=subject();started=time.monotonic();result=unittest.TextTestRunner(verbosity=2,resultclass=EvidenceResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeBindingTests))
    final=subject();unchanged=initial==final;names=unittest.defaultTestLoader.getTestCaseNames(RuntimeBindingTests)
    unsupported=[c for c in RuntimeBindingTests.evidence if c.get('outcome')=='unsupported creation']
    complete=result.testsRun==len(names);passed=result.wasSuccessful() and unchanged and complete
    record={'schema_version':'octon.runtime-binding-qualification.v1','permission_grant':False,
        'qualified':passed and not initial['status'] and not unsupported,'test_suite_passed':passed,
        'qualification_scope':'exact native caller-pinned metadata fixture tests only','candidate_qualified':False,
        'complete_suite':complete,'source_subject':initial,'source_unchanged':unchanged,
        'source_revision':initial['revision'],'source_status':initial['status'],
        'platform':{'system':platform.system(),'machine':platform.machine(),'version':platform.version(),'os_name':os.name},
        'python':sys.version,'executable':sys.executable,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'case_names':names,'cases':RuntimeBindingTests.evidence,'native_unsupported':unsupported,
        'elapsed_seconds':time.monotonic()-started,'meaning':'Caller-pinned integrity/compatibility, not authentication or authority; current fixture tests only'}
    print('OCTON_RUNTIME_BINDING_EVIDENCE_BEGIN\n'+json.dumps(record,sort_keys=True)+'\nOCTON_RUNTIME_BINDING_EVIDENCE_END',flush=True)
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
