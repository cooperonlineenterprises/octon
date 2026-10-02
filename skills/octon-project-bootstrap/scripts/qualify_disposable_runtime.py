#!/usr/bin/env python3
"""Explicit source-only, disposable target packaging; never a production installer."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import installation_runtime as reader
import installation_runtime_v2 as admission_reader
import scaffold_project as scaffold

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[2]


def project_path(value):
    if value.startswith('.agent/scripts/'):
        return value.replace('.agent/scripts/','.octon/runtime/scripts/',1)
    if value.startswith('.agent/'):
        return value.replace('.agent/','.octon/agent/',1)
    if value.startswith('project-dossier/'):
        return value.replace('project-dossier/','.octon/dossier/',1)
    if value.startswith('.agents/'):
        return value.replace('.agents/','.octon/agents/',1)
    return value


def project_text(text):
    # Closed compatibility projection, applied only to freshly generated assets.
    return (text.replace('".agent" / "scripts"', '".octon/runtime/scripts"').replace('.agent/scripts/', '.octon/runtime/scripts/')
            .replace('.agent/', '.octon/agent/').replace('project-dossier/', '.octon/dossier/').replace('"project-dossier"','".octon/dossier"')
            .replace('".agent"','".octon/agent"').replace("'.agent'","'.octon/agent'")
            .replace('.agents/', '.octon/agents/'))


def run(argv,cwd):
    result = subprocess.run([str(x) for x in argv],cwd=cwd,capture_output=True,text=True,check=False,shell=False)
    if result.returncode:
        raise ValueError(result.stderr or result.stdout)
    return result


def generate(target, project_name='Disposable Runtime Fixture', *, admission=False, protected=False, durable=False):
    if durable and not (admission and protected):
        raise ValueError('durable successor requires explicit protected and admission fixture dependencies')
    if protected and not admission:
        raise ValueError('protected successor requires explicit admission fixture dependency')
    if not target.is_absolute():
        raise ValueError('target must be absolute')
    scaffold.validate_target(target)
    policy = scaffold.load_generation_policy()
    contract = policy['disposable_runtime']
    if contract['status'] != 'qualification_only_not_selectable':
        raise ValueError('qualification contract is inactive or unsupported')
    templates, schemas = scaffold.resolve_generation_inputs('minimal',policy,'compact')
    source_inputs = set(templates.values()) | set(schemas.values()) | {
        SCRIPTS/'scaffold_project.py',SCRIPTS/'installation_runtime.py',Path(__file__).resolve(),
        ROOT/'shared/source-contracts/profile-manifest.json',ROOT/'shared/source-contracts/profile-manifest-v3.schema.json',
        ROOT/'dossier/artifact-types.json',ROOT/'octon.json',ROOT/'VERSION'}
    inputs = [{'path':path.relative_to(ROOT).as_posix(), 'sha256':reader.digest(path.read_bytes())}
              for path in sorted(source_inputs)]
    facet = admission_reader.validate_admission_inventory(reader.load(ROOT/'shared/source-contracts/admission-fixture-inventory.json')) if admission else None
    if admission:
        for item in facet['assets']:
            path=ROOT/item['source']; inputs.append({'path':item['source'],'sha256':reader.digest(path.read_bytes())})
        path=ROOT/'shared/source-contracts/admission-fixture-inventory.json'
        inputs.append({'path':path.relative_to(ROOT).as_posix(),'sha256':reader.digest(path.read_bytes())})
        inputs=sorted(inputs,key=lambda row:row['path'])
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    with tempfile.TemporaryDirectory(prefix='octon-disposable-stage-',dir=target.parent) as temporary:
        area = Path(temporary)
        legacy = area/'rendered'
        run([sys.executable,'-B',SCRIPTS/'scaffold_project.py','--target',legacy,
             '--project-name',project_name,'--profile','minimal','--layout','compact'],ROOT)
        stage = area/'target'
        stage.mkdir()
        for path in sorted(legacy.rglob('*')):
            if path.is_file():
                relative = path.relative_to(legacy).as_posix()
                destination = stage/project_path(relative)
                destination.parent.mkdir(parents=True,exist_ok=True)
                text = path.read_text(encoding='utf-8') if relative.startswith('.agent/schemas/') else project_text(path.read_text(encoding='utf-8'))
                if relative.startswith('.agent/scripts/'):
                    text = text.replace('parents[2]', 'parents[3]')
                    text = text.replace('if path.is_file() and not path.is_symlink()', 'if path.is_file() and not path.is_symlink() and not path.relative_to(root).as_posix().startswith(".octon/archive/predecessor/")')
                    text = text.replace('if item.is_file() and not item.is_symlink()', 'if item.is_file() and not item.is_symlink() and not item.relative_to(root).as_posix().startswith(".octon/archive/predecessor/")')
                    if relative == '.agent/scripts/validate.py':
                        text = text.replace('or rel.startswith(".octon/agent/transactions/")', 'or rel.startswith(".octon/agent/transactions/")\n            or rel.startswith(".agent/transactions/")')
                        text = text.replace('if rel.startswith(".octon/agent/tests/fixtures/invalid/"):', 'if rel.startswith((".octon/agent/tests/fixtures/invalid/", ".octon/archive/predecessor/")):')
                        text = text.replace('predecessor_origin, ".octon"):', 'predecessor_origin):')
                        adapter = r'''def qualification_schema_paths(value):
    if isinstance(value, dict):
        return {key: (item.replace('project-dossier', r'\.octon/dossier').replace(r'\.agent', r'\.octon/agent') if key == 'pattern' and isinstance(item, str) else qualification_schema_paths(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [qualification_schema_paths(item) for item in value]
    if isinstance(value, str):
        return value.replace('.agent/scripts/', '.octon/runtime/scripts/').replace('.agent/', '.octon/agent/').replace('project-dossier/', '.octon/dossier/')
    return value


'''
                        text = text.replace('def load_schema(root:', adapter+'def load_schema(root:')
                        text = text.replace('value = load_json(root / ".octon/agent" / "schemas" / name)', 'value = qualification_schema_paths(load_json(root / ".octon/agent" / "schemas" / name))')
                        text = text.replace('value.update(relative_path.encode("utf-8"))', 'value.update(relative_path.replace(".octon/agent/", ".agent/", 1).encode("utf-8"))')
                    if relative == '.agent/scripts/octon_transaction.py':
                        text = text.replace('ROOT = Path(__file__).resolve().parents[3]', 'import sys\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom installation_runtime import protected_paths, admit_work_plan, admit_recovery_record, load as qualification_json_load\nROOT = Path(__file__).resolve().parents[3]')
                        admission_helpers = """def qualification_work_admission(root, plan):
    try:
        admit_work_plan(root, plan)
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise TransactionError(str(error)) from error


