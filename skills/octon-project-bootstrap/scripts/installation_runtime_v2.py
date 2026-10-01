#!/usr/bin/env python3
"""Independent, non-authorizing disposable installation reader (stdlib only)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

SCHEMA = 'octon.disposable-installation.v1'
ADMISSION_SCHEMA = 'octon.disposable-installation.v2'
CONTRACT = 'octon.source.disposable-runtime.v1'
MODULES = {'octon.py','octon_autonomous_delivery.py','octon_continuation.py','octon_doctor.py',
           'octon_transaction.py','octon_work_completion.py','refresh.py','run_project_checks.py','validate.py'}


FACET_SOURCES = {'skills/octon-project-bootstrap/scripts/fixture_admission.py':'.octon/runtime/fixture_admission.py','skills/octon-project-bootstrap/scripts/governance_shadow.py':'.octon/runtime/authority/scripts/governance_shadow.py','skills/octon-project-bootstrap/scripts/validate_source_contracts.py':'.octon/runtime/authority/scripts/validate_source_contracts.py','shared/source-contracts/governance-foundation-v2.schema.json':'.octon/runtime/authority/shared/source-contracts/governance-foundation-v2.schema.json','skills/octon-project-bootstrap/scripts/installation_runtime_v2.py':'.octon/runtime/installation_runtime_v2.py'}

def validate_admission_inventory(facet):
    fields={'schema_version','status','permission_grant','installation_schema','required_dependencies','assets'}
    if not isinstance(facet,dict) or set(facet)!=fields or facet['schema_version']!='octon.source.admission-fixture-inventory.v1' or facet['status']!='source_only_disposable_qualification' or facet['permission_grant'] is not False or facet['installation_schema']!=ADMISSION_SCHEMA or facet['required_dependencies']!=['python>=3.11','canonical-minimal-core','openssl-ed25519']:
        raise ValueError('unsupported closed admission inventory')
    assets=facet['assets']
    if not isinstance(assets,list) or any(set(row)!={'source','target'} for row in assets) or {row['source']:row['target'] for row in assets} != FACET_SOURCES or len(assets)!=len(FACET_SOURCES):
        raise ValueError('unsupported canonical admission assets')
    return facet



def pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError(f'duplicate JSON key: {key}')
        value[key] = item
    return value


def load(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)+'\n').encode()


def confined(root, value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('invalid portable installation path')
    parts = value.split('/')
    if any(part in {'', '.', '..'} or part[-1:] in {' ', '.'} or
           re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part)
           for part in parts) or PurePosixPath(value).is_absolute():
        raise ValueError('invalid portable installation path')
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('installation path escapes project')
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('installation symlink is unsupported')
    return path


def inspect(root):
    manifest = load(confined(root, '.octon/manifest.json'))
    fields = {'schema_version','permission_grant','status','profile','layout','source_revision',
              'projection_version','inventory_sha256','required_dependencies','assets','inputs', 'output_inventory'}
    admission = isinstance(manifest,dict) and manifest.get('schema_version') == ADMISSION_SCHEMA
    if admission: fields.add('admission_inventory_sha256')
    if not isinstance(manifest, dict) or set(manifest) != fields or manifest['schema_version'] not in {SCHEMA,ADMISSION_SCHEMA}:
        raise ValueError('unsupported installation manifest version or fields')
    if manifest['permission_grant'] is not False or manifest['status'] != 'disposable_qualification_only':
        raise ValueError('installation cannot claim permission or activation')
    if (manifest['profile'], manifest['layout'], manifest['projection_version']) != ('minimal','compact','target-path-projection.v2' if admission else 'target-path-projection.v1'):
        raise ValueError('unsupported installation selection')
    if not re.fullmatch('[a-f0-9]{40}', manifest['source_revision']):
        raise ValueError('invalid exact source revision')
    inventory_path = confined(root, '.octon/runtime/profile-inventory.json')
    if digest(inventory_path.read_bytes()) != manifest['inventory_sha256']:
        raise ValueError('canonical inventory binding mismatch')
    inventory = load(inventory_path)
    inventory_fields = {'schema_version','document_role','permission_grant','profiles','layouts',
                        'installation_bindings','project_paths','packages','acceptance_criteria',
                        'documentation_projections','default_disposition','inventory_hash_algorithm',
                        'rules','forbidden_outputs','limitations','disposable_runtime'}
    if not isinstance(inventory,dict) or set(inventory) != inventory_fields or inventory.get('permission_grant') is not False or inventory.get('default_disposition') != 'source_only':
        raise ValueError('invalid closed canonical inventory')
    if inventory['installation_bindings']['target']['generation_status'] != 'design_only_not_selectable':
        raise ValueError('ordinary target generation must remain inactive')
    contract = inventory.get('disposable_runtime')
    if not isinstance(contract, dict) or contract.get('schema_version') != CONTRACT:
        raise ValueError('unsupported qualification inventory')
    if inventory.get('schema_version') != 'octon.source.profile-manifest.v3':
        raise ValueError('unsupported canonical inventory version')
    expected_fields = {'schema_version','status','permission_grant','profile','layout','projection_version','required_dependencies','runtime_paths'}
    if set(contract) != expected_fields or contract['status'] != 'qualification_only_not_selectable' or contract['permission_grant'] is not False or (contract['profile'],contract['layout'],contract['projection_version']) != ('minimal','compact','target-path-projection.v1'):
        raise ValueError('invalid closed qualification inventory')
    # Resolve mandatory copied modules from reviewed canonical generation rules.
    paths = sorted('.octon/runtime/scripts/'+Path(path).name[:-5]
                   for rule in inventory['rules'] if rule.get('disposition') == 'generated' and 'minimal' in rule.get('profiles',[])
                   for path in rule.get('inventory_paths',[]) if path.startswith('.agent/scripts/') and path.endswith('.py.tmpl'))
    if {Path(path).name for path in paths} != MODULES or contract['runtime_paths'] != paths or len(paths) != len(set(paths)):
        raise ValueError('canonical runtime dependency inventory differs')
    if contract['required_dependencies'] != ['python>=3.11','canonical-minimal-core']:
        raise ValueError('unsupported required dependency')
    extra_assets = []
    dependencies = contract['required_dependencies']
    if admission:
        extra_path=confined(root,'.octon/runtime/admission-inventory.json')
        if digest(extra_path.read_bytes()) != manifest['admission_inventory_sha256']:
            raise ValueError('admission inventory binding mismatch')
        facet=load(extra_path)
        if set(facet) != {'schema_version','status','permission_grant','installation_schema','required_dependencies','assets'} or facet['schema_version'] != 'octon.source.admission-fixture-inventory.v1' or facet['status'] != 'source_only_disposable_qualification' or facet['permission_grant'] is not False or facet['installation_schema'] != ADMISSION_SCHEMA:
            raise ValueError('unsupported admission inventory')
        dependencies=['python>=3.11','canonical-minimal-core','openssl-ed25519']
        if facet['required_dependencies'] != dependencies:
            raise ValueError('unsupported admission dependency')
        validate_admission_inventory(facet)
        extra_assets=[item['target'] for item in facet['assets']]+['.octon/runtime/admission-inventory.json']
    if manifest['required_dependencies'] != dependencies:
        raise ValueError('required dependency resolution mismatch')
    if sys.version_info < (3,11):
        raise ValueError('Python 3.11 or newer required')
    assets = manifest['assets']
    schema_rules = [rule for rule in inventory['rules'] if rule.get('id') == 'shared-kernel-schemas'
                    and rule.get('disposition') == 'generated' and 'minimal' in rule.get('profiles',[])]
    if len(schema_rules) != 1 or schema_rules[0]['output'] != {'root':'.agent/schemas','strip_suffix':None}:
        raise ValueError('canonical schema dependency rule differs')
    schema_paths = ['.octon/agent/schemas/'+path for path in schema_rules[0]['inventory_paths']]
    if not {'.octon/agent/schemas/harness-kernel.schema.json','.octon/agent/schemas/harness-record.schema.json'}.issubset(schema_paths):
        raise ValueError('required verifier schema dependency is absent')
    copied_paths = []
    for rule in inventory['rules']:
        if rule.get('disposition') == 'generated' and 'minimal' in rule.get('profiles',[]) and rule['output']['strip_suffix'] is None:
            for path in rule['inventory_paths']:
                value = rule['output']['root']+'/'+path
                copied_paths.append(value.replace('.agent/', '.octon/agent/',1))
    expected = extra_assets + contract['runtime_paths'] + copied_paths + ['.octon/runtime/installation_runtime.py','.octon/runtime/octon','octon']
    if not isinstance(assets, list) or [item.get('path') for item in assets] != sorted(expected):
        raise ValueError('runtime asset inventory mismatch')
    for item in assets:
        if set(item) != {'path','sha256'} or not re.fullmatch('[a-f0-9]{64}',item['sha256']):
            raise ValueError('invalid runtime asset binding')
        path = confined(root,item['path'])
        if not path.is_file() or digest(path.read_bytes()) != item['sha256']:
            raise ValueError('missing or mismatched required asset: '+item['path'])
    if manifest['inputs'] == [] or manifest['output_inventory'] == []:
        raise ValueError('missing generation inventory')
    derived = {'.octon/agent/state/current.json','.octon/dossier/ARTIFACT_CATALOG.json',
               '.octon/dossier/MANIFEST.json','.octon/dossier/machine-readable/path-authority.json',
               '.octon/manifest.json'}
    for field in ['inputs','output_inventory']:
        items = manifest[field]
        if not isinstance(items,list) or len({item['path'] for item in items}) != len(items):
            raise ValueError('duplicate generation inventory path')
        for item in items:
            if set(item) != {'path','sha256'}:
                raise ValueError('invalid generation asset binding')
            if not (field == 'output_inventory' and item['path'] in derived and item['sha256'] is None) and not re.fullmatch('[a-f0-9]{64}',str(item['sha256'])):
                raise ValueError('invalid generation asset digest')
            confined(root,item['path'])
    if admission:
        sys.path.insert(0,str(root/'.octon/runtime'))
        from fixture_admission import openssl
        openssl()
    observations=root/'.octon/agent/transactions/evidence'
    if admission and observations.exists():
        from fixture_admission import validate_observation, digest as record_digest
        if observations.is_symlink():raise ValueError('unsafe transaction evidence directory')
        for event_path in observations.rglob('*'):
            relative=event_path.relative_to(root).as_posix();confined(root,relative)
            if event_path.is_file():
                value=load(event_path);validate_observation(value,event_path.parent.name)
                if event_path.name!=record_digest(value)+'.json':raise ValueError('authority observation content address mismatch')
    return manifest


def protected_paths(root):
    return sorted([str(path.relative_to(root)).replace('\\','/') for directory in
                   (root/'.octon/runtime', root/'.octon/agent') for path in directory.glob('*.json')]
                  + [str(path.relative_to(root)).replace('\\','/') for path in (root/'.octon/runtime/scripts').glob('*.py')]
                  + [str(path.relative_to(root)).replace('\\','/') for directory in
                     (root/'.octon/agent/schemas',root/'.octon/agent/diagnostics',root/'.octon/agent/decisions')
                     for path in directory.rglob('*.json')]
                  + [p.relative_to(root).as_posix() for p in (root/'.octon/runtime/authority').rglob('*') if p.is_file()]
                  + ([ '.octon/runtime/admission-inventory.json','.octon/runtime/fixture_admission.py','.octon/runtime/installation_runtime_v2.py'] if (root/'.octon/runtime/fixture_admission.py').exists() else [])
                  + ['AGENTS.md','.octon/manifest.json','.octon/runtime/installation_runtime.py','.octon-origin.json'])


WORK_OPERATIONS = {'work.start','work.block','work.handoff'}
DERIVED_PATHS = ['.octon/agent/state/current.json','.octon/dossier/ARTIFACT_CATALOG.json',
                 '.octon/dossier/MANIFEST.json','.octon/dossier/machine-readable/path-authority.json']


def work_path(root, path, operation):
    confined(root,path)
    if path == '.octon/agent/state/focus.json':
        return True
    return operation != 'work.handoff' and re.fullmatch(
        r'\.octon/agent/(?:tasks/TASK|plans/PLAN)-[0-9]{4}\.md',path) is not None


def admit_recovery_record(root, record):
    operation = record.get('operation')
    if operation not in WORK_OPERATIONS:
        raise ValueError('unsupported qualification recovery operation')
    for item in record['paths']:
        path = item['path']
        confined(root,path)
        if path not in DERIVED_PATHS and not work_path(root,path,operation):
            raise ValueError('unauthorized qualification recovery control/verifier path: '+path)
    permitted_directories={'.octon/agent/tasks','.octon/agent/plans','.octon/agent/state',
                           '.octon/dossier/machine-readable'}
    for directory in record.get('created_directories',[]):
        confined(root,directory)
        if directory not in permitted_directories:
            raise ValueError('unauthorized qualification recovery directory: '+directory)


def admit_work_plan(root, plan):
    if plan.get('operation') not in WORK_OPERATIONS:
        raise ValueError('qualification admits only local work plans')
    for item in plan['operations']:
        path = item['path']
        confined(root,path)
        if not work_path(root,path,plan['operation']):
            raise ValueError('unauthorized qualification control/verifier operation: '+path)
    validation = plan['validation']
    if validation['declared_write_paths'] != DERIVED_PATHS or validation['external_effects'] != [] or validation['shell_interpretation'] is not False:
        raise ValueError('unauthorized qualification derived/control operation')
    expected_check = [sys.executable,'-B','.octon/runtime/scripts/validate.py','--check']
    expected_refresh = [sys.executable,'-B','.octon/runtime/scripts/refresh.py','--refresh']
    if validation['staged_argv'] != [expected_refresh,expected_check] or validation['post_apply_argv'] != [expected_check]:
        raise ValueError('unauthorized qualification verifier command')
    bound = {item['path'] for item in plan['evidence_preimages']}
    if not set(protected_paths(root)).issubset(bound):
        raise ValueError('prior control/verifier baseline is not bound')


def main():
    root = Path(__file__).resolve().parents[2]
    try:
        manifest = inspect(root)
        args = sys.argv[1:]
        if args == ['installation','inspect']:
            print(json.dumps({'schema_version':manifest['schema_version'],'status':manifest['status'],
                              'source_revision':manifest['source_revision'],'required_dependencies':manifest['required_dependencies'],
                              'runtime_assets':len(manifest['assets']), 'execution_authority':False}, sort_keys=True))
            return 0
        if args[:2] == ['transaction','apply']:
            if '--plan' not in args:
                raise ValueError('exact work plan is required')
            admit_work_plan(root, load(Path(args[args.index('--plan')+1])))
        if not (args == ['check'] or args[:1] == ['doctor'] or args[:2] in
                (['work','start'],['work','block'],['work','handoff'],['work','resume'],
                 ['transaction','apply'],['transaction','recover'],['transaction','rollback'])):
            raise ValueError('command outside disposable qualification boundary')
        dispatcher = root/'.octon/runtime/scripts/octon.py'
        result = subprocess.run([sys.executable,'-B',str(dispatcher),*args],cwd=root,check=False,shell=False)
        return result.returncode
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('ERROR: disposable installation refused: '+str(error),file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.dont_write_bytecode = True
    raise SystemExit(main())
