#!/usr/bin/env python3
"""Caller-pinned runtime provenance data; never authorization or target execution.

The source qualifier owns creation. This module has no target import, hook or
refresh path. The historical-v3 adapter is explicit data compatibility, not
retagging of the current inventory.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys

SOURCE_SCHEMA = 'octon.source.profile-manifest.v4'
TARGET_SCHEMA = 'octon.source.target-installation-manifest.v2'
BINDING_SCHEMA = 'octon.source.runtime-binding.v1'
FACET_SCHEMA = 'octon.runtime-distribution-manifest.v1'
PARENT_SCHEMA = 'octon.disposable-installation.v1'
HISTORICAL_SCHEMA = 'octon.source.profile-manifest.v3'
HISTORICAL_SOURCE = 'shared/source-contracts/historical/profile-manifest-v3.json'
HISTORICAL_SHA = 'd3b9b33d7136d9806b1839ec198929625bd3a4523a72948d43c925f8bc6916d3'
QUALIFIER_SOURCE = 'skills/octon-project-bootstrap/scripts/qualify_disposable_runtime.py'
READER_SOURCE = 'skills/octon-project-bootstrap/scripts/runtime_binding.py'
SCHEMA_SOURCES = ['shared/source-contracts/profile-manifest-v4.schema.json', 'shared/source-contracts/runtime-binding-v1.schema.json']
RECIPE_RULES = {'runtime.manifest': 'qualified-runtime-manifest', 'runtime.entry': 'qualified-runtime-entry'}
TARGET_PATHS = {'runtime.manifest': '.octon/runtime/manifest.json', 'runtime.entry': '.octon/runtime/octon'}
DERIVED_REFRESH_PATHS = {
    '.octon/agent/state/current.json', '.octon/dossier/ARTIFACT_CATALOG.json',
    '.octon/dossier/MANIFEST.json', '.octon/dossier/machine-readable/path-authority.json',
}
SOURCE_LIMITATIONS = [
    'Only two runtime entries and the existing nine copied modules have source-only binding qualification.',
    'Remaining target entries are unqualified; this inventory cannot select ordinary target generation or migration.',
]
MAX_BYTES = 2 * 1024 * 1024
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
RESERVED_WINDOWS = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{prefix}{number}' for prefix in ('COM', 'LPT') for number in range(1, 10)}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> bytes:
    """New canonical payload bytes use UTF-8/LF with final LF, not file identity."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def inventory_digest(value: object) -> str:
    """Retained target inventory convention has NO final newline."""
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8'))


def strict_json(data: bytes):
    if len(data) > MAX_BYTES:
        raise ValueError('bounded metadata size exceeded')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate metadata member')
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('nonfinite metadata number')
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)