def qualification_recovery_admission(root, record):
    try:
        admit_recovery_record(root, record)
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise TransactionError(str(error)) from error


"""
                        text = text.replace('def apply_plan(', admission_helpers+'def apply_plan(')
                        text = text.replace('json.loads(receipt_path.read_text(encoding="utf-8"))', 'qualification_json_load(receipt_path)')
                        text = text.replace('json.loads(pending_path.read_text(encoding="utf-8"))', 'qualification_json_load(pending_path)')
                        text = text.replace('    if receipt["status"] == "applied":', '    qualification_recovery_admission(root, receipt)\n    if receipt["status"] == "applied":')
                        text = text.replace('    recovery_path = confined_path(', '    qualification_recovery_admission(root, pending)\n    recovery_path = confined_path(')
                        text = text.replace('LAST_PHASE_TIMINGS.clear()', 'qualification_work_admission(root, plan)\n    LAST_PHASE_TIMINGS.clear()')
                        text = text.replace('root = root.resolve()\n    if not operations:', 'root = root.resolve()\n    if operation_name.startswith("work."):\n        evidence_paths = list(dict.fromkeys([*(evidence_paths or []), *protected_paths(root)]))\n    if not operations:')
                    if relative == '.agent/scripts/octon.py':
                        text = text.replace('_CURRENT_DISPATCHER_PARENT_INDEX = "2"','_CURRENT_DISPATCHER_PARENT_INDEX = "3"')
                if admission and relative == '.agent/scripts/octon_transaction.py':
                    text = admission_transaction_projection(text)
                if admission and relative == '.agent/scripts/refresh.py':
                    text = text.replace('generated_at = datetime.now(timezone.utc).isoformat()', 'generated_at = qualification_refresh()[0]').replace('identifier = secrets.token_hex(16)', 'identifier = qualification_refresh()[1]')
                    text = text.replace('def main(', '''def qualification_refresh():
    import os
    path=os.environ.get('OCTON_FIXTURE_ADMISSION_CONTEXT')
    if path:
        value=json.loads(Path(path).read_text())['refresh']
        return value['time'],value['id']
    return datetime.now(timezone.utc).isoformat(),secrets.token_hex(16)


def main(''')
                destination.write_text(text,encoding='utf-8')
                shutil.copymode(path,destination)
        runtime=stage/'.octon/runtime'
        shutil.copy2(SCRIPTS/'installation_runtime.py',runtime/'installation_runtime.py')
        if admission:
            for item in facet['assets']:
                destination=stage/item['target']; destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/item['source'],destination)
            shutil.copy2(ROOT/'shared/source-contracts/admission-fixture-inventory.json',runtime/'admission-inventory.json')
        (runtime/'profile-inventory.json').write_bytes((ROOT/'shared/source-contracts/profile-manifest.json').read_bytes())
        entry='#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nsys.path.insert(0,str(Path(__file__).resolve().parent))\nfrom installation_runtime import main\nraise SystemExit(main())\n'
        if admission: entry=entry.replace('from installation_runtime import main','from installation_runtime_v2 import main')
        (runtime/'octon').write_text(entry)
        (stage/'octon').write_text('#!/usr/bin/env python3\nimport runpy\nfrom pathlib import Path\nimport sys\nsys.dont_write_bytecode=True\nrunpy.run_path(str(Path(__file__).resolve().parent/".octon/runtime/octon"),run_name="__main__")\n')
        (stage/'WORKSPACE.md').write_text('Disposable Octon runtime qualification. Read AGENTS.md and .octon/agent/START_HERE.md.\n')
        manifest={'schema_version':reader.SCHEMA,'permission_grant':False,'status':'disposable_qualification_only',
                  'profile':'minimal','layout':'compact','source_revision':revision,'projection_version':'target-path-projection.v1',
                  'inventory_sha256':reader.digest((runtime/'profile-inventory.json').read_bytes()),
                  'required_dependencies':contract['required_dependencies'],'inputs':inputs,'assets':[], 'output_inventory':[]}
        if admission:
            manifest.update(schema_version=admission_reader.ADMISSION_SCHEMA,projection_version='target-path-projection.v2',required_dependencies=facet['required_dependencies'],admission_inventory_sha256=reader.digest((runtime/'admission-inventory.json').read_bytes()))
        # Refresh validates the actual paths before binding immutable runtime bytes.
        run([sys.executable,'-B',runtime/'scripts/refresh.py','--refresh'],stage)
        manifest['assets']=[{'path':path,'sha256':reader.digest((stage/path).read_bytes())}
                            for path in sorted(contract['runtime_paths']+[project_path(path.as_posix()) for path in schemas]+['.octon/runtime/installation_runtime.py','.octon/runtime/octon','octon'])]
        if admission:
            extra=[row['target'] for row in facet['assets']]+['.octon/runtime/admission-inventory.json']
            manifest['assets'] += [{'path':path,'sha256':reader.digest((stage/path).read_bytes())} for path in extra]
            manifest['assets'].sort(key=lambda row:row['path'])
        manifest['output_inventory']=output_inventory(stage)
        (stage/'.octon/manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        (admission_reader if admission else reader).inspect(stage)
        run([sys.executable,'-B',runtime/'scripts/refresh.py','--refresh'],stage)
        run([sys.executable,'-B',stage/'octon','check'],stage)
        if protected:
            if sys.platform != 'linux':raise ValueError('protected fixture execution profile is Linux-only')
            from protected_fixture import install
            install(stage)
            if durable:
                from durable_fixture import install as install_durable
                install_durable(stage)
            run([sys.executable,'-B',runtime/'scripts/refresh.py','--refresh'],stage)
            run([sys.executable,'-B',stage/'octon','check'],stage)
        if target.exists():
            target.rmdir()
        stage.rename(target)
    return manifest


def seed_source_binding():
    """Independent exact source binding supplied by the trusted suite owner."""
    paths=subprocess.check_output(['git','--no-optional-locks','ls-files','-z'],cwd=ROOT).decode().split('\0')
    return {'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'inputs':{path:reader.digest(admission_reader.confined(ROOT,path).read_bytes()) for path in paths if path}}


def keyless_seed_inventory(root):
    rows=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root).as_posix()
        admission_reader.confined(root,relative)
        if path.is_file():
            if path.suffix=='.pem' or path.name.startswith(('TASK-','DEC-','EVD-','RCPT-','WCR-')) and '/tests/fixtures/' not in '/'+relative:
                raise ValueError('keyless seed contains project record or credential')
            if '/transactions/' in '/'+relative or path.name in {'bootstrap.json','anchor.json','index.json','authority-owner.json','authority.json'}:
                raise ValueError('keyless seed contains authority/history/currentness state')
            if relative.endswith('/state/focus.json'):
                focus=reader.load(path)
                if focus.get('current_task_id') is not None or focus.get('handoff_summary') is not None or focus.get('updated_by') is not None:raise ValueError('keyless seed contains project operator facts')
            rows.append({'path':relative,'sha256':reader.digest(path.read_bytes()),'mode':stat.S_IMODE(path.stat().st_mode)})
    return rows


def create_keyless_seed(root,image_binding):
    """Compile only empty source snapshots; never an authority/recovery cache."""
    root=Path(root)
    if any(root.iterdir()):raise ValueError('fresh owned keyless seed required')
    source=seed_source_binding()
    generate(root/'plain')
    generate(root/'admission',admission=True)
    run([sys.executable,'-B',SCRIPTS/'scaffold_project.py','--target',root/'legacy','--project-name','Synthetic preserved record fixture','--profile','minimal','--layout','compact'],ROOT)
    record={'schema_version':'octon.keyless-fixture-seed.v1','permission_grant':False,'source':source,'image':image_binding,'files':keyless_seed_inventory(root)}
    # Returned record is independently retained by the host launch handle, not
    # recovered from a seed-side manifest. No ticket/key/actor state is here.
    return record


def materialize_keyless_seed(root,name,target,expected,image_binding):
    root=Path(root);target=Path(target)
    if set(expected)!={'schema_version','permission_grant','source','image','files'} or expected['schema_version']!='octon.keyless-fixture-seed.v1' or expected['permission_grant'] is not False:
        raise ValueError('unsupported closed keyless seed binding')
    if expected['source']!=seed_source_binding() or expected['image']!=image_binding or expected['files']!=keyless_seed_inventory(root):
        raise ValueError('seed differs from independently retained exact source/image/inventory')
    mounts=[line.split(' - ',1) for line in Path('/proc/self/mountinfo').read_text().splitlines()]
    if not any(left.split()[4]==str(root) and 'ro' in left.split()[5].split(',') and right.split()[0] in {'ext4','xfs'} for left,right in mounts):
        raise ValueError('keyless seed requires readonly owned kernel volume')
    if name not in {'plain','admission','legacy'} or target.exists():raise ValueError('fresh exact seed destination required')
    source=admission_reader.confined(root,name)
    shutil.copytree(source,target,symlinks=False)
    # Refresh/check current target state through its existing owner, never cache
    # the live acceptance/authority/fence/postimage evaluation.
    script='.agent/scripts/refresh.py' if name=='legacy' else '.octon/runtime/scripts/refresh.py'
    run([sys.executable,'-B',target/script,'--refresh'],target)
    if name!='legacy':
        (admission_reader if name=='admission' else reader).inspect(target)
        run([sys.executable,'-B',target/'octon','check'],target)
    return target



def output_inventory(stage):
    derived = {'.octon/agent/state/current.json','.octon/dossier/ARTIFACT_CATALOG.json',
               '.octon/dossier/MANIFEST.json','.octon/dossier/machine-readable/path-authority.json',
               '.octon/manifest.json'}
    paths = {p.relative_to(stage).as_posix():p for p in stage.rglob('*') if p.is_file()}
    paths.setdefault('.octon/manifest.json',stage/'.octon/manifest.json')
    return [{'path':value,'sha256':None if value in derived else reader.digest(path.read_bytes())}
            for value,path in sorted(paths.items())]



def admission_transaction_projection(text):
    support = r"""import fixture_admission as qualification_authority
