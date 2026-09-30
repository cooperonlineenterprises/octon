#!/usr/bin/env python3
"""Explicit source-only, disposable target packaging; never a production installer."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import installation_runtime as reader
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


def generate(target, project_name='Disposable Runtime Fixture'):
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
    inputs = [{'path':str(path.relative_to(ROOT)), 'sha256':reader.digest(path.read_bytes())}
              for path in sorted(source_inputs)]
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
                        text = text.replace('ROOT = Path(__file__).resolve().parents[3]', 'import sys\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom installation_runtime import protected_paths, admit_work_plan\nROOT = Path(__file__).resolve().parents[3]')
                        text = text.replace('LAST_PHASE_TIMINGS.clear()', 'admit_work_plan(root, plan)\n    LAST_PHASE_TIMINGS.clear()')
                        text = text.replace('root = root.resolve()\n    if not operations:', 'root = root.resolve()\n    if operation_name.startswith("work."):\n        evidence_paths = list(dict.fromkeys([*(evidence_paths or []), *protected_paths(root)]))\n    if not operations:')
                    if relative == '.agent/scripts/octon.py':
                        text = text.replace('_CURRENT_DISPATCHER_PARENT_INDEX = "2"','_CURRENT_DISPATCHER_PARENT_INDEX = "3"')
                destination.write_text(text,encoding='utf-8')
                shutil.copymode(path,destination)
        runtime=stage/'.octon/runtime'
        shutil.copy2(SCRIPTS/'installation_runtime.py',runtime/'installation_runtime.py')
        (runtime/'profile-inventory.json').write_bytes((ROOT/'shared/source-contracts/profile-manifest.json').read_bytes())
        entry='#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nsys.path.insert(0,str(Path(__file__).resolve().parent))\nfrom installation_runtime import main\nraise SystemExit(main())\n'
        (runtime/'octon').write_text(entry)
        (stage/'octon').write_text('#!/usr/bin/env python3\nimport runpy\nfrom pathlib import Path\nimport sys\nsys.dont_write_bytecode=True\nrunpy.run_path(str(Path(__file__).resolve().parent/".octon/runtime/octon"),run_name="__main__")\n')
        (stage/'WORKSPACE.md').write_text('Disposable Octon runtime qualification. Read AGENTS.md and .octon/agent/START_HERE.md.\n')
        manifest={'schema_version':reader.SCHEMA,'permission_grant':False,'status':'disposable_qualification_only',
                  'profile':'minimal','layout':'compact','source_revision':revision,'projection_version':'target-path-projection.v1',
                  'inventory_sha256':reader.digest((runtime/'profile-inventory.json').read_bytes()),
                  'required_dependencies':contract['required_dependencies'],'inputs':inputs,'assets':[], 'output_inventory':[]}
        # Refresh validates the actual paths before binding immutable runtime bytes.
        run([sys.executable,'-B',runtime/'scripts/refresh.py','--refresh'],stage)
        manifest['assets']=[{'path':path,'sha256':reader.digest((stage/path).read_bytes())}
                            for path in sorted(contract['runtime_paths']+[project_path(path.as_posix()) for path in schemas]+['.octon/runtime/installation_runtime.py','.octon/runtime/octon','octon'])]
        manifest['output_inventory']=output_inventory(stage)
        (stage/'.octon/manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        reader.inspect(stage)
        run([sys.executable,'-B',runtime/'scripts/refresh.py','--refresh'],stage)
        run([sys.executable,'-B',stage/'octon','check'],stage)
        if target.exists():
            target.rmdir()
        stage.rename(target)
    return manifest



def output_inventory(stage):
    derived = {'.octon/agent/state/current.json','.octon/dossier/ARTIFACT_CATALOG.json',
               '.octon/dossier/MANIFEST.json','.octon/dossier/machine-readable/path-authority.json',
               '.octon/manifest.json'}
    paths = {p.relative_to(stage).as_posix():p for p in stage.rglob('*') if p.is_file()}
    paths.setdefault('.octon/manifest.json',stage/'.octon/manifest.json')
    return [{'path':value,'sha256':None if value in derived else reader.digest(path.read_bytes())}
            for value,path in sorted(paths.items())]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--disposable-qualification',action='store_true',required=True)
    args=parser.parse_args()
    try:
        result=generate(args.target)
        print(json.dumps({'status':result['status'],'source_revision':result['source_revision'],'assets':len(result['assets'])}))
        return 0
    except (ValueError,OSError,KeyError) as error:
        print('ERROR: '+str(error),file=sys.stderr)
        return 2

# Conversion is intentionally a source qualification API, not a consumer command.
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
                if expected_mode is not None and path.stat().st_mode & 0o777 != expected_mode:
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