def exact_fields(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(label + ': unsupported closed fields')


def same_json(value, expected):
    """Preserve JSON scalar types: false is not zero; three is not 3.0."""
    return canonical_json(value) == canonical_json(expected)


def digest_value(value, label):
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ValueError(label + ': expected raw SHA-256 string')
    return value


def path_records(value, label, *, nullable=False):
    if not isinstance(value, list) or not value:
        raise ValueError(label + ': nonempty path records required')
    names = []
    for row in value:
        exact_fields(row, {'path', 'sha256'}, label)
        portable_path(row['path'])
        names.append(row['path'])
        if row['sha256'] is not None or not nullable:
            digest_value(row['sha256'], label)
    if names != sorted(names) or len({name.casefold() for name in names}) != len(names):
        raise ValueError(label + ': duplicate, casefold collision or unordered path inventory')
    return names


def portable_path(value) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or any(ord(c) < 32 or c in '<>"|?*' for c in value):
        raise ValueError('invalid portable relative path')
    parts = value.split('/')
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive or PureWindowsPath(value).root or any(part in {'', '.', '..'} or part.endswith((' ', '.')) for part in parts):
        raise ValueError('unsafe portable relative path')
    if any(part.split('.', 1)[0].rstrip(' ').upper() in RESERVED_WINDOWS for part in parts):
        raise ValueError('reserved native path')
    return tuple(parts)


def reparse(info) -> bool:
    return bool(getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def native_mode(info):
    return {'model': 'windows_writable', 'writable': bool(info.st_mode & stat.S_IWRITE)} if os.name == 'nt' else {'model': 'posix_bits', 'bits': stat.S_IMODE(info.st_mode)}


class ReadOnlyTargetBinding:
    """Occupied explicit-root resolver; not a generation/adoption permission."""
    def __init__(self, root: Path, *, layout_id: str, state_owner: str):
        if layout_id != 'oep1_target' or state_owner != 'embedded':
            raise ValueError('only explicit target layout with one embedded state is qualified')
        root = Path(root)
        if not root.is_absolute() or root == Path(root.anchor):
            raise ValueError('explicit non-filesystem project root required')
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or reparse(info) or root.is_symlink():
            raise ValueError('project root must be a regular unambiguous directory')
        if root.resolve() != root:
            raise ValueError('canonical project root spelling required')
        current = Path(root.anchor)
        for part in root.parts[1:]:
            matches = [item for item in current.iterdir() if item.name.casefold() == part.casefold()]
            if len(matches) != 1 or matches[0].name != part:
                raise ValueError('project root component spelling/case differs')
            current = matches[0]; component = current.lstat()
            if not stat.S_ISDIR(component.st_mode) or stat.S_ISLNK(component.st_mode) or reparse(component):
                raise ValueError('project root component symlink/reparse/type is unsupported')
        self.root = root

    def path(self, relative: str, *, file: bool = True) -> Path:
        parts = portable_path(relative)
        current = self.root
        for index, part in enumerate(parts):
            matches = [entry for entry in current.iterdir() if entry.name.casefold() == part.casefold()]
            if len(matches) != 1 or matches[0].name != part:
                raise ValueError('missing path or ambiguous component spelling/case')
            current = matches[0]
            info = current.lstat()
            if current.is_symlink() or reparse(info):
                raise ValueError('symlink/junction/reparse path is not qualified')
            needed_file = file and index == len(parts) - 1
            if not (stat.S_ISREG(info.st_mode) if needed_file else stat.S_ISDIR(info.st_mode)):
                raise ValueError('unexpected path component type')
        return current

    def read(self, relative: str) -> bytes:
        path = self.path(relative)
        before = path.lstat()
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or reparse(opened) or opened.st_size > MAX_BYTES or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise ValueError('metadata object identity/type/size changed')
            with os.fdopen(descriptor, 'rb', closefd=False) as handle:
                data = handle.read(MAX_BYTES + 1)
            after = path.lstat()
            if (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns) or len(data) > MAX_BYTES:
                raise ValueError('target changed during read-only inspection')
            return data
        finally:
            os.close(descriptor)


def occupied_casefold(root, relative):
    """Non-following occupancy: aliases and dangling objects cannot mean absence."""
    current = Path(root)
    parts = portable_path(relative)
    for index, part in enumerate(parts):
        matches = [entry for entry in current.iterdir() if entry.name.casefold() == part.casefold()]
        if not matches:
            return False
        if index == len(parts)-1:
            return True
        if len(matches)!=1 or matches[0].name!=part:
            return True
        current = matches[0]; info=current.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or reparse(info):
            return True
    return False


def recipe_rule(identifier):
    source = 'skill:scripts/runtime_binding.py' if identifier == RECIPE_RULES['runtime.manifest'] else 'skill:scripts/qualify_disposable_runtime.py'
    return {'id': identifier, 'source': source, 'match': 'exact',
            'suffix': None, 'disposition': 'source_only', 'profiles': [], 'inventory_paths': None,
            'inventory_count': None, 'inventory_paths_sha256': None, 'output': None,
            'reason': 'Source-only disposable runtime binding recipe; not ordinary generation or activation.'}


def historical_compatibility_policy(current, historical_bytes: bytes):
    """Reject semantic drift beyond precisely named v4 qualification additions."""
    if sha256(historical_bytes) != HISTORICAL_SHA:
        raise ValueError('historical inventory bytes differ from the retained baseline')
    historical = strict_json(historical_bytes)
    if not isinstance(historical,dict) or historical.get('schema_version') != HISTORICAL_SCHEMA:
        raise ValueError('historical source shape/version differs')
    exact_fields(current, set(historical) | {'runtime_binding'}, 'current source shape')
    if current['schema_version'] != SOURCE_SCHEMA:
        raise ValueError('explicit current-v4/historical-v3 compatibility route required')
    binding = current['runtime_binding']
    if not isinstance(binding,dict):
        raise ValueError('source runtime binding: object required')
    if binding.get('schema_version') != BINDING_SCHEMA or binding.get('status') != 'qualification_only_not_selectable' or binding.get('permission_grant') is not False:
        raise ValueError('runtime binding cannot claim selection or permission')
    exact_fields(current['installation_bindings'], set(historical['installation_bindings']), 'current installation bindings shape')
    target = current['installation_bindings']['target']
    exact_fields(target, set(historical['installation_bindings']['target']), 'current target shape')
    if not isinstance(target['file_inventory'],list) or not isinstance(target['root_bindings'],dict):
        raise ValueError('current target inventory/root shape differs')
    if type(target['inventory_count']) is not int or not isinstance(target['inventory_sha256'],str):
        raise ValueError('current target count/digest shape differs')
    for row in target['file_inventory']:
        exact_fields(row, set(historical['installation_bindings']['target']['file_inventory'][0]), 'current target row shape')
        if not all(isinstance(row[key],str) for key in row if key!='source_rule_id') or row['source_rule_id'] is not None and not isinstance(row['source_rule_id'],str):
            raise ValueError('current target row scalar shape differs')
    if not isinstance(current['rules'],list) or not current['rules']:
        raise ValueError('current source rules shape differs')
    for rule in current['rules']:
        exact_fields(rule, set(historical['rules'][0]), 'current source rule shape')
        if not isinstance(rule['id'],str):
            raise ValueError('current source rule identity shape differs')
    expected_history = {'source': HISTORICAL_SOURCE, 'sha256': HISTORICAL_SHA, 'schema_version': HISTORICAL_SCHEMA, 'document_role': 'historical_inventory_data_not_current_owner'}
    if binding.get('historical_inventory') != expected_history:
        raise ValueError('historical source locator/digest is not explicit')
    validate_source_binding(current)
    normalized = copy.deepcopy(current)
    normalized.pop('runtime_binding')
    normalized['schema_version'] = HISTORICAL_SCHEMA
    existing = {rule['id']: rule for rule in normalized['rules']}
    if len(existing) != len(normalized['rules']):
        raise ValueError('duplicate source rule identity')
    for identifier in RECIPE_RULES.values():
        if existing.get(identifier) != recipe_rule(identifier):
            raise ValueError('qualification recipe rule is not exact source-only')
    normalized['rules'] = [rule for rule in normalized['rules'] if rule['id'] not in RECIPE_RULES.values()]
    target = normalized['installation_bindings']['target']
    if target['schema_version'] != TARGET_SCHEMA or target['version'] != '2.0.0' or target['limitations'] != SOURCE_LIMITATIONS:
        raise ValueError('explicit inactive target-design successor required')
    if target['inventory_sha256'] != inventory_digest(target['file_inventory']):
        raise ValueError('current target inventory payload digest differs')
    for row in target['file_inventory']:
        expected = RECIPE_RULES.get(row['id'])
        if row['source_rule_id'] != expected:
            raise ValueError('only the two bounded runtime rows may acquire source rules')
        row['source_rule_id'] = None
    target['schema_version'] = 'octon.source.target-installation-manifest.v1'
    target['version'] = '1.0.0'
    target['limitations'] = copy.deepcopy(historical['installation_bindings']['target']['limitations'])
    target['inventory_sha256'] = inventory_digest(target['file_inventory'])
    if not same_json(normalized, historical):
        raise ValueError('legacy generation/dependency/ownership/layout semantics diverged')
    return historical


def structural_imports(data: bytes):
    """Syntax/data observation only. This never imports the observed program."""
    tree = ast.parse(data.decode('utf-8'))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append('.' * node.level + (node.module or ''))
    return sorted(set(imports))


def validate_source_binding(policy, *, source_root: Path | None = None):
    if not isinstance(policy,dict):raise ValueError('current source shape: object required')
    binding = policy.get('runtime_binding')
    exact_fields(binding, {'schema_version','status','permission_grant','profile','layout','parent_schema',
        'projection_version','historical_inventory','recipe','reader','schema_inputs','modules','raw_hash_algorithm',
        'canonical_payload_algorithm','source_encoding','source_newline','output_encoding','output_newline',
        'allowed_postfacet_refresh'}, 'source runtime binding')
    for field, expected in {'schema_version':BINDING_SCHEMA,'status':'qualification_only_not_selectable',
        'permission_grant':False,'profile':'minimal','layout':'compact','parent_schema':PARENT_SCHEMA,
        'projection_version':'target-path-projection.v1','raw_hash_algorithm':'sha256_file_bytes_v1',
        'canonical_payload_algorithm':'sha256_canonical_json_final_lf_v1','source_encoding':'utf-8',
        'source_newline':'lf','output_encoding':'utf-8','output_newline':'lf',
        'allowed_postfacet_refresh':sorted(DERIVED_REFRESH_PATHS)}.items():
        if not same_json(binding[field], expected):
            raise ValueError('unsupported binding selection/byte contract')
    exact_fields(binding['recipe'], {'source','sha256','version','entry_function','manifest_function','serializer'}, 'source recipe')
    if {k:v for k,v in binding['recipe'].items() if k not in {'sha256','serializer'}} != {
        'source':QUALIFIER_SOURCE,'version':'runtime-binding-qualification.v1',
        'entry_function':'runtime_entry_text','manifest_function':'runtime_binding_manifest'}:
        raise ValueError('unsupported actual producer recipe')
    exact_fields(binding['reader'], {'source','sha256','version'}, 'source reader')
    if binding['recipe']['serializer'] != {'source':READER_SOURCE,'sha256':binding['reader']['sha256'],'function':'canonical_json'}:
        raise ValueError('manifest serializer/reader source binding differs')
    exact_fields(binding['reader'], {'source','sha256','version'}, 'source reader')
    if binding['reader']['source'] != READER_SOURCE or binding['reader']['version'] != 'runtime-binding-reader.v1':
        raise ValueError('unsupported standalone trusted reader')
    modules = binding['modules']
    if not isinstance(modules,list) or len(modules)!=9:
        raise ValueError('exact existing nine core modules required')
    if not isinstance(policy.get('rules'),list):
        raise ValueError('source module/dependency shape differs')
    disposable=policy.get('disposable_runtime')
    exact_fields(disposable, {'schema_version','status','permission_grant','profile','layout','projection_version','required_dependencies','runtime_paths'}, 'source disposable dependency shape')
    if not isinstance(disposable['runtime_paths'],list) or not all(isinstance(path,str) for path in disposable['runtime_paths']) or len(set(disposable['runtime_paths']))!=len(disposable['runtime_paths']):
        raise ValueError('source disposable runtime paths shape/uniqueness differs')
    if not same_json({key:value for key,value in disposable.items() if key!='runtime_paths'}, {'schema_version':'octon.source.disposable-runtime.v1','status':'qualification_only_not_selectable','permission_grant':False,'profile':'minimal','layout':'compact','projection_version':'target-path-projection.v1','required_dependencies':['python>=3.11','canonical-minimal-core']}):
        raise ValueError('source disposable dependency selection/semantics differ')
    for rule in policy['rules']:
        if not isinstance(rule,dict) or not isinstance(rule.get('id'),str):raise ValueError('source rule shape differs')
    matching = [rule for rule in policy['rules'] if rule['id']=='templates-core']
    if len(matching)!=1 or not isinstance(matching[0].get('inventory_paths'),list) or not all(isinstance(path,str) for path in matching[0]['inventory_paths']):
        raise ValueError('source core inventory shape differs')
    core = matching[0]
    for row in modules:
        exact_fields(row, {'source_rule_id','source','raw_sha256','path','required'}, 'raw module')
        portable_path(row['path'])
    expected = sorted('.octon/runtime/scripts/'+Path(p).name[:-5] for p in core['inventory_paths']
                      if p.startswith('.agent/scripts/') and p.endswith('.py.tmpl'))
    if [row['path'] for row in modules] != expected or expected != policy['disposable_runtime']['runtime_paths']:
        raise ValueError('qualified/current core module path inventories diverged')
    schema_inputs = binding['schema_inputs']
    if not isinstance(schema_inputs, list) or len(schema_inputs) != len(SCHEMA_SOURCES):
        raise ValueError('exact runtime schema raw inputs required')
    for row, expected in zip(schema_inputs, SCHEMA_SOURCES):
        exact_fields(row, {'source_rule_id', 'source', 'sha256'}, 'schema input')
        if row['source_rule_id'] != 'source-contracts' or row['source'] != expected:
            raise ValueError('schema source rule/locator differs')
    inputs = [binding['recipe'],binding['reader'],*schema_inputs]
    for row in modules:
        exact_fields(row, {'source_rule_id','source','raw_sha256','path','required'}, 'raw module')
        name = Path(row['path']).name+'.tmpl'
        source = 'skills/octon-project-bootstrap/assets/templates/core/.agent/scripts/'+name
        if row['source_rule_id']!='templates-core' or row['source']!=source or row['required'] is not True or not HEX64.fullmatch(str(row['raw_sha256'])):
            raise ValueError('module raw source rule/content contract differs')
        inputs.append({'source':row['source'],'sha256':row['raw_sha256']})
    for row in inputs:
        portable_path(row['source'])
        if not isinstance(row['sha256'],str) or not HEX64.fullmatch(row['sha256']):
            raise ValueError('invalid raw source byte digest')
        if source_root is not None:
            path = ReadOnlyTargetBinding(Path(source_root), layout_id='oep1_target', state_owner='embedded').path(row['source'])
            data = path.read_bytes()
            if b'\r' in data or sha256(data)!=row['sha256']:
                raise ValueError('raw source LF/content bytes differ from reviewed inventory')
    return binding


def tree_inventory(root: Path, *, include_bytes=True, max_entries=None):
    """Full local mutation footprint, including directory/type/native mode."""
    root = Path(root)
    rows = []
    def visit(directory):
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            kind = 'symlink' if stat.S_ISLNK(info.st_mode) else 'reparse' if reparse(info) else 'file' if stat.S_ISREG(info.st_mode) else 'directory' if stat.S_ISDIR(info.st_mode) else 'other'
            row = {'path':relative,'type':kind,'mode':native_mode(info)}
            if kind=='file' and include_bytes:row['sha256']=sha256(path.read_bytes())
            rows.append(row)
            if max_entries is not None and len(rows)>max_entries:raise ValueError('bounded runtime path inventory exceeded')
            if kind=='directory':visit(path)
    visit(root)
    rows.sort(key=lambda row: row['path'])
    return rows


FORBIDDEN_DERIVED = ['.octon/dossier/CHECKSUMS.sha256', '.octon/agent/generated/manifest.json', '.octon/agent/generated/validation-report.json']


def verify_parent_bindings(root, parent):
    binding = ReadOnlyTargetBinding(root, layout_id='oep1_target', state_owner='embedded')
    rows = parent['assets'] + [row for row in parent['output_inventory'] if row['sha256'] is not None]
    for row in rows:
        if sha256(binding.read(row['path'])) != row['sha256']:
            raise ValueError('parent asset/non-null output bytes differ')
    for relative in FORBIDDEN_DERIVED:
        if occupied_casefold(binding.root,relative):
            raise ValueError('unsupported high-assurance derived output')
    return [{'path':row['path'], 'sha256':row['sha256']} for row in rows]


def verify_postfacet_refresh(root, parent, parent_bytes, facet_bytes, before, after):
    """Packaging observation only; inspector never invokes or repairs refresh."""
    old = {row['path']:row for row in before}; new = {row['path']:row for row in after}
    if set(old) != set(new):
        raise ValueError('postfacet refresh created or deleted an output/type')
    changes = sorted(name for name in old if not same_json(old[name], new[name]))
    for name in changes:
        if name not in DERIVED_REFRESH_PATHS or old[name]['type'] != 'file' or new[name]['type'] != 'file' or not same_json(old[name]['mode'],new[name]['mode']):
            raise ValueError('postfacet refresh changed unqualified paths/types/modes')
    if any(row['type'] in {'symlink','reparse','other'} for row in after):
        raise ValueError('postfacet refresh left an unsafe path/type')
    binding = ReadOnlyTargetBinding(root, layout_id='oep1_target', state_owner='embedded')
    if binding.read('.octon/manifest.json') != parent_bytes or binding.read(TARGET_PATHS['runtime.manifest']) != facet_bytes:
        raise ValueError('postfacet refresh changed immutable parent/facet bytes')
    immutable = verify_parent_bindings(root, parent)
    return {'schema_version':'octon.runtime-binding-refresh-proof.v1','permission_grant':False,
        'parent_sha256':sha256(parent_bytes),'facet_sha256':sha256(facet_bytes),
        'before':before,'after':after,'changed_paths':changes,
        'allowed_derived_paths':sorted(DERIVED_REFRESH_PATHS),'immutable_bindings':immutable,
        'all_non_null_outputs_verified':True,'all_assets_verified':True,
        'no_output_created_or_deleted':True,'no_residual_refresh_artifact':True,
        'forbidden_derived_absent':FORBIDDEN_DERIVED}


FACET_FIELDS = {'schema_version','document_role','permission_grant','execution_authorized','status',
    'layout_id','state_binding','source_inventory','historical_inventory','parent_installation',
    'recipe','reader','schema_inputs','render_inputs','entry','modules','dependency_assets','non_null_outputs',
    'excluded_from_parent_initial_inventory','raw_hash_algorithm','canonical_payload_algorithm'}
PARENT_FIELDS = {'schema_version','permission_grant','status','profile','layout','source_revision',
    'projection_version','inventory_sha256','required_dependencies','assets','inputs','output_inventory'}



def legacy_generation_data(historical):
    """Derive complete old path/render inventories without importing a generator."""
    generated = {}
    source_paths = set()
    for rule in historical['rules']:
        if rule['disposition'] != 'generated' or 'minimal' not in rule['profiles']:
            continue
        source = rule['source']
        base = ('skills/octon-project-bootstrap/' + source[6:]) if source.startswith('skill:') else source[len('octon-mini:'):]
        suffix = rule['output']['strip_suffix']
        for item in rule['inventory_paths']:
            output = item[:-len(suffix)] if suffix else item
            root = rule['output']['root']
            output = output if root == '.' else root + '/' + output
            source_path = base + '/' + item if rule['match'] != 'exact' else base
            generated[output] = source_path
    layout = next(row for row in historical['layouts'] if row['id'] == 'compact')
    for omitted in layout['omit_paths']:
        generated.pop(omitted)
    for override in layout['template_overrides']:
        generated[override['output_path']] = 'skills/octon-project-bootstrap/' + override['source'][6:]
    source_paths.update(generated.values())
    paths = historical['project_paths']
    derived = {row['path'] for row in paths['derived_outputs'] if row['minimum_profile'] == 'minimal'}
    local = {row['path'] for row in paths['project_local_sources'] if row['minimum_profile'] == 'minimal'}
    candidates = set(generated) | derived | local | {paths['origin']['path']}
    projection = paths['operational_projection']
    operational = {name for name in candidates if name in projection['include_exact'] or any(name == prefix or name.startswith(prefix + '/') for prefix in projection['include_subtrees'])}
    portfolio = next(row for row in historical['packages'] if row['id'] == 'small-team-git-portfolio')
    json_paths = lambda value: json.dumps(sorted(value), separators=(',', ':'))
    variables = {'CURRENT_DISPATCHER_PARENT_INDEX': '2',
        'DERIVED_OPERATIONAL_FILES_JSON': json_paths(derived & operational),
        'PROFILE_OPERATIONAL_FILES_JSON': json_paths(operational),
        'KERNEL_FILES_JSON': json_paths(paths['kernel_files']),
        'GIT_PORTFOLIO_VERSION': str(portfolio['version']), 'GIT_PORTFOLIO_SHA256': str(portfolio['sha256'])}
    def project(name):
        for old, new in [('.agent/scripts/', '.octon/runtime/scripts/'), ('.agent/', '.octon/agent/'), ('project-dossier/', '.octon/dossier/'), ('.agents/', '.octon/agents/')]:
            if name.startswith(old):
                return new + name[len(old):]
        return name
    outputs = {project(name) for name in candidates} | {'.octon/runtime/installation_runtime.py', '.octon/runtime/profile-inventory.json', '.octon/runtime/octon', 'octon', 'WORKSPACE.md', '.octon/manifest.json'}
    source_paths |= {QUALIFIER_SOURCE, 'skills/octon-project-bootstrap/scripts/scaffold_project.py',
        'skills/octon-project-bootstrap/scripts/installation_runtime.py', 'shared/source-contracts/profile-manifest.json',
        HISTORICAL_SOURCE, 'shared/source-contracts/profile-manifest-v3.schema.json', 'dossier/artifact-types.json', 'octon.json', 'VERSION', READER_SOURCE, *SCHEMA_SOURCES}
    return variables, sorted(outputs), sorted(source_paths)


def validate_import_closure(observations):
    local = {Path(row['path']).stem for row in observations if row['path'].endswith('.py')}
    for row in observations:
        for name in row['imports']:
            if name.startswith('.') or name.split('.', 1)[0] not in sys.stdlib_module_names | local:
                raise ValueError('unbound non-stdlib executable import dependency')


def inspect_runtime_binding(root: Path, source_snapshot: Path, *, expected_source_sha256: str,
                            expected_runtime_sha256: str, layout_id: str, state_owner: str):
    digest_value(expected_source_sha256,'both independent source and output expectations')
    digest_value(expected_runtime_sha256,'both independent source and output expectations')
    binding = ReadOnlyTargetBinding(root,layout_id=layout_id,state_owner=state_owner)
    if Path(__file__).resolve().is_relative_to(binding.root):
        raise ValueError('trusted inspection program must be outside inspected target custody')
    source_snapshot = Path(source_snapshot)
    if not source_snapshot.is_absolute() or source_snapshot.resolve().is_relative_to(binding.root) or source_snapshot.is_symlink():
        raise ValueError('independent source snapshot must be an external regular file')
    source_info = source_snapshot.lstat()
    if not stat.S_ISREG(source_info.st_mode) or reparse(source_info) or source_info.st_size>MAX_BYTES:
        raise ValueError('unambiguous external source snapshot required')
    source_raw = source_snapshot.read_bytes()
    if b'\r' in source_raw:
        raise ValueError('external current source snapshot must retain exact LF bytes')
    if sha256(source_raw)!=expected_source_sha256:
        raise ValueError('external source snapshot differs from independent expectation')
    source = strict_json(source_raw)
    if not isinstance(source,dict) or source.get('schema_version')!=SOURCE_SCHEMA:
        raise ValueError('unsupported source inventory version')
    source_binding = validate_source_binding(source)
    if sha256(Path(__file__).read_bytes()) != source_binding['reader']['sha256']:
        raise ValueError('trusted reader bytes differ from externally pinned source contract')
    raw = binding.read(TARGET_PATHS['runtime.manifest'])
    if sha256(raw)!=expected_runtime_sha256:
        raise ValueError('runtime facet differs from independent output expectation')
    facet = strict_json(raw)
    exact_fields(facet,FACET_FIELDS,'runtime facet')
    if raw != canonical_json(facet):
        raise ValueError('runtime facet raw UTF8/LF serialization differs from actual recipe')
    if any(not same_json(facet.get(k),v) for k,v in {'schema_version':FACET_SCHEMA,
        'document_role':'derived_runtime_integrity_and_compatibility_provenance','permission_grant':False,
        'execution_authorized':False,'status':'disposable_qualification_only','layout_id':'oep1_target',
        'state_binding':{'owner_policy':'exactly_one','owner':'embedded','path':'.octon/agent/state','external':None},
        'raw_hash_algorithm':'sha256_file_bytes_v1','canonical_payload_algorithm':'sha256_canonical_json_final_lf_v1',
        'excluded_from_parent_initial_inventory':[TARGET_PATHS['runtime.manifest']]}.items()):
        raise ValueError('runtime facet role/version/permission/state differs')
    binding.path('.octon/agent/state',file=False)
    for marker in ['.agent','.agents','project-dossier','.octon-mini-origin.json']:
        if occupied_casefold(binding.root,marker):raise ValueError('mixed legacy installation markers')
    historical_raw = binding.read('.octon/runtime/profile-inventory.json')
    historical = historical_compatibility_policy(source,historical_raw)
    parent_raw = binding.read('.octon/manifest.json');parent = strict_json(parent_raw)
    exact_fields(parent,PARENT_FIELDS,'retained parent')
    if any(not same_json(parent.get(k),v) for k,v in {'schema_version':PARENT_SCHEMA,'permission_grant':False,
        'status':'disposable_qualification_only','profile':'minimal','layout':'compact',
        'projection_version':'target-path-projection.v1','inventory_sha256':HISTORICAL_SHA,
        'required_dependencies':['python>=3.11','canonical-minimal-core']}.items()):
        raise ValueError('unsupported or mixed retained parent')
    if not re.fullmatch('[0-9a-f]{40}',str(parent['source_revision'])):
        raise ValueError('exact source revision required')
    if facet['source_inventory']!={'source':'shared/source-contracts/profile-manifest.json','schema_version':SOURCE_SCHEMA,
        'sha256':expected_source_sha256,'source_revision':parent['source_revision']}:
        raise ValueError('runtime source/parent revision binding differs')
    if facet['historical_inventory']!={**source_binding['historical_inventory'],'installed_path':'.octon/runtime/profile-inventory.json'}:
        raise ValueError('actual historical/raw source locator binding differs')
    if facet['parent_installation']!={'path':'.octon/manifest.json','schema_version':PARENT_SCHEMA,'sha256':sha256(parent_raw)}:
        raise ValueError('parent raw bytes changed or cyclic parent binding')
    if not same_json(facet['recipe'],source_binding['recipe']) or not same_json(facet['reader'],source_binding['reader']) or not same_json(facet['schema_inputs'],source_binding['schema_inputs']):
        raise ValueError('runtime recipe/reader source differs')
    render=facet['render_inputs']
    exact_fields(render, {'template_variables','profile','layout','admission','projection_version',
        'projected_dispatcher_parent_index','source_encoding','source_newline','output_encoding','output_newline'}, 'render inputs')
    expected_render={'profile':'minimal','layout':'compact','admission':False,
        'projection_version':'target-path-projection.v1','projected_dispatcher_parent_index':3,
        'source_encoding':'utf-8','source_newline':'lf','output_encoding':'utf-8','output_newline':'lf'}
    if any(not same_json(render[k],v) for k,v in expected_render.items()):
        raise ValueError('unsupported deterministic render/projection inputs')
    variables=render['template_variables']
    exact_fields(variables, {'CURRENT_DISPATCHER_PARENT_INDEX','DERIVED_OPERATIONAL_FILES_JSON',
        'PROFILE_OPERATIONAL_FILES_JSON','KERNEL_FILES_JSON','GIT_PORTFOLIO_VERSION','GIT_PORTFOLIO_SHA256'}, 'template variables')
    expected_variables, expected_outputs, expected_inputs = legacy_generation_data(historical)
    if not same_json(variables, expected_variables):
        raise ValueError('complete deterministic template render inputs differ')
    if path_records(parent['inputs'], 'parent raw inputs') != expected_inputs:
        raise ValueError('parent raw input closure differs')
    if path_records(parent['output_inventory'], 'parent initial outputs', nullable=True) != expected_outputs:
        raise ValueError('parent initial output closure differs')
    null_paths = {row['path'] for row in parent['output_inventory'] if row['sha256'] is None}
    if null_paths != DERIVED_REFRESH_PATHS | {'.octon/manifest.json'}:
        raise ValueError('only exact historical derived/self output hashes may be null')
    for row in parent['output_inventory']:
        binding.path(row['path'])
    inputs = {row['path']:row['sha256'] for row in parent['inputs']}
    if inputs['shared/source-contracts/profile-manifest.json'] != expected_source_sha256 or inputs[HISTORICAL_SOURCE] != HISTORICAL_SHA:
        raise ValueError('actual current/historical dual parent inputs missing or changed')
    for row in [source_binding['recipe'], source_binding['reader'], *source_binding['schema_inputs']]:
        if inputs[row['source']] != row['sha256']:
            raise ValueError('parent recipe/reader/schema raw source binding differs')
    for row in source_binding['modules']:
        if inputs.get(row['source'])!=row['raw_sha256']:
            raise ValueError('parent raw template content binding differs')
    # Derive the exact legacy asset closure as data, including helpers/schemas.
    schemas = next(rule for rule in historical['rules'] if rule['id']=='shared-kernel-schemas')
    copied = [rule['output']['root']+'/'+p for rule in historical['rules']
        if rule['disposition']=='generated' and 'minimal' in rule['profiles'] and rule['output']['strip_suffix'] is None
        for p in rule['inventory_paths']]
    copied = [p.replace('.agent/','.octon/agent/',1) for p in copied]
    expected_assets = sorted(historical['disposable_runtime']['runtime_paths']+copied+
        ['.octon/runtime/installation_runtime.py','.octon/runtime/octon','octon'])
    if path_records(parent['assets'], 'parent assets')!=expected_assets:
        raise ValueError('parent helper/schema/core dependency closure differs')
    if len(facet['dependency_assets'])!=len(parent['assets']):
        raise ValueError('runtime dependency closure missing')
    observations=[]
    for row, declared in zip(parent['assets'],facet['dependency_assets']):
        exact_fields(row,{'path','sha256'},'parent asset')
        exact_fields(declared,{'path','sha256','mode','imports'},'runtime dependency')
        data=binding.read(row['path'])
        raw_input = 'shared/schemas/'+Path(row['path']).name if row['path'].startswith('.octon/agent/schemas/') else 'skills/octon-project-bootstrap/scripts/installation_runtime.py' if row['path']=='.octon/runtime/installation_runtime.py' else None
        if raw_input is not None and inputs[raw_input] != row['sha256']:
            raise ValueError('copied schema/helper raw input/output binding differs')
        mode=native_mode(binding.path(row['path']).lstat())
        imports=structural_imports(data) if row['path'].endswith('.py') or row['path'] in {'octon','.octon/runtime/octon'} else []
        if sha256(data)!=row['sha256'] or not same_json(declared,{**row,'mode':mode,'imports':imports}):
            raise ValueError('required dependency bytes/mode/import observation changed')
        observations.append(declared)
    validate_import_closure(observations)
    non_null=[r for r in parent['output_inventory'] if r['sha256'] is not None]
    if facet['non_null_outputs']!=non_null:
        raise ValueError('non-null initial output bindings differ')
    if any(r['path']==TARGET_PATHS['runtime.manifest'] for r in parent['output_inventory']+parent['assets']):
        raise ValueError('facet cannot retroactively join retained parent inventory')
    for row in non_null:
        exact_fields(row,{'path','sha256'},'initial output')
        if sha256(binding.read(row['path']))!=row['sha256']:
            raise ValueError('non-null initial output changed')
    for forbidden in ['.octon/dossier/CHECKSUMS.sha256','.octon/agent/generated/manifest.json','.octon/agent/generated/validation-report.json']:
        if occupied_casefold(binding.root,forbidden):raise ValueError('unsupported high-assurance derived output')
    entry=facet['entry'];exact_fields(entry,{'id','path','source_rule_id','sha256','mode'},'entry')
    if entry['id']!='runtime.entry' or entry['path']!=TARGET_PATHS['runtime.entry'] or entry['source_rule_id']!=RECIPE_RULES['runtime.entry'] or entry['sha256']!=sha256(binding.read(entry['path'])) or not same_json(entry['mode'],native_mode(binding.path(entry['path']).lstat())):
        raise ValueError('runtime entry exact binding differs')
    if len(facet['modules'])!=9:
        raise ValueError('runtime module inventory incomplete')
    for raw_source,output in zip(source_binding['modules'],facet['modules']):
        exact_fields(output,set(raw_source)|{'sha256','mode','imports'},'module output')
        if {k:output[k] for k in raw_source}!=raw_source:
            raise ValueError('raw template/installed module identity substituted')
        data=binding.read(output['path'])
        if b'\r' in data or sha256(data)!=output['sha256'] or not same_json(output['mode'],native_mode(binding.path(output['path']).lstat())) or output['imports']!=structural_imports(data):
            raise ValueError('installed module byte/mode/import binding differs')
    expected_python = {r['path'] for r in parent['assets'] if r['path'].endswith('.py')}
    runtime_inventory = [{**row,'path':'.octon/runtime/'+row['path']} for row in tree_inventory(binding.path('.octon/runtime',file=False),include_bytes=False,max_entries=1024)]
    actual_python = {row['path'] for row in runtime_inventory if row['path'].endswith('.py')}
    allowed_runtime = {name for name in expected_outputs if name.startswith('.octon/runtime/')} | {TARGET_PATHS['runtime.manifest']}
    if actual_python!=expected_python or any(row['type'] != 'directory' and (row['type'] != 'file' or row['path'] not in allowed_runtime) for row in runtime_inventory):
        raise ValueError('unreviewed executable runtime dependency or alias')
    return {'schema_version':'octon.runtime-binding-inspection.v1','permission_grant':False,'execution_authorized':False,
        'authority_authentication':'not_performed','provenance':'caller_pinned_content_integrity_only',
        'source_revision':parent['source_revision'],'source_sha256':expected_source_sha256,'runtime_sha256':expected_runtime_sha256,
        'layout_id':layout_id,'state_owner':state_owner,'entry':entry['path'],'modules':9,'dependency_assets':len(observations),
        'target_code_executed':False,'target_mutations':False,
        'import_closure':'stdlib_and_exact_pinned_local_assets','non_null_outputs':len(non_null),'parent_sha256':sha256(parent_raw)}


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,required=True)
    parser.add_argument('--source-snapshot',type=Path,required=True)
    parser.add_argument('--expected-source-sha256',required=True)
    parser.add_argument('--expected-runtime-sha256',required=True)
    parser.add_argument('--layout-id',required=True)
    parser.add_argument('--state-owner',required=True)
    args=parser.parse_args()
    try:
        result=inspect_runtime_binding(args.project_root,args.source_snapshot,
            expected_source_sha256=args.expected_source_sha256,expected_runtime_sha256=args.expected_runtime_sha256,
            layout_id=args.layout_id,state_owner=args.state_owner)
        print(json.dumps(result,sort_keys=True));return 0
    except (ValueError,OSError,KeyError,TypeError,StopIteration,SyntaxError) as error:
        print(json.dumps({'schema_version':'octon.runtime-binding-inspection.v1','permission_grant':False,
            'execution_authorized':False,'target_code_executed':False,'target_mutations':False,
            'provenance':'unestablished','error':str(error)},sort_keys=True));return 2



NATIVE_CAPABILITY_CASES = {
    'test_native_symlink_or_explicit_unsupported': ('symlink', 'all'),
    'test_native_dangling_reserved_and_forbidden_occupancy_refuse': ('symlink', 'all'),
    'test_native_windows_junction_or_nonwindows_disposition': ('windows junction', 'nt'),
    'test_native_fifo_refusal_or_nonposix_disposition': ('POSIX FIFO', 'posix'),
}


def validate_native_capabilities(data):
    """Coherent observed/native applicability; unit success cannot invent a cap."""
    names=data['case_names'];cases=data['cases']
    expected_unsupported=[]
    for row in cases:
        if not isinstance(row,dict) or row.get('case') not in names:
            raise ValueError('native detail has an unknown case or invalid shape')
        if 'terminal' in row and type(row['terminal']) is not bool:
            raise ValueError('native terminal disposition must be explicit boolean')
    terminals={row['case']:row for row in cases if row.get('terminal') is True}
    for name in names:
        terminal=terminals[name]['outcome']
        details=[row for row in cases if row['case']==name and row.get('terminal') is not True and ('host_capability' in row or row.get('outcome') in {'unsupported creation','not applicable'})]
        if name not in NATIVE_CAPABILITY_CASES:
            if terminal!='passed' or details:
                raise ValueError('native unsupported/inapplicable case lacks declared capability')
            continue
        capability,host=NATIVE_CAPABILITY_CASES[name]
        if len(details)!=1 or details[0].get('host_capability')!=capability:
            raise ValueError('native capability needs one exact matching detail')
        detail=details[0];applies=host=='all' or host==data['platform']['os_name']
        if not applies:
            if terminal!='not_applicable' or detail.get('outcome')!='not applicable' or detail.get('actual_host')!=data['platform']['os_name'] or detail.get('protection_claim') is not False or detail.get('available') is not False:
                raise ValueError('native not_applicable disposition lacks actual platform justification')
        elif terminal=='unsupported':
            if detail.get('outcome')!='unsupported creation' or detail.get('protection_claim') is not False or detail.get('available') is not False:
                raise ValueError('native unsupported disposition lacks unavailable capability detail')
            expected_unsupported.append(detail)
        elif terminal=='passed':
            if detail.get('outcome')!='passed' or detail.get('available') is not True or detail.get('actual_refusal') is not True or detail.get('protection_claim') is not True:
                raise ValueError('native passing capability lacks actual exercised refusal')
        else:
            raise ValueError('required native capability cannot be not_applicable')
    if not same_json(data['native_unsupported'],expected_unsupported):
        raise ValueError('native unsupported array contradicts capability/terminal details')
    return expected_unsupported


def native_qualification_exit(passed, unsupported):
    """Required unavailable native capability is a qualification gate failure."""
    return 0 if passed and not unsupported else 1

def forward_native_evidence(text):
    """Forward only the reviewed bounded strict-JSON block from the known suite."""
    begin='OCTON_RUNTIME_BINDING_EVIDENCE_BEGIN\n';end='\nOCTON_RUNTIME_BINDING_EVIDENCE_END'
    if text.count(begin)!=1 or text.count(end)!=1:
        raise ValueError('runtime native suite must emit one bounded evidence block')
    payload=text.split(begin,1)[1].split(end,1)[0]
    data=strict_json(payload.encode('utf-8'))
    required = {'schema_version','permission_grant','candidate_qualified','source_subject','case_names',
        'source_revision','source_status','source_unchanged','test_suite_passed','complete_suite',
        'tests_run','failures','errors','cases','native_unsupported','platform','python','executable','qualified'}
    if not isinstance(data,dict) or not required <= set(data) or data['schema_version']!='octon.runtime-binding-qualification.v1' or data['permission_grant'] is not False or data['candidate_qualified'] is not False:
        raise ValueError('runtime native evidence role/version/required fields differ')
    exact_fields(data['platform'], {'system','machine','version','os_name'}, 'native platform')
    if not all(isinstance(v,str) and v for v in data['platform'].values()) or data['platform']['os_name'] != os.name or data['python'] != sys.version or data['executable'] != sys.executable:
        raise ValueError('native evidence must declare actual platform/interpreter')
    subject = data['source_subject']
    exact_fields(subject, {'revision','status','files'}, 'native source subject')
    if not isinstance(subject['files'],dict) or not subject['files'] or not isinstance(subject['status'],list) or not re.fullmatch('[0-9a-f]{40}', str(subject['revision'])) or subject['revision'] != data['source_revision'] or subject['status'] != data['source_status']:
        raise ValueError('runtime native evidence lacks coherent exact source subject')
    for path, digest in subject['files'].items():
        portable_path(path); digest_value(digest, 'native source subject')
    names = data['case_names']
    if not isinstance(names,list) or not names or not all(isinstance(name,str) and name.startswith('test_') for name in names) or len(set(names)) != len(names):
        raise ValueError('native case inventory must be explicit and unique')
    if not isinstance(data['cases'],list) or not isinstance(data['native_unsupported'],list):
        raise ValueError('native case/capability evidence must be arrays')
    terminals = [row for row in data['cases'] if isinstance(row,dict) and row.get('terminal') is True]
    if sorted(row.get('case','') for row in terminals) != sorted(names) or any(row.get('outcome') not in {'passed','not_applicable','unsupported'} for row in terminals):
        raise ValueError('every mandatory native case needs one successful explicit terminal disposition')
    if any(type(data[key]) is not int for key in ['tests_run','failures','errors']) or data['tests_run'] != len(names) or data['failures'] != 0 or data['errors'] != 0 or data['source_unchanged'] is not True or data['test_suite_passed'] is not True or data['complete_suite'] is not True:
        raise ValueError('native suite incomplete, failed or source changed')
    validate_native_capabilities(data)
    if type(data['qualified']) is not bool or data['qualified'] != (not subject['status'] and not data['native_unsupported']):
        raise ValueError('native qualification cannot erase dirty/unsupported scope')
    print(begin+json.dumps(data,sort_keys=True)+end,flush=True)
    return data


if __name__=='__main__':raise SystemExit(main())