_qualification_subject = None
_qualification_phase = 'effect'
_qualification_decisions = []
_qualification_evidence_write = None


def qualification_current(root, subject, phase):
    global _qualification_subject, _qualification_phase
    try:
        context=qualification_json_load(Path(os.environ['OCTON_FIXTURE_ADMISSION_CONTEXT']))
        if instruction_fingerprint(root)!=context['plan']['governing_instruction_fingerprint']:
            raise ValueError('governing instructions changed before effect/recovery')
        decision = qualification_authority.guarded(root, subject, phase)
        _qualification_decisions.append(decision)
    except Exception as error:
        refused = TransactionError('current fixture authority refused: '+str(error))
        pending_root=root/'.octon/agent/transactions/pending'
        if pending_root.is_dir() and any(pending_root.iterdir()):
            refused.report['mutation']={'occurred':True,'repository_paths':[], 'external_effects':[], 'statement':'A write-ahead journal remains. Local effects require exact current-authority reconciliation; no replay or non-effect claim.'}
        raise refused from error
    _qualification_subject = subject
    _qualification_phase = phase
    qualification_persist_observation(root, decision, phase)


def qualification_persist_observation(root, decision, phase):
    global _qualification_evidence_write
    context=qualification_json_load(Path(os.environ['OCTON_FIXTURE_ADMISSION_CONTEXT']))
    event={'schema_version':'octon.fixture-transaction-authority-observation.v1','permission_grant':False,
           'receipt_ref':context['record']['receipt_id'],'lineage_digest':qualification_authority.digest(qualification_authority.lineage(context['record'])),
           'phase':phase,'admission_evidence':decision}
    qualification_authority.validate_observation(event, context['record']['receipt_id'])
    qualification_authority.validate_evidence(context,decision,context['binding'])
    path=confined_path(root,'.octon/agent/transactions/evidence/'+event['receipt_ref']+'/'+qualification_authority.digest(event)+'.json')
    data=(json.dumps(event,indent=2,sort_keys=True)+'\n').encode('utf-8')
    if path.exists():
        if path.read_bytes()!=data:raise TransactionError('authority observation collision')
        return
    # A narrowly scoped metadata writer receives only these just-authenticated
    # bytes/path. It cannot exempt any other mutation or reconstruct authority.
    _qualification_evidence_write=(path.resolve(),data)
    try:
        write_new_json(path,event)
    finally:
        _qualification_evidence_write=None


def qualification_boundary(root, phase=None):
    context_path=os.environ.get('OCTON_FIXTURE_ADMISSION_CONTEXT')
    if not context_path:
        raise TransactionError('explicit fixture authority required')
    context=qualification_json_load(Path(context_path))
    if str(root.resolve()) != context['root']:
        return  # staging is isolated; the live operation owner guards its invocation
    qualification_current(root, _qualification_subject or context['plan'], phase or _qualification_phase)


"""
    text=text.replace('from installation_runtime import protected_paths, admit_work_plan, admit_recovery_record, load as qualification_json_load','from installation_runtime_v2 import protected_paths, admit_work_plan, admit_recovery_record, load as qualification_json_load')
    text=text.replace('def qualification_work_admission(',support+'def qualification_work_admission(')
    text=text.replace('        admit_work_plan(root, plan)', "        admit_work_plan(root, plan)\n        qualification_current(root, plan, 'prepare')")
    text=text.replace('        admit_recovery_record(root, record)', "        admit_recovery_record(root, record)\n        qualification_current(root, record, 'rollback' if record.get('status') in {'applied','rollback_in_progress'} else 'recover')")
    text=text.replace('    for item in plan["operations"]:\n        target = confined_path(root, item["path"])', '    for item in plan["operations"]:\n        qualification_boundary(root, "effect")\n        target = confined_path(root, item["path"])')
    text=text.replace('    for item in reversed(receipt_paths):', '    qualification_boundary(root, "recover")\n    for item in reversed(receipt_paths):\n        qualification_boundary(root, "recover")')
    text=text.replace('    path.parent.mkdir(parents=True, exist_ok=True)\n    temporary:', '    context_path=os.environ.get("OCTON_FIXTURE_ADMISSION_CONTEXT")\n    if context_path:\n        context=qualification_json_load(Path(context_path))\n        live=Path(context["root"])\n        if path.resolve().is_relative_to(live.resolve()) and _qualification_evidence_write != (path.resolve(),data):\n            relative=path.resolve().relative_to(live.resolve()).as_posix()\n            metadata={".octon/agent/transactions/{}/{}.json".format(kind,context["record"]["receipt_id"]) for kind in ["pending","receipts","recovered"]}\n            if relative not in {item["path"] for item in context["record"]["paths"]} and relative not in metadata:\n                raise TransactionError("write outside admitted transaction")\n            if relative in metadata:\n                candidate=qualification_authority.strict(data)\n                if candidate.get("permission_grant") is not False or qualification_authority.lineage(candidate)!=qualification_authority.lineage(context["record"]):\n                    raise TransactionError("metadata outside admitted transaction lineage")\n                if "/pending/" in relative and not path.exists() and any((live/".octon/agent/transactions"/kind/(context["record"]["receipt_id"]+".json")).exists() for kind in ["receipts","recovered"]):\n                    raise TransactionError("transaction identity already has terminal history")\n            for item in context["record"]["paths"]:\n                if item["path"]==relative and (sha256(data),bool(mode & 0o200) if os.name=="nt" else mode) not in {(item[key]["sha256"],bool(item[key]["mode"] & 0o200) if os.name=="nt" and item[key]["mode"] is not None else item[key]["mode"]) for key in ["before","after"]}:\n                    raise TransactionError("write content outside admitted pre/postimage")\n            qualification_boundary(live)\n    path.parent.mkdir(parents=True, exist_ok=True)\n    temporary:')
    text=text.replace('        for relative in plan["validation"]["declared_write_paths"]:', '        for relative in plan["validation"]["declared_write_paths"]:\n            qualification_boundary(root, "effect")')
    text=text.replace('    staged_outcomes, staged_results, stage_timings = _staged_result', '    qualification_boundary(root, "validate")\n    staged_outcomes, staged_results, stage_timings = _staged_result')
    text=text.replace('        validation_results.extend(\n            _run_post_apply_isolated(', '        qualification_boundary(root, "validate")\n        validation_results.extend(\n            _run_post_apply_isolated(')
    text=text.replace('    path = confined_path(\n        root, f".octon/agent/transactions/pending/{receipt_id}.json"', '    qualification_current(root, value, "effect")\n    path = confined_path(\n        root, f".octon/agent/transactions/pending/{receipt_id}.json"')
    text=text.replace('    pending, pending_path = _write_pending(', '    qualification_boundary(root, "effect")\n    pending, pending_path = _write_pending(')
    text=text.replace('        receipt_persist_started = time.perf_counter()', '        qualification_boundary(root, "finalize")\n        receipt_persist_started = time.perf_counter()')
    text=text.replace('    qualification_work_admission(root, plan)\n    LAST_PHASE_TIMINGS.clear()\n    LAST_PHASE_TIMINGS.update(', '    qualification_boundary(root, "finalize")\n    LAST_PHASE_TIMINGS.clear()\n    LAST_PHASE_TIMINGS.update(')
    text=text.replace('    qualification_work_admission(root, plan)\n    LAST_PHASE_TIMINGS.clear()\n    total_started', '    _qualification_decisions.clear()\n    qualification_work_admission(root, plan)\n    LAST_PHASE_TIMINGS.clear()\n    total_started')
    text=text.replace('\"validation\": validation_results,', '\"validation\": validation_results + [{\"schema_version\": \"octon.fixture-admission-evidence.v1\", \"fixture_only\": True, \"decisions\": list(_qualification_decisions)}],')
    lines=[]
    owner=''
    for line in text.splitlines(keepends=True):
        if line.startswith('def '): owner=line.split('def ',1)[1].split('(',1)[0]
        if line.lstrip().startswith('pending_path.unlink('):
            indent=line[:len(line)-len(line.lstrip())]
            phase='finalize' if owner=='apply_plan' else 'recover'
            lines.append(indent+f'qualification_boundary(root, {phase!r})\n')
        lines.append(line)
    text=''.join(lines)
    return text

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--disposable-qualification',action='store_true',required=True)
    parser.add_argument('--admission-qualification',action='store_true')
    parser.add_argument('--protected-fixture-qualification',action='store_true')
    parser.add_argument('--durable-fixture-qualification',action='store_true')
    args=parser.parse_args()
    try:
        result=generate(args.target,admission=args.admission_qualification,protected=args.protected_fixture_qualification,durable=args.durable_fixture_qualification)
        print(json.dumps({'status':result['status'],'source_revision':result['source_revision'],'assets':len(result['assets'])}))
        return 0
    except (ValueError,OSError,KeyError) as error:
        print('ERROR: '+str(error),file=sys.stderr)
        return 2

# Conversion is intentionally a source qualification API, not a consumer command.
def supported_mode(mode, host=os.name):
    """Use the host's actual chmod contract; Windows exposes read-only only."""
    return bool(mode & 0o200) if host == 'nt' else mode


def fixture_conversion_plan(target):
    """Plan one exact pristine-control Mini4.2→Octon5→disposable bridge fixture."""
    import upgrade_project as upgrade
    transaction = upgrade.TRANSACTION
    origin = reader.load(target/'.octon-origin.json')
    if (origin.get('product'), origin.get('octon_mini_version'), origin.get('profile'), origin.get('layout')) != ('octon','5.0.0','minimal','compact'):
        raise ValueError('unsupported fixture predecessor')
    history = origin.get('migration_history',[])
    if not history or history[-1].get('from_product') != 'octon-mini' or history[-1].get('from_version') != '4.2.0':
        raise ValueError('fixture requires the supported exact Mini4.2 identity conversion')
    reserved={'.octon','.octon-mini-origin.json','.project-blueprint-origin.json'}
    for path in target.iterdir():
        if path.name.casefold() in reserved:
            raise ValueError('mixed or colliding fixture installation')
    if (target/'.git').exists():
        raise ValueError('Git-backed or live consumer conversion is unqualified')
    if list((target/'.agent/transactions/pending').glob('*.json')):
        raise ValueError('pending predecessor must reconcile before conversion')
    for path in (target/'.agent').rglob('*.json'):
        if '/tests/fixtures/' in path.as_posix() or '/schemas/' in path.as_posix():
            continue
        value=reader.load(path)
        if isinstance(value,dict) and any(isinstance(value.get(key),str) and value[key] in {'attempted','outcome_unknown','unknown'} for key in ['state','outcome','effect_state']):
            raise ValueError('unknown predecessor effect requires original-owner reconciliation')
    project=reader.load(target/'.agent/project.json')
    if project['autonomous_delivery']['status'] != 'available_not_activated' or project['work_completion']['status'] != 'disabled':
        raise ValueError('activated or custom operating controls are unsupported')
    for directory in ['capabilities','workflows']:
        if (target/'.agent'/directory).exists():
            raise ValueError('optional installed package conversion is unqualified')
    inventory={item['path']:item for item in origin['installed_inventory']['paths']}
    # A custom control/verifier needs its own conversion. Records and instructions
    # are project-owned and are preserved separately below, never text-rewritten.
    controls=['.agent/policy.json','.agent/context.json','.agent/schema.json','.agent/lifecycle.json',
              '.agent/tools.json','.agent/validators.json','.agent/packages.json','.agent/scm.json']
    for value in controls+[p for p in inventory if p.startswith('.agent/scripts/')]:
        expected=inventory.get(value)
        if not expected or reader.digest((target/value).read_bytes()) != expected.get('sha256'):
            raise ValueError('custom control or verifier conversion unsupported: '+value)
    supported_authored={
        'AGENTS.md','.agent/state/focus.json','.agent/decisions/governance-register.json',
        '.agent/decisions/reuse-policy.json','project-dossier/machine-readable/artifact-registry.json'}
    derived_predecessor={'.agent/state/current.json','project-dossier/ARTIFACT_CATALOG.json',
                         'project-dossier/MANIFEST.json','project-dossier/machine-readable/path-authority.json'}
    for relative,expected in inventory.items():
        path=target/relative
        if relative in derived_predecessor or relative=='.octon-origin.json':
            continue
        if not path.is_file() or path.is_symlink():
            raise ValueError('missing or unsafe predecessor inventory dependency: '+relative)
        if relative=='.agent/project.json':
            # The existing identity upgrader's reviewed version-only merge is
            # checked against canonical configuration after rendering below.
            continue
        supported=relative in supported_authored or (relative.startswith('project-dossier/') and relative.endswith('.md'))
        if not supported and (expected.get('sha256') is None or reader.digest(path.read_bytes()) != expected['sha256']):
            raise ValueError('modified recognized predecessor row requires separate qualification: '+relative)

    with tempfile.TemporaryDirectory(prefix='octon-conversion-candidate-') as temporary:
        candidate=Path(temporary)/'target'
        generated=set(inventory) | {'.octon-origin.json'}
        record_prefixes=('.agent/tasks/TASK-','.agent/plans/PLAN-','.agent/evidence/EVD-',
                         '.agent/handoffs/','.agent/decisions/DEC-','.agent/transactions/')
        for path in target.rglob('*'):
            if path.is_symlink():
                raise ValueError('symlink fixture input is unsupported')
            if path.is_file():
                relative=path.relative_to(target).as_posix()
                if relative not in generated and not relative.startswith(record_prefixes):
                    raise ValueError('unclassified project content requires separate qualification: '+relative)
                expected=inventory.get(relative)
                expected_mode=expected.get('mode') if expected else (0o600 if relative.startswith('.agent/transactions/') else 0o644)
                if expected_mode is not None and supported_mode(path.stat().st_mode & 0o777) != supported_mode(expected_mode):
                    raise ValueError('fixture mode drift requires separate qualification: '+relative)
        generate(candidate,origin['project_name'])
        if json.loads(project_text(json.dumps(project))) != reader.load(candidate/'.octon/agent/project.json'):
            raise ValueError('custom project configuration conversion unsupported')
        before={path.relative_to(target).as_posix():path for path in target.rglob('*') if path.is_file()}
        # Preserve byte-exact project instructions, documents and immutable records.
        record_prefixes=('.agent/tasks/','.agent/plans/','.agent/evidence/','.agent/handoffs/','.agent/decisions/DEC-')
        preserved=[]
        for value,path in before.items():
            if value == 'AGENTS.md' or value.startswith(record_prefixes) or (value.startswith('project-dossier/') and value.endswith('.md')) or value in ['.agent/policy.json','.agent/state/focus.json','.agent/decisions/governance-register.json','.agent/decisions/reuse-policy.json']:
                destination=candidate/project_path(value)
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(path.read_bytes())
                shutil.copymode(path,destination)
                preserved.append(value)
        # The existing origin/history is retained byte-exact. The new installation
        # manifest owns target bindings; no historical origin is reinterpreted.
        projected_origin = json.loads(json.dumps(origin))
        projected_origin['generated_paths'] = [project_path(value) for value in origin['generated_paths']]
        for item in projected_origin['installed_inventory']['paths']:
            item['path'] = project_path(item['path'])
            if item.get('sha256') is not None and (candidate/item['path']).is_file():
                item['sha256'] = reader.digest((candidate/item['path']).read_bytes())
        (candidate/'.octon-origin.json').write_text(json.dumps(projected_origin,indent=2,sort_keys=True)+'\n')
        registry = reader.load(target/'project-dossier/machine-readable/artifact-registry.json')
        for representation in registry['representations']:
            representation['path'] = project_path(representation['path'])
        (candidate/'.octon/dossier/machine-readable/artifact-registry.json').write_text(json.dumps(registry,indent=2,sort_keys=True)+'\n')
        # Every predecessor byte, including path-bearing controls, source maps,
        # provenance and receipts, is immutable conversion evidence in archive.
        for value,path in before.items():
            archived=candidate/'.octon/archive/predecessor'/value
            archived.parent.mkdir(parents=True,exist_ok=True)
            archived.write_bytes(path.read_bytes())
            shutil.copymode(path,archived)
        manifest=reader.load(candidate/'.octon/manifest.json')
        manifest['output_inventory']=output_inventory(candidate)
        (candidate/'.octon/manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        # Control mapping is admitted only for exact-pristine predecessor controls.
        # Target copies come from canonical rendering, and every original is retained.
        run([sys.executable,'-B',candidate/'.octon/runtime/scripts/refresh.py','--refresh'],candidate)
        run([sys.executable,'-B',candidate/'octon','check'],candidate)
        derived=['.octon/agent/state/current.json','.octon/dossier/ARTIFACT_CATALOG.json',
                 '.octon/dossier/MANIFEST.json','.octon/dossier/machine-readable/path-authority.json']
        operations=[]
        after={p.relative_to(candidate).as_posix():p for p in candidate.rglob('*') if p.is_file()}
        for value in sorted(set(before)|set(after)):
            if value in derived:
                continue
            old=before.get(value);new=after.get(value)
            if old and new and old.read_bytes()==new.read_bytes():
                continue
            action='replace' if old and new else 'delete' if old else 'create'
            operations.append(transaction.operation(action,value,new.read_bytes() if new else None,
                                                   'Exact disposable path projection with preserved predecessor archive.',
                                                   mode=(new.stat().st_mode & 0o777) if new else None))
        return transaction.build_plan(target,operation_name='qualification.convert_fixture',
            scope='Exact pristine-control minimal/compact Mini4.2→5.0→disposable target fixture only',
            operations=operations,evidence=[transaction.source_evidence('fixture_authority','authority:current-user-bounded-disposable-fixture')],
            assumptions=['Direct invocation authorizes this disposable fixture only.'],confidence='exact',
            limitations=['No live adoption. Historical plans/receipts are read-only archive; no replay under target paths.',
                         'The conversion receipt remains in .agent/transactions as an explicit predecessor recovery capsule, not live work state.',
                         'Custom controls, installed packages, grants, pending outcomes and other profiles are unsupported.'],
            staged_validation_plan=[[sys.executable,'-B','.octon/runtime/scripts/refresh.py','--refresh'],[sys.executable,'-B','octon','check']],
            post_apply_validation_plan=[[sys.executable,'-B','octon','check']],derived_write_paths=derived,
            evidence_paths=sorted(before))

if __name__=='__main__':
    sys.dont_write_bytecode=True
    raise SystemExit(main())
