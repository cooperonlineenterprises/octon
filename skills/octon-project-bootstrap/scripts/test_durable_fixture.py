#!/usr/bin/env python3
"""Owned Docker fixture orchestration; no live grants or provider effects."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]
IMAGE='python@sha256:4d1caded1f729ae443eb803f26ffde7b61e696aeaef62f099abb6dd6b14257c7'
CAPS=['CHOWN','SETUID','SETGID','SETPCAP','KILL']
RESOURCE_EVENTS=[]
ACTIVE_LIFETIMES=[]
LAUNCH_BARRIER=None
SEED=None
DEADLINE=None
CLEANUP_UNTIL=None
CHECKPOINT_SEQUENCE=0


class QualificationDeadline(KeyboardInterrupt):pass


def checkpoint(kind,**details):
    global CHECKPOINT_SEQUENCE
    CHECKPOINT_SEQUENCE+=1
    # Only deliberately selected public metadata enters this partial stream.
    print('OCTON_DURABLE_CHECKPOINT '+json.dumps({'sequence':CHECKPOINT_SEQUENCE,'kind':kind,'complete':False,'qualified':False,**details},sort_keys=True),flush=True)


def run(argv,*,input=None,check=True):
    now=time.monotonic()
    if CLEANUP_UNTIL is None and DEADLINE is not None and now>=DEADLINE:raise QualificationDeadline
    timeout=180 if CLEANUP_UNTIL is None else min(10,max(.1,CLEANUP_UNTIL-now))
    if CLEANUP_UNTIL is not None and now>=CLEANUP_UNTIL:raise ValueError('bounded cleanup deadline exhausted; owned resources remain unknown')
    value=subprocess.run(argv,input=input,capture_output=True,text=True,check=False,timeout=timeout)
    if check and value.returncode:raise ValueError('owned fixture command failed: '+value.stderr+value.stdout)
    return value


def engine_id():
    value=run(['docker','info','--format','{{.ID}}'])
    if not value.stdout.strip():raise ValueError('engine observation unavailable; cleanup remains unknown')
    return value.stdout.strip()


def pinned_image(engine):
    """Reconcile this immutable image only; unavailable is never absence."""
    def observe():
        value=run(['docker','image','inspect',IMAGE],check=False)
        if value.returncode:
            if value.stderr.strip()=='Error response from daemon: No such image: '+IMAGE:return None
            raise ValueError('pinned image observation unavailable; no acquisition inferred: '+value.stderr)
        rows=json.loads(value.stdout)
        if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict):raise ValueError('ambiguous pinned image observation')
        identity=rows[0].get('Id');digests=rows[0].get('RepoDigests')
        if not isinstance(identity,str) or not identity.startswith('sha256:') or len(identity)!=71 or any(c not in '0123456789abcdef' for c in identity[7:]) or not isinstance(digests,list) or IMAGE not in digests:
            raise ValueError('pinned image identity/digest observation malformed')
        return identity
    if engine_id()!=engine:raise ValueError('engine continuity unavailable before pinned image observation')
    identity=observe()
    if identity is None:
        event={'image':IMAGE,'engine_observed':engine,'image_acquisition_intent':True}
        RESOURCE_EVENTS.append(event);checkpoint('pinned_image_acquisition_intent',**event)
        value=run(['docker','pull',IMAGE],check=False)
        if engine_id()!=engine:raise ValueError('engine continuity unavailable after pinned image acquisition')
        identity=observe()
        outcome={'image':IMAGE,'engine_observed':engine,'pull_exit':value.returncode,'confirmed_image_id':identity}
        RESOURCE_EVENTS.append(outcome);checkpoint('pinned_image_acquisition_observed',**outcome)
        if identity is None:raise ValueError('exact pinned image acquisition not confirmed')
    else:
        checkpoint('pinned_image_observed',image=IMAGE,image_id=identity,engine_observed=engine)
    return identity


def inspect_owned(kind,name,prefix):
    value=run(['docker']+(['volume','inspect'] if kind=='volume' else ['inspect'])+[name],check=False)
    if value.returncode:
        error=value.stderr.lower()
        if name.lower() in error and any(marker in error for marker in ['no such object','no such container','no such volume']):return None
        raise ValueError('resource observation failed; absence remains unknown: '+name+' '+value.stderr)
    rows=json.loads(value.stdout)
    if len(rows)!=1:raise ValueError('ambiguous resource ownership')
    row=rows[0];labels=row['Labels'] if kind=='volume' else row['Config']['Labels']
    if labels.get('octon.owned-qualification')!=prefix:raise ValueError('resource ownership changed; removal refused')
    return row


def source_subject():
    files=['durable_fixture.py','durable_fixture_worker.py','test_durable_fixture.py','qualify_disposable_runtime.py','protected_fixture.py','fixture_admission.py','installation_runtime.py','installation_runtime_v2.py']
    files=[HERE/name for name in files]+[SOURCE/'shared/source-contracts'/name for name in ['durable-fixture-inventory.json','durable-fixture-v2.schema.json']]
    def local_git(*args):
        return subprocess.check_output(['git','--no-optional-locks',*args],text=True,timeout=5).strip()
    return {'revision':local_git('rev-parse','HEAD'),'status':local_git('status','--porcelain=v1').splitlines(),
            'files':{str(path.relative_to(SOURCE)):hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}


class Lifetime:
    """Retained launch handle; never reconstructs currentness from saved files."""
    def __init__(self):
        self.prefix='octon-durable-'+secrets.token_hex(8);self.ticket=secrets.token_hex(32)
        self.started=False;self.retired=False;self.pin=None;self.containers=[];self.volumes=[];self.cleanup_record=None;self.keeper_process=None;self.launches={}
        ACTIVE_LIFETIMES.append(self)
        self.engine=engine_id()
        try:
            for role in ['state','authority','continuity','ipc']:
                name=self.prefix+'-'+role
                if inspect_owned('volume',name,self.prefix) is not None:raise ValueError('fresh owned volume name required')
                self.creation_intent('volume',name)
                value=run(['docker','volume','create','--label','octon.owned-qualification='+self.prefix,name],check=False)
                observed=self.creation_observed('volume',name,value.returncode)
                if value.returncode or observed is None:raise ValueError('owned volume creation not confirmed')
        except BaseException:
            self.cleanup();raise

    def creation_intent(self,kind,name):
        resources=self.volumes if kind=='volume' else self.containers
        if kind not in {'volume','container'} or not name.startswith(self.prefix+'-') or name in resources:
            raise ValueError('fresh exact owned resource intent required')
        resources.append(name)
        event={'prefix':self.prefix,'resource_kind':kind,'create_intent':name,'engine_observed':self.engine}
        RESOURCE_EVENTS.append(event);checkpoint('owned_creation_intent',**event)

    def creation_observed(self,kind,name,exit=None):
        observed=inspect_owned(kind,name,self.prefix)
        event={'prefix':self.prefix,'resource_kind':kind,'create_intent':name,'exit':exit,'confirmed_owned':observed is not None,
               'owned_id':observed['Id'] if kind=='container' and observed else None}
        RESOURCE_EVENTS.append(event);checkpoint('owned_creation_observed',**event)
        return observed

    def args(self,name,*,keeper=False,source=True,seed=False):
        values=['docker','run','--name',name,'--label','octon.owned-qualification='+self.prefix,
                '--network','none','--cap-drop','ALL']
        for capability in CAPS:values+=['--cap-add',capability]
        values+=['--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,nosuid,nodev,exec,size=512m',
                 '--tmpfs','/evidence:rw,nosuid,nodev,size=64m','-e','OCTON_OWNED_EPHEMERAL_CONTAINER=protected-fixture-v1',
                 '-e','OCTON_OWNED_DURABLE_FIXTURE=durable-fixture-v2','-e','GIT_CONFIG_COUNT=1',
                 '-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/source',
                 '-v',self.volumes[0]+':/state:rw',
                 '-v',self.volumes[3]+':/ipc:'+('rw' if keeper else 'ro'),'-w','/source' if source else '/state/target']
        if source:values+=['-v',str(SOURCE)+':/source:ro']
        if keeper:values+=['-v',self.volumes[1]+':/authority:rw','-v',self.volumes[2]+':/continuity:rw']
        if seed:
            if SEED is None:raise ValueError('independent keyless seed handle missing')
            values+=['-v',SEED.volumes[0]+':/seed:ro']
        return values

    def prepare(self):
        name=self.prefix+'-prepare';self.creation_intent('container',name)
        value=run(self.args(name,keeper=True,seed=SEED is not None)+['-i',IMAGE,'python','-B',
                    'skills/octon-project-bootstrap/scripts/durable_fixture.py','--prepare-fixture'],input=json.dumps({'ticket':self.ticket,'seed_binding':SEED.binding if SEED else None,'image_binding':SEED.image if SEED else None})+'\n')
        self.creation_observed('container',name,value.returncode)
        self.prepared=json.loads(value.stdout.splitlines()[-1]);run(['docker','rm',name]);return self.prepared

    def start_keeper(self):
        if self.started or self.retired:raise ValueError('existing fixture lifetime cannot bootstrap fresh currentness')
        self.started=True
        name=self.prefix+'-keeper';self.creation_intent('container',name);self.keeper=name
        self.keeper_process=subprocess.Popen(self.args(name,keeper=True)+['-i',IMAGE,'python','-B','skills/octon-project-bootstrap/scripts/durable_fixture.py','--keeper','/authority/bootstrap.json'],
                                             stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
        self.keeper_process.stdin.write(self.ticket+'\n');self.keeper_process.stdin.close();self.ticket=None
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            value=run(['docker','logs',name],check=False)
            if value.stdout.strip():
                self.creation_observed('container',name)
                self.pin=json.loads(value.stdout.splitlines()[0]);return self.pin
            status=run(['docker','inspect','--format','{{.State.Status}}',name],check=False).stdout.strip()
            if status in {'exited','dead'} or self.keeper_process.poll() is not None:raise ValueError('keeper failed: '+run(['docker','logs',name],check=False).stderr)
            time.sleep(.05)
        raise ValueError('keeper ready barrier unavailable')

    def admin(self,command,body={}):
        if self.retired or not self.started or not self.pin:raise ValueError('independently current launch handle unavailable')
        if run(['docker','inspect','--format','{{.State.Running}}',self.keeper],check=False).stdout.strip()!='true':
            self.retired=True;raise ValueError('keeper lost; fixture lifetime retired')
        path='/tmp/admin-'+secrets.token_hex(8)+'.json'
        write=['docker','exec','-i',self.keeper,'python','-B','-c',
               'import sys,pathlib; pathlib.Path(sys.argv[1]).write_text(sys.stdin.read())',path]
        run(write,input=json.dumps(body))
        pin_path=path+'.pin';run(write[:-1]+[pin_path],input=json.dumps(self.pin))
        value=run(['docker','exec',self.keeper,'python','-B','skills/octon-project-bootstrap/scripts/durable_fixture.py',
                   '--admin',command,'--body',path,'--keeper-pin',pin_path])
        return json.loads(value.stdout)

    def code(self,code,*,container=None,input=None,check=True):
        return run(['docker','exec']+(['-i'] if input is not None else [])+[container or self.keeper,'python','-B','-c',code],input=input,check=check)

    def wait_file(self,container,path):
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            value=self.code('from pathlib import Path; import sys;sys.exit(0 if Path('+repr(path)+').is_file() else 1)',container=container,check=False)
            if not value.returncode:return
            running=run(['docker','inspect','--format','{{.State.Running}}',container],check=False).stdout.strip()
            if running!='true':raise ValueError('barrier process ended: '+run(['docker','logs',container],check=False).stdout)
            time.sleep(.05)
        raise ValueError('explicit fault/contention barrier unavailable')

    def release(self,container):self.code('from pathlib import Path;Path("/tmp/fault-release").touch()',container=container)

    def terminal(self,container):
        value=run(['docker','wait',container]);logs=run(['docker','logs',container],check=False)
        return {'container':container,'exit':int(value.stdout.strip()),'stdout':logs.stdout,'stderr':logs.stderr}

    def enroll(self,expected=0,*,independent=False):
        name=self.prefix+'-controller-'+secrets.token_hex(3);self.creation_intent('container',name)
        path='/state/launch-'+secrets.token_hex(8)+'.json'
        script='.octon/runtime/durable_fixture.py' if independent else 'skills/octon-project-bootstrap/scripts/durable_fixture.py'
        run(self.args(name,source=not independent)+['-d',IMAGE,'python','-I','-B',script,'--await-launch',path])
        self.creation_observed('container',name,0)
        self.wait_file(name,'/tmp/launch-ready.json')
        proof=json.loads(self.code('from pathlib import Path;print(Path("/tmp/launch-ready.json").read_text())',container=name).stdout)
        snapshot=self.admin('inspect')['authority']
        body={'expected_generation':expected,'pid_namespace':proof['pid_namespace'],'namespace_identity':proof['namespace_identity'],'expected_control_generation':snapshot['control_generation'],'expected_control_digest':self.digest(snapshot['bundle'])}
        envelope=self.sign_enrollment(body)
        target='/tmp/enrollment-'+secrets.token_hex(8)+'.json';pin_path=target+'.pin'
        for file,data in [(target,envelope),(pin_path,self.pin)]:
            run(['docker','exec','-i',name,'python','-B','-c','from pathlib import Path;import sys;Path(sys.argv[1]).write_text(sys.stdin.read());Path(sys.argv[1]).chmod(0o600)',file],input=json.dumps(data))
        lease=json.loads(run(['docker','exec',name,'python','-I','-B',script,'--forward-enrollment',target,'--keeper-pin',pin_path]).stdout)
        config={'lease':lease,'pin':self.pin}
        run(['docker','exec','-i',self.keeper,'python','-B','-c',
             'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.stdin.read()); pathlib.Path(sys.argv[1]).chmod(0o600)',path],input=json.dumps(config))
        self.launches[path]=name
        observed=inspect_owned('container',name,self.prefix)
        RESOURCE_EVENTS.append({'prefix':self.prefix,'enrolled_container_id':observed['Id'],'namespace':proof,'generation':lease['generation'],'controller_id':lease['id'],'public_key_digest':hashlib.sha256(lease['public_key'].encode()).hexdigest(),'retained_namespace_identity':lease['namespace_identity']})
        return lease,path

    def sign_enrollment(self,body):
        target='/tmp/sign-enrollment-'+secrets.token_hex(8)+'.json';pin_path=target+'.pin'
        for file,data in [(target,body),(pin_path,self.pin)]:
            run(['docker','exec','-i',self.keeper,'python','-B','-c','from pathlib import Path;import sys;Path(sys.argv[1]).write_text(sys.stdin.read());Path(sys.argv[1]).chmod(0o600)',file],input=json.dumps(data))
        value=run(['docker','exec',self.keeper,'python','-B','skills/octon-project-bootstrap/scripts/durable_fixture.py','--sign-enrollment',target,'--keeper-pin',pin_path])
        return json.loads(value.stdout)

    @staticmethod
    def digest(value):return hashlib.sha256((json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()).hexdigest()

    def execute(self,path,command='apply',fault=None,*,detached=False,peer=False):
        if path in self.launches:
            name=self.launches.pop(path)
            self.code('from pathlib import Path;import sys;Path("/tmp/launch-command.json").write_text(sys.stdin.read())',container=name,input=json.dumps({'command':command,'fault':fault,'peer':peer}))
            if detached:return name
            ended=self.terminal(name);output=ended['stdout'].strip();ended['result']=json.loads(output.splitlines()[-1]) if output else None;return ended
        name=self.prefix+'-controller-'+secrets.token_hex(3);self.creation_intent('container',name)
        argv=self.args(name)+(['-d'] if detached else [])+[IMAGE,'python','-B',
              'skills/octon-project-bootstrap/scripts/durable_fixture.py','--execute',path,'--command',command]
        if fault:argv+=['--fault-at',fault]
        value=run(argv,check=False)
        observed=self.creation_observed('container',name,value.returncode)
        if detached:return name
        output=value.stdout.strip()
        if observed is None:raise ValueError('owned unenrolled container creation not confirmed')
        proof=[json.loads(line)['actual_namespace'] for line in output.splitlines() if line.startswith('{') and 'actual_namespace' in json.loads(line)]
        RESOURCE_EVENTS.append({'prefix':self.prefix,'unenrolled_container_id':observed['Id'],'actual_namespace':proof,'copied_configuration':path,'exit':value.returncode})
        return {'container':name,'container_id':observed['Id'],'namespace':proof,'exit':value.returncode,'stdout':output,'stderr':value.stderr,
                                           'result':json.loads(output.splitlines()[-1]) if output else None}

    def destroy(self,name):
        observed=inspect_owned('container',name,self.prefix)
        if observed is None:raise ValueError('owned container termination outcome unavailable')
        run(['docker','kill','--signal','KILL',observed['Id']],check=False)
        result=run(['docker','inspect','--format','{{.State.ExitCode}}',name],check=False).stdout.strip()
        run(['docker','rm','-f',observed['Id']],check=False);return result

    def worker_probe(self):
        name=self.prefix+'-worker-probe-'+secrets.token_hex(3);self.creation_intent('container',name)
        value=run(self.args(name,keeper=True)+[IMAGE,'python','-B','skills/octon-project-bootstrap/scripts/durable_fixture.py','--worker-probe'])
        self.creation_observed('container',name,value.returncode)
        result=json.loads(value.stdout.splitlines()[-1]);run(['docker','rm',name]);return result

    def cleanup(self):
        records=[]
        self.cleanup_record=records
        if engine_id()!=self.engine:raise ValueError('engine continuity unavailable; cleanup remains unknown')
        for name in reversed(self.containers):
            observed=inspect_owned('container',name,self.prefix)
            value=run(['docker','rm','-f',observed['Id']],check=False) if observed is not None else None
            records.append({'container':name,'owned_id':observed['Id'] if observed else None,'remove_exit':value.returncode if value else None,'absent':inspect_owned('container',name,self.prefix) is None})
        for name in reversed(self.volumes):
            observed=inspect_owned('volume',name,self.prefix)
            value=run(['docker','volume','rm',name],check=False) if observed is not None else None
            records.append({'volume':name,'owned_created_at':observed['CreatedAt'] if observed else None,'remove_exit':value.returncode if value else None,'absent':inspect_owned('volume',name,self.prefix) is None})
        self.cleanup_record=records
        if self.keeper_process:self.keeper_process.wait(timeout=15)
        if engine_id()!=self.engine:raise ValueError('engine observation changed; cleanup remains unknown')
        RESOURCE_EVENTS.append({'prefix':self.prefix,'cleanup':records,'engine_observed':self.engine})
        checkpoint('owned_cleanup',prefix=self.prefix,records=records,engine_observed=self.engine)
        if not all(row['absent'] for row in records):raise ValueError('owned disposable key/resource cleanup incomplete')
        if self in ACTIVE_LIFETIMES:ACTIVE_LIFETIMES.remove(self)
        return records


class KeylessSeed(Lifetime):
    """Existing qualifier's immutable compile output; never an authority store."""
    def __init__(self):
        self.prefix='octon-keyless-'+secrets.token_hex(8);self.containers=[];self.volumes=[];self.cleanup_record=None;self.keeper_process=None
        self.engine=engine_id();ACTIVE_LIFETIMES.append(self)
        self.image=pinned_image(self.engine)
        import qualify_disposable_runtime as Q
        independent=Q.seed_source_binding();name=self.prefix+'-seed'
        if inspect_owned('volume',name,self.prefix) is not None:raise ValueError('fresh keyless seed volume required')
        self.creation_intent('volume',name)
        value=run(['docker','volume','create','--label','octon.owned-qualification='+self.prefix,name],check=False)
        if self.creation_observed('volume',name,value.returncode) is None or value.returncode:raise ValueError('owned keyless volume creation not confirmed')
        container=self.prefix+'-compile';self.creation_intent('container',container);started=time.monotonic()
        argv=['docker','run','--name',container,'--label','octon.owned-qualification='+self.prefix,'--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,nosuid,nodev,exec,size=512m','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/source','-v',str(SOURCE)+':/source:ro','-v',name+':/seed:rw','-w','/source','-i',IMAGE,'python','-B','skills/octon-project-bootstrap/scripts/durable_fixture.py','--create-keyless-seed']
        result=run(argv,input=json.dumps({'image_binding':self.image})+'\n');self.creation_observed('container',container,result.returncode)
        self.binding=json.loads(result.stdout.splitlines()[-1])
        if self.binding['source']!=independent or self.binding['image']!=self.image:raise ValueError('compiled seed differs from independent source/image subject')
        self.seconds=round(time.monotonic()-started,6)
        checkpoint('keyless_seed',source_revision=independent['revision'],image=self.image,files=len(self.binding['files']),compile_seconds=self.seconds)
        run(['docker','rm',container])


class DurableTests(unittest.TestCase):
    evidence=[]
    def setUp(self):
        self.case_started=time.monotonic();self.life=Lifetime();self.addCleanup(self.clean);self.life.prepare();self.life.start_keeper()
        self.lease,self.path=self.life.enroll()
        if LAUNCH_BARRIER is not None:
            LAUNCH_BARRIER.write_text(json.dumps({'prefix':self.life.prefix,'volumes':self.life.volumes,'containers':self.life.containers,'private_bytes_exported':False}))
            while True:time.sleep(.02)
    def clean(self):
        try:
            records=self.life.cleanup();timing={'case_seconds':round(time.monotonic()-self.case_started,6),'preparation_seconds':self.life.prepared.get('preparation_seconds') if hasattr(self.life,'prepared') else None,'keyless_seed_used':self.life.prepared.get('keyless_seed_used') if hasattr(self.life,'prepared') else None}
            self.evidence.append({'case':self._testMethodName,'cleanup':records,'timing':timing});checkpoint('case_completed',case=self._testMethodName,timing=timing,owned_cleanup_verified=True)
        except Exception as error:self.evidence.append({'case':self._testMethodName,'cleanup_unknown':str(error),'records':self.life.cleanup_record});raise
    def relative(self,kind):
        identity=self.life.prepared['receipt_ref']
        return '.octon/agent/transactions/'+({'journal':'pending/','receipt':'receipts/','recovery':'recovered/'}[kind])+identity+'.json'
    def crash(self,name,relative):
        child=self.life.execute(self.path,fault=name+':'+relative,detached=True)
        self.life.wait_file(child,'/tmp/fault-ready.json');self.assertEqual(self.life.destroy(child),'137')
        self.lease,self.path=self.life.enroll(self.lease['generation']);return child
    def controls(self,change):
        snapshot=self.life.admin('inspect')['authority'];value=snapshot['bundle'];expected=self.life.digest(value);value['controls'].update(change)
        # Use the existing canonical digest owner, never hand-written signatures.
        sealed=self.life.code('import sys,json;sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts");from test_fixture_admission import seal;v=json.loads(sys.stdin.read());seal(v);print(json.dumps(v))',input=json.dumps(value))
        return self.life.admin('control',{'bundle':json.loads(sealed.stdout),'expected_control_generation':snapshot['control_generation'],'expected_control_digest':expected})
    def replacement(self):self.lease,self.path=self.life.enroll(self.lease['generation'])
    def denied_recovery(self,reason):
        self.replacement();result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn(reason,result['stdout']);return result
    def preservation(self):
        value=self.life.code('import pathlib,hashlib,json;rows='+repr(self.life.prepared['synthetic_preservation'])+';print(json.dumps([{**r,"actual_sha256":hashlib.sha256((pathlib.Path("/state/target")/r["path"]).read_bytes()).hexdigest()} for r in rows]))')
        records=json.loads(value.stdout);self.assertTrue(all(row['sha256']==row['actual_sha256'] for row in records),records);return records
    def test_actual_narrow_committer_and_container_replacement(self):
        first=self.life.execute(self.path)
        self.assertEqual(first['exit'],0,first)
        self.assertEqual(first['result']['status'],'applied')
        run(['docker','rm',first['container']])
        self.lease,self.path=self.life.enroll(1)
        result=self.life.execute(self.path,'reconcile')
        self.assertEqual(result['exit'],0,result)
        self.assertEqual(result['result']['status'],'applied')
        self.replacement();replay=self.life.execute(self.path)
        self.assertEqual(replay['exit'],2,replay)
        self.assertIn('consumed identity',replay['stdout'])
        self.evidence.append({'case':self._testMethodName,'first':first,'replacement':result,'replay':replay,
                              'retained_dependency':'original live keeper/launch handle/volumes/kernel boot'})

    def test_sigkill_journal_actual_replacement_recovers(self):
        child=self.crash('after-effect',self.relative('journal'))
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],0,result)
        self.assertEqual(result['result']['status'],'recovered_to_preimage')
        self.replacement();replay=self.life.execute(self.path);self.assertEqual(replay['exit'],2);self.assertIn('consumed identity',replay['stdout'])
        self.evidence.append({'case':self._testMethodName,'termination':'actual SIGKILL137/container removal','old_container':child,'recovery':result})

    def test_sigkill_partial_write_exact_recovery(self):
        self.crash('after-effect','.octon/agent/state/focus.json')
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],0,result)
        self.assertEqual(result['result']['status'],'recovered_to_preimage')
        self.evidence.append({'case':self._testMethodName,'recovery':result})

    def test_receipt_published_unacknowledged_reconciles_without_replay(self):
        self.crash('published-unacknowledged',self.relative('receipt'))
        before=self.life.code('import hashlib,pathlib;print(hashlib.sha256(pathlib.Path("/state/target/'+self.relative('receipt')+'").read_bytes()).hexdigest())').stdout.strip()
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],0,result)
        self.assertEqual(result['result']['status'],'applied')
        after=self.life.code('import hashlib,pathlib;print(hashlib.sha256(pathlib.Path("/state/target/'+self.relative('receipt')+'").read_bytes()).hexdigest())').stdout.strip()
        self.assertEqual(before,after);self.lease,self.path=self.life.enroll(self.lease['generation'])
        replay=self.life.execute(self.path);self.assertEqual(replay['exit'],2);self.assertIn('consumed identity',replay['stdout'])
        self.evidence.append({'case':self._testMethodName,'receipt_before':before,'receipt_after':after,'result':result})

    def test_old_alive_controller_immutable_generation(self):
        child=self.life.execute(self.path,fault='before-lock:',detached=True);self.life.wait_file(child,'/tmp/fault-ready.json')
        self.lease,self.path=self.life.enroll(1);self.life.release(child)
        old=self.life.terminal(child);self.assertEqual(old['exit'],2,old);self.assertIn('stale immutable',old['stdout'])
        result=self.life.execute(self.path);self.assertEqual(result['exit'],0,result)
        self.evidence.append({'case':self._testMethodName,'old_process_alive_during_replacement':True,'old':old,'new':result})

    def test_queued_control_does_not_deadlock_holder_currentness(self):
        child=self.life.execute(self.path,fault='before-effect:.octon/agent/state/focus.json',detached=True)
        self.life.wait_file(child,'/tmp/fault-ready.json');results=[];errors=[]
        def stop():
            try:results.append(self.controls({'emergency_stop':True}))
            except Exception as error:errors.append(str(error))
        updater=threading.Thread(target=stop);updater.start()
        self.life.wait_file(self.life.keeper,'/tmp/control-contended.json')
        self.assertTrue(updater.is_alive());self.life.release(child)
        result=self.life.terminal(child);updater.join(60);self.assertFalse(updater.is_alive());self.assertFalse(errors,errors)
        self.assertEqual(result['exit'],0,result);self.assertEqual(len(results),1)
        self.lease,self.path=self.life.enroll(self.lease['generation'])
        denied=self.life.execute(self.path,'reconcile');self.assertEqual(denied['exit'],2);self.assertIn('current authority',denied['stdout'])
        self.evidence.append({'case':self._testMethodName,'order':'explicit control contention before holder next RPC; transaction ACK then stop; subsequent reconciliation refused','result':result,'control':results})

    def test_real_worker_persisted_store_exclusion_before_after_replacement(self):
        before=self.life.worker_probe()
        original=self.life.launches[self.path];self.life.destroy(original);self.life.launches.pop(self.path)
        self.replacement();after=self.life.worker_probe()
        result=self.life.execute(self.path,peer=True);self.assertEqual(result['exit'],0,result)
        self.assertEqual(result['result']['status'],'applied');self.assertEqual(result['result']['worker_cleanup']['remaining'],[])
        self.evidence.append({'case':self._testMethodName,'before':before,'after':after,'replacement_producing_peer':result,'preserved':self.preservation()})

    def test_consumption_without_journal_never_replays(self):
        identity=self.life.prepared['receipt_ref'];self.crash('after-effect','.octon/agent/transactions/durable/'+identity+'/consumed.json')
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('without original journal/receipt',result['stdout'])
        self.replacement();replay=self.life.execute(self.path);self.assertIn('consumed identity',replay['stdout'])
        self.evidence.append({'case':self._testMethodName,'recovery':result,'replay':replay})

    def test_prepared_missing_journal_preserves_uncertainty(self):
        self.crash('prepared',self.relative('journal'))
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('missing/truncated/changed publication',result['stdout'])
        self.evidence.append({'case':self._testMethodName,'recovery':result})

    def test_effects_before_missing_receipt_preserve_uncertainty(self):
        self.crash('before-effect',self.relative('receipt'))
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('missing/truncated/changed publication',result['stdout'])
        self.assertIn('Continue durable',self.life.code('from pathlib import Path;print(Path("/state/target/.octon/agent/state/focus.json").read_text())').stdout)
        self.evidence.append({'case':self._testMethodName,'recovery':result,'pending_retained':True})

    def test_confirmed_receipt_response_lost_reconciles_exact_history(self):
        self.crash('confirmed',self.relative('receipt'))
        before=self.life.code('from pathlib import Path;import hashlib;print(hashlib.sha256(Path("/state/target/'+self.relative('receipt')+'").read_bytes()).hexdigest())').stdout.strip()
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],0,result)
        after=self.life.code('from pathlib import Path;import hashlib;print(hashlib.sha256(Path("/state/target/'+self.relative('receipt')+'").read_bytes()).hexdigest())').stdout.strip()
        self.assertEqual(before,after);self.evidence.append({'case':self._testMethodName,'response_lost':'SIGKILL after confirmed receipt ACK before process response','receipt_sha256':after,'recovery':result,'preserved':self.preservation()})

    def test_stop_during_container_downtime_refuses_recovery(self):
        self.crash('after-effect',self.relative('journal'));self.controls({'emergency_stop':True})
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('current authority',result['stdout'])
        self.evidence.append({'case':self._testMethodName,'recovery':result})

    def test_revocation_during_container_downtime_refuses_recovery(self):
        self.crash('after-effect',self.relative('journal'))
        snapshot=self.life.admin('inspect')['authority']['bundle'];self.controls({'revoked_delegation_ids':[snapshot['delegations'][0]['id']]})
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('current authority',result['stdout'])
        self.evidence.append({'case':self._testMethodName,'recovery':result})

    def test_actual_expiry_during_downtime_without_grant_refresh(self):
        self.crash('after-effect',self.relative('journal'))
        from datetime import datetime,timezone,timedelta
        deadline=(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat();self.controls({'fresh_until':deadline})
        before=self.life.admin('inspect')['authority']['bundle'];grant_hash=self.life.digest(before['delegations']);control_hash=self.life.digest(before['controls'])
        value=self.life.code('import datetime,time;deadline=datetime.datetime.fromisoformat('+repr(deadline)+');\nwhile datetime.datetime.now(datetime.timezone.utc)<deadline:time.sleep(.01)\nprint(datetime.datetime.now(datetime.timezone.utc).isoformat())')
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('current authority',result['stdout'])
        after=self.life.admin('inspect')['authority']['bundle'];self.assertEqual(grant_hash,self.life.digest(after['delegations']));self.assertEqual(control_hash,self.life.digest(after['controls']))
        self.evidence.append({'case':self._testMethodName,'unchanged_grant_digest':grant_hash,'unchanged_control_digest':control_hash,'deadline':deadline,'observed_after_deadline':value.stdout.strip(),'recovery':result})

    def test_stale_authority_snapshot_cannot_resurrect_stop(self):
        self.life.code('from pathlib import Path;Path("/tmp/old-authority.json").write_bytes(Path("/authority/authority.json").read_bytes())')
        self.controls({'emergency_stop':True})
        self.life.code('from pathlib import Path;Path("/authority/authority.json").write_bytes(Path("/tmp/old-authority.json").read_bytes())')
        result=self.life.execute(self.path);self.assertEqual(result['exit'],2,result);self.assertIn('stale primary authority',result['stdout'])
        self.evidence.append({'case':self._testMethodName,'restoration':'actual authority file restore','result':result})

    def test_missing_corrupt_truncated_continuity_refuses(self):
        stale=self.life.code('from pathlib import Path;import base64;print(base64.b64encode(Path("/continuity/index.json").read_bytes()).decode())').stdout.strip()
        self.life.admin('inspect')
        saved=self.life.code('from pathlib import Path;import base64;print(base64.b64encode(Path("/continuity/index.json").read_bytes()).decode())').stdout.strip()
        cases=[]
        # Original live tip stays outside these file mutations. Each failed
        # admin read leaves it unchanged; restoring those exact current bytes
        # permits the next independent corruption probe, never a lower tip.
        for mode in ['missing','corrupt','truncated','stale']:
            code='from pathlib import Path;import base64; p=Path("/continuity/index.json");p.write_bytes(base64.b64decode('+repr(saved)+'));'
            code+= 'p.unlink()' if mode=='missing' else 'p.write_bytes(b"{broken")' if mode=='corrupt' else 'p.write_bytes(p.read_bytes()[:25])' if mode=='truncated' else 'p.write_bytes(base64.b64decode('+repr(stale)+'))'
            self.life.code(code)
            with self.assertRaises(ValueError) as failure:self.life.admin('inspect')
            cases.append({'mode':mode,'refused':True,'error':str(failure.exception)[:300]})
        self.evidence.append({'case':self._testMethodName,'probes':cases})

    def test_keeper_loss_new_key_deleted_markers_cannot_bootstrap(self):
        self.controls({'emergency_stop':True});self.assertEqual(self.life.destroy(self.life.keeper),'137')
        with self.assertRaises(ValueError):self.life.admin('inspect')
        self.assertTrue(self.life.retired)
        name=self.life.prefix+'-marker-loss';self.life.creation_intent('container',name)
        value=run(self.life.args(name,keeper=True)+[IMAGE,'python','-B','-c','from pathlib import Path;import shutil;Path("/state/target/.octon/agent/transactions/durable/authority-owner.json").unlink();shutil.rmtree("/continuity");'],check=False)
        self.life.creation_observed('container',name,value.returncode)
        # Mount roots cannot be removed; their lost marker/key files are the
        # intended fault. The retained consumed launch handle remains decisive.
        with self.assertRaisesRegex(ValueError,'lifetime cannot bootstrap'):self.life.start_keeper()
        fresh=self.life.prefix+'-fresh-keeper';self.life.creation_intent('container',fresh)
        result=run(self.life.args(fresh,keeper=True)+['-i',IMAGE,'python','-B','skills/octon-project-bootstrap/scripts/durable_fixture.py','--keeper','/authority/bootstrap.json'],input=secrets.token_hex(32)+'\n',check=False)
        self.life.creation_observed('container',fresh,result.returncode)
        self.assertNotEqual(result.returncode,0);self.assertIn('saved records/new key are not trusted initial launch',result.stderr)
        self.evidence.append({'case':self._testMethodName,'actual_keeper_sigkill':137,'retained_launch_refused':True,'fresh_key_bootstrap_refused':True,'marker_fault_exit':value.returncode})

    def test_backward_time_new_boot_unavailable_time_refuse(self):
        # Probe each fault independently against an exact saved current index;
        # unavailable/new-boot is modeled, not an engine/host reboot claim.
        for kind in ['backward_floor','new_boot','time_unavailable']:
            if kind!='backward_floor':
                self.life.cleanup();self.life=Lifetime();self.life.prepare();self.life.start_keeper();self.lease,self.path=self.life.enroll()
            self.life.admin('fault',{'kind':kind});result=self.life.execute(self.path)
            self.assertEqual(result['exit'],2,result);self.assertTrue(any(word in result['stdout'] for word in ['time','boot']))
            self.evidence.append({'case':self._testMethodName,'trusted_fault':kind,'actual_reboot_tested':False,'result':result})

    def test_concurrent_snapshot_is_immutable_and_signed(self):
        results=[];errors=[]
        def inspect():
            try:results.append(self.life.admin('inspect',{'snapshot_barrier':True}))
            except Exception as error:errors.append(str(error))
        child=threading.Thread(target=inspect);child.start();self.life.wait_file(self.life.keeper,'/tmp/snapshot-ready.json')
        self.controls({'emergency_stop':True});self.life.code('from pathlib import Path;Path("/tmp/snapshot-release").touch()');child.join(30)
        self.assertFalse(child.is_alive());self.assertFalse(errors,errors);self.assertFalse(results[0]['authority']['bundle']['controls']['emergency_stop'])
        self.assertTrue(self.life.admin('inspect')['authority']['bundle']['controls']['emergency_stop'])
        self.evidence.append({'case':self._testMethodName,'explicit_snapshot_barrier':True,'original_pin_signature_verified':True})

    def test_stale_control_cas_cannot_remove_newer_restriction(self):
        snapshot=self.life.admin('inspect')['authority'];old=snapshot['bundle']
        narrowed=dict(old['controls']['policy_scope']);narrowed['resources']=['resource:unrelated-fixture']
        self.controls({'policy_scope':narrowed})
        with self.assertRaisesRegex(ValueError,'stale current control CAS'):
            self.life.admin('control',{'bundle':old,'expected_control_generation':snapshot['control_generation'],'expected_control_digest':self.life.digest(old)})
        result=self.life.execute(self.path);self.assertEqual(result['exit'],2,result);self.assertIn('current authority',result['stdout'])
        self.evidence.append({'case':self._testMethodName,'delayed_old_control_refused':True,'result':result})

    def test_copied_launch_requires_actual_replacement_enrollment(self):
        # Remove the intended container without consuming its original action.
        old=self.life.launches.pop(self.path);self.life.destroy(old)
        results=[]
        original={'namespace':self.lease['pid_namespace'],'identity':self.lease['namespace_identity'],'controller_id':self.lease['id'],'generation':self.lease['generation']}
        for _ in range(3):
            result=self.life.execute(self.path);self.assertEqual(result['exit'],2,result);self.assertIn('unenrolled replacement controller namespace',result['stdout']);results.append(result)
        self.replacement();good=self.life.execute(self.path);self.assertEqual(good['exit'],0,good)
        self.evidence.append({'case':self._testMethodName,'original_enrollment':original,'copied_launches':results,'trusted_replacement':good})

    def test_exact_service_publication_kinds_schema_paths_and_deletion(self):
        name=self.life.launches[self.path]
        code='''import sys,json,fcntl,copy
sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts")
import durable_fixture as D
v=D.V.load(D.Path(sys.argv[1]));e=D.Executor(v['lease'],v['pin']);ref=v['lease']['context']['record'];b=v['lease']['context']['binding'];identity=ref['receipt_id'];results={}
with (D.IPC/'fence.lock').open('rb') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 attempts=[('kind overlap','history','.octon/agent/transactions/durable/'+identity+'/consumed.json',{},False),('forged journal','journal','.octon/agent/transactions/pending/'+identity+'.json',{'permission_grant':False,**ref},False),('footprint expansion','canonical','.octon/runtime/fixture_admission.py',{},False),('unsafe path','canonical','../outside',{},False),('terminal delete','receipt','.octon/agent/transactions/receipts/'+identity+'.json',{},True),('truthy delete','journal','.octon/agent/transactions/pending/'+identity+'.json',{},'true')]
 for label,kind,path,value,delete in attempts:
  try:e.call('prepare',{'kind':kind,'relative':path,'format':'json','value':value,'delete':delete});results[label]={'refused':False}
  except Exception as error:results[label]={'refused':True,'error':str(error)}
 try:e.call('admit',{'phase':'uncovered-recovery'});results['phase']={'refused':False}
 except Exception as error:results['phase']={'refused':True,'error':str(error)}
print(json.dumps(results))'''
        value=run(['docker','exec',name,'python','-B','-c',code,self.path]);proof=json.loads(value.stdout)
        self.assertTrue(all(row['refused'] for row in proof.values()),proof)
        good=self.life.execute(self.path);self.assertEqual(good['exit'],0,good)
        self.evidence.append({'case':self._testMethodName,'denials':proof,'legitimate_after_denials':good})

    def test_changed_postimage_and_forged_journal_refuse(self):
        self.crash('after-effect','.octon/agent/state/focus.json')
        self.life.code('from pathlib import Path;Path("/state/target/.octon/agent/state/focus.json").write_text("independent changed postimage")')
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('changed postimage',result['stdout'])
        self.assertEqual(self.life.code('from pathlib import Path;print(Path("/state/target/.octon/agent/state/focus.json").read_text())').stdout.strip(),'independent changed postimage')
        self.evidence.append({'case':self._testMethodName,'changed_postimage':result,'pending_preserved':True})

    def test_stale_terminal_receipt_and_task_snapshot_cannot_undo_rollback(self):
        first=self.life.execute(self.path);self.assertEqual(first['exit'],0,first)
        self.life.code('import shutil;shutil.copytree("/state/target","/tmp/applied-snapshot")')
        self.replacement();rolled=self.life.execute(self.path,'rollback');self.assertEqual(rolled['exit'],0,rolled);self.assertEqual(rolled['result']['status'],'rolled_back')
        archived=self.life.code('from pathlib import Path;import json,hashlib;p=Path("/state/target/.octon/agent/transactions/durable/'+self.life.prepared['receipt_ref']+'/archive");print(json.dumps([{ "name":r.name,"sha256":hashlib.sha256(r.read_bytes()).hexdigest(),"status":json.loads(r.read_text()).get("status")} for r in sorted(p.glob("*.json"))]))').stdout
        history=json.loads(archived);self.assertTrue(any(row['status']=='applied' for row in history));self.assertTrue(any(row['status']=='rollback_in_progress' for row in history));self.assertTrue(any(row['status']=='rolled_back' for row in history))
        self.replacement()
        self.life.code('import shutil;from pathlib import Path;src=Path("/tmp/applied-snapshot");dst=Path("/state/target");paths='+repr([self.relative('receipt')])+''';import json
receipt=json.loads((src/paths[0]).read_text())
for relative in paths+[r['path'] for r in receipt['paths']]:shutil.copy2(src/relative,dst/relative)
''')
        result=self.life.execute(self.path,'reconcile');self.assertEqual(result['exit'],2,result);self.assertIn('stale/missing durable canonical record',result['stdout'])
        self.evidence.append({'case':self._testMethodName,'rollback':rolled,'exact_readable_historical_receipts':history,'actual_partial_snapshot_restoration':result,'preserved':self.preservation()})

    def test_mock_attempt_lost_outcome_no_reinvocation_after_replacement(self):
        first=self.life.execute(self.path,fault='mock-unknown');self.assertEqual(first['exit'],2,first);self.assertIn('mock provider response deliberately lost',first['stdout'])
        count=self.life.admin('inspect')['mock_attempts'];self.assertEqual(count,1)
        self.life.destroy(first['container']);self.replacement()
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('unknown mock external outcome',result['stdout'])
        self.assertEqual(self.life.admin('inspect')['mock_attempts'],1)
        self.replacement();retry=self.life.execute(self.path);self.assertEqual(retry['exit'],2,retry);self.assertIn('consumed identity',retry['stdout'])
        self.assertEqual(self.life.admin('inspect')['mock_attempts'],1)
        self.evidence.append({'case':self._testMethodName,'attempt':first,'replacement_recovery':result,'retry':retry,'actual_mock_invocations':1,'reconciliation':'original unknown outcome remains unresolved; no retry permitted','real_provider':False})

    def test_copied_runtime_without_source_siblings_or_plectarium(self):
        original=self.life.launches.pop(self.path);self.life.destroy(original)
        self.lease,self.path=self.life.enroll(1,independent=True)
        container=self.life.launches[self.path]
        checked=self.life.code('import subprocess,sys,pathlib,json;assert not pathlib.Path("/source").exists();r=subprocess.run([sys.executable,"-I","-B","octon","check"],capture_output=True,text=True);print(json.dumps({"exit":r.returncode,"stderr":r.stderr}));sys.exit(r.returncode)',container=container)
        result=self.life.execute(self.path,peer=True);self.assertEqual(result['exit'],0,result)
        self.evidence.append({'case':self._testMethodName,'no_source_mount':True,'isolated_python':True,'plectarium_present':False,'basic_check':json.loads(checked.stdout),'actual_narrow_effect':result})

    def test_mixed_profile_missing_dependency_and_unsafe_overlay_refuse(self):
        code='''import sys,json,copy,os
sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts")
import durable_fixture as D
p=D.ROOT/'.octon/durable-profile.json';saved=p.read_bytes();good=D.V.load(p);results={}
for label,change in [('omitted assets',{'assets':[]}),('mixed version',{'schema_version':'future'}),('unsupported host',{'host_profile':'windows'}),('wrong origin',{'source_revision':'0'*40})]:
 value=copy.deepcopy(good);value.update(change);p.write_text(json.dumps(value))
 try:D.profile();results[label]=False
 except Exception:results[label]=True
 p.write_bytes(saved)
asset=D.ROOT/'.octon/runtime/durable_fixture.py';asset.rename('/state/missing-durable.py')
try:D.profile();results['missing dependency']=False
except Exception:results['missing dependency']=True
finally:D.Path('/state/missing-durable.py').rename(asset)
for path in ['../outside','a/../b','C:/drive','a\\\\b','a/CON','a.','/absolute']:
 try:D.confined(D.ROOT,path);results[path]=False
 except ValueError:results[path]=True
print(json.dumps(results))'''
        results=json.loads(self.life.code(code).stdout);self.assertTrue(all(results.values()),results)
        good=self.life.execute(self.path);self.assertEqual(good['exit'],0,good)
        self.evidence.append({'case':self._testMethodName,'denials':results,'legitimate_after_exact_restoration':good})

    def test_unacknowledged_directory_publication_replacement_syncs_record(self):
        self.crash('published-before-directory-sync',self.relative('journal'))
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],0,result);self.assertEqual(result['result']['status'],'recovered_to_preimage')
        self.evidence.append({'case':self._testMethodName,'fault':'actual SIGKILL after rename before directory fsync','recovery':result,'power_loss_tested':False})

    def test_tombstone_before_directory_ack_replacement_reconciles(self):
        self.crash('deleted-before-directory-sync',self.relative('journal'))
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],0,result);self.assertEqual(result['result']['status'],'applied')
        self.evidence.append({'case':self._testMethodName,'fault':'actual SIGKILL after exact journal unlink before directory fsync','recovery':result})

    def test_actual_expiry_after_admission_and_mid_multiwrite_refuses_next_effect(self):
        from datetime import datetime
        capture_code=r'''import json,sys
sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts")
import durable_fixture as D
record=D.V.load(D.AUTH/'bootstrap.json')['context']['record'];state=D.V.load(D.CURRENT/'index.json')
print(json.dumps({'observed_at':D.effective_time(state).isoformat(),'planned_paths':[{key:row[key] for key in ['path','before','after']} for row in record['paths']],
 'actual_paths':[D.path_state(D.confined(D.ROOT,row['path']),row['path']) for row in record['paths']],
 'journal_exists':(D.ROOT/'.octon/agent/transactions/pending'/(record['receipt_id']+'.json')).is_file(),
 'consumption_exists':(D.ROOT/'.octon/agent/transactions/durable'/record['receipt_id']/'consumed.json').is_file()}))'''
        for position in ['.octon/agent/state/focus.json','.octon/dossier/MANIFEST.json']:
            if position!='.octon/agent/state/focus.json':
                cleanup=self.life.cleanup();self.evidence.append({'case':self._testMethodName,'subfixture_cleanup':cleanup})
                self.life=Lifetime();self.life.prepare();self.life.start_keeper();self.lease,self.path=self.life.enroll()
            original=self.life.admin('inspect')['authority']['bundle']
            deadline=self.life.code('from datetime import datetime,timezone,timedelta;print((datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat())').stdout.strip()
            chosen=datetime.fromisoformat(deadline)
            self.assertLessEqual(chosen,datetime.fromisoformat(original['controls']['fresh_until']))
            caps=[row['valid_until'] for row in original['delegations']]+[row['fresh_until'] for row in original['controls']['obligation_results']]+[row['period_accounting']['end'] for row in original['controls']['budget_snapshots']]
            self.assertTrue(all(chosen<datetime.fromisoformat(value) for value in caps))
            self.controls({'fresh_until':deadline});before=self.life.admin('inspect')['authority']['bundle']
            self.assertEqual(before['controls']['fresh_until'],deadline)
            self.assertEqual(before['delegations'],original['delegations'])
            self.assertEqual(before['controls']['obligation_results'],original['controls']['obligation_results'])
            self.assertEqual(before['controls']['budget_snapshots'],original['controls']['budget_snapshots'])
            checkpoint('expiry_deadline_armed',case=self._testMethodName,position=position,window_seconds=60,deadline=deadline,
                       original_fresh_until=original['controls']['fresh_until'],original_bundle_digest=self.life.digest(original),
                       narrowed_bundle_digest=self.life.digest(before),grant_digest=self.life.digest(before['delegations']))
            child=self.life.execute(self.path,fault='before-effect:'+position,detached=True);self.life.wait_file(child,'/tmp/fault-ready.json')
            ready=json.loads(self.life.code('from pathlib import Path;print(Path("/tmp/fault-ready.json").read_text())',container=child).stdout)
            self.assertEqual(ready['fault'],'before-effect:'+position)
            barrier=json.loads(self.life.code(capture_code).stdout)
            self.assertLess(datetime.fromisoformat(barrier['observed_at']),chosen,'intended barrier missed the fixed freshness window; no retry')
            planned={row['path']:row for row in barrier['planned_paths']};actual={row['path']:row for row in barrier['actual_paths']}
            self.assertEqual(actual[position],planned[position]['before'])
            earlier=[path for path,row in planned.items() if row['before']!=row['after'] and actual[path]==row['after']]
            if position=='.octon/dossier/MANIFEST.json':self.assertTrue(earlier,'later barrier must prove an earlier original planned postimage')
            else:self.assertFalse(earlier,'first barrier must precede any original canonical effect')
            self.assertTrue(barrier['journal_exists']);self.assertTrue(barrier['consumption_exists'])
            checkpoint('expiry_barrier_fresh',case=self._testMethodName,position=position,deadline=deadline,observed_at=barrier['observed_at'],
                       remaining_seconds=(chosen-datetime.fromisoformat(barrier['observed_at'])).total_seconds(),earlier_planned_postimages=earlier)
            observed=self.life.code('import sys,time;sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts");import durable_fixture as D;deadline=D.A.timestamp('+repr(deadline)+');clock=D.V.load(D.CURRENT/"index.json");\nwhile D.effective_time(clock)<deadline:time.sleep(.01)\nprint(D.effective_time(clock).isoformat())').stdout.strip()
            self.assertGreaterEqual(datetime.fromisoformat(observed),chosen)
            self.life.release(child);result=self.life.terminal(child);self.assertEqual(result['exit'],2,result);self.assertIn('current authority',result['stdout'])
            after=self.life.admin('inspect')['authority']['bundle'];self.assertEqual(before,after)
            retained=json.loads(self.life.code(capture_code).stdout)
            self.assertEqual(retained['actual_paths'],barrier['actual_paths'])
            self.assertTrue(retained['journal_exists']);self.assertTrue(retained['consumption_exists'])
            self.evidence.append({'case':self._testMethodName,'explicit_barrier':position,'ready':ready,'original_bundle_digest':self.life.digest(original),
                                  'narrowed_bundle_digest':self.life.digest(before),'unchanged_grant_digest':self.life.digest(before['delegations']),
                                  'unchanged_grants_and_controls':True,'fixed_freshness_seconds':60,'deadline':deadline,'original_fresh_until':original['controls']['fresh_until'],
                                  'unchanged_grant_obligation_accounting_caps':caps,'barrier':barrier,'earlier_planned_postimages':earlier,
                                  'actual_time_after_deadline':observed,'retained':retained,'no_later_canonical_transition':True,'result':result})

    def test_owned_driver_sigterm_cleans_key_bearing_resources(self):
        with tempfile.TemporaryDirectory(prefix='octon-owned-driver-interrupt-') as temporary:
            area=Path(temporary);barrier=area/'ready.json';output=area/'interrupted.json';log=area/'driver.log'
            with log.open('w') as stream:
                process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--qualify-owned-durable-fixture','--launch-barrier',str(barrier),'--output',str(output),'test_actual_narrow_committer_and_container_replacement'],stdout=stream,stderr=stream)
                try:
                    deadline=time.monotonic()+180
                    while not barrier.is_file():
                        if process.poll() is not None or time.monotonic()>deadline:raise ValueError('owned interrupted driver readiness failed: '+log.read_text())
                        time.sleep(.05)
                    owned=json.loads(barrier.read_text());process.send_signal(signal.SIGTERM);exit=process.wait(timeout=90)
                finally:
                    if process.poll() is None:process.send_signal(signal.SIGTERM);process.wait(timeout=90)
            record=json.loads(output.read_text());self.assertEqual(exit,130);self.assertTrue(record['aborted']);self.assertFalse(record['qualified']);self.assertFalse(record['cleanup_unknown'])
            self.assertTrue(all(inspect_owned('volume',name,owned['prefix']) is None for name in owned['volumes']))
            self.assertTrue(all(inspect_owned('container',name,owned['prefix']) is None for name in owned['containers']))
            self.evidence.append({'case':self._testMethodName,'termination':'actual owned host driver SIGTERM handled as interruption','exit':exit,'owned_key_volumes_removed':True,'interrupted_record':{key:record[key] for key in ['qualified','aborted','cleanup_unknown','resource_intents_and_cleanup']},'sigkill_of_driver_tested':False})

    def test_actual_stale_journal_restore_after_tombstone_refuses(self):
        first=self.life.execute(self.path);self.assertEqual(first['exit'],0,first);self.replacement()
        code='from pathlib import Path;import shutil;p=Path("/state/target/.octon/agent/transactions/durable/'+self.life.prepared['receipt_ref']+'/archive");src=next(p.glob("journal-*.json"));shutil.copy2(src,Path("/state/target/'+self.relative('journal')+'"))'
        self.life.code(code)
        result=self.life.execute(self.path,'recover');self.assertEqual(result['exit'],2,result);self.assertIn('restored tombstoned record',result['stdout'])
        self.evidence.append({'case':self._testMethodName,'actual_stale_journal_restore':True,'result':result})

    def test_terminal_ack_rejects_wrong_filesystem_kind(self):
        first=self.life.execute(self.path);self.assertEqual(first['exit'],0,first);self.replacement()
        self.life.code('from pathlib import Path;p=Path("/state/target/.octon/agent/state/focus.json");p.unlink();p.mkdir()')
        name=self.life.launches[self.path]
        code='''import sys,fcntl,json
sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts")
import durable_fixture as D
v=D.V.load(D.Path(sys.argv[1]));e=D.Executor(v['lease'],v['pin'])
with (D.IPC/'fence.lock').open('rb') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 try:e.call('confirm',{'kind':'receipt','relative':sys.argv[2]});print(json.dumps({'refused':False}))
 except Exception as error:print(json.dumps({'refused':True,'error':str(error)}))'''
        result=json.loads(run(['docker','exec',name,'python','-B','-c',code,self.path,self.relative('receipt')]).stdout)
        self.assertTrue(result['refused']);self.assertIn('terminal ACK postimage',result['error'])
        self.evidence.append({'case':self._testMethodName,'existing_directory_not_absence':True,'result':result})

    def test_enrollment_rejects_missing_extra_wrong_type_identity_and_truncated_rights(self):
        name=self.life.launches[self.path];snapshot=self.life.admin('inspect')['authority'];proof=self.lease
        base={'expected_generation':1,'pid_namespace':proof['pid_namespace'],'namespace_identity':proof['namespace_identity'],'expected_control_generation':snapshot['control_generation'],'expected_control_digest':self.life.digest(snapshot['bundle'])}
        records=[]
        for mode,reason in [('missing','exactly one'),('extra','exactly one'),('wrong_type','not an actual PID namespace'),('wrong_identity','differs from signed launch subject'),('truncated','truncated namespace descriptor')]:
            body=dict(base)
            if mode=='wrong_identity':body['namespace_identity']=[body['namespace_identity'][0],body['namespace_identity'][1]+1]
            envelope=self.life.sign_enrollment(body);packet='/tmp/negative-enrollment.json'
            run(['docker','exec','-i',name,'python','-B','-c','from pathlib import Path;import sys;Path(sys.argv[1]).write_text(sys.stdin.read());Path(sys.argv[1]).chmod(0o600)',packet],input=json.dumps({'envelope':envelope,'pin':self.life.pin,'mode':mode}))
            code='''import sys,os,json
sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts")
import durable_fixture as D
v=D.V.load(D.Path(sys.argv[1]));mode=v['mode'];fd=os.open('/proc/self/ns/user' if mode=='wrong_type' else '/proc/self/ns/pid',os.O_RDONLY|os.O_CLOEXEC)
try:
 rights=[] if mode=='missing' else [fd,fd] if mode=='extra' else [fd]*16 if mode=='truncated' else [fd]
 try:D.exchange(v['pin'],v['envelope'],rights);print(json.dumps({'refused':False}))
 except Exception as error:print(json.dumps({'refused':True,'error':str(error)}))
finally:os.close(fd)'''
            result=json.loads(run(['docker','exec',name,'python','-B','-c',code,packet]).stdout);self.assertTrue(result['refused'],result);self.assertIn(reason,result['error']);records.append({'mode':mode,**result})
            self.assertEqual(self.life.admin('inspect')['authority']['generation'],1)
        good=self.life.execute(self.path);self.assertEqual(good['exit'],0,good)
        self.evidence.append({'case':self._testMethodName,'actual_scm_rights_denials':records,'legitimate_original':good})

    def test_lost_retained_namespace_handle_refuses_currentness_and_replacement(self):
        self.life.admin('fault',{'kind':'close_namespace'})
        result=self.life.execute(self.path);self.assertEqual(result['exit'],2,result);self.assertIn('retained actual controller namespace handle unavailable',result['stdout'])
        with self.assertRaisesRegex(ValueError,'retained actual controller namespace handle unavailable'):self.life.admin('inspect')
        self.evidence.append({'case':self._testMethodName,'actual_retained_fd_closed':True,'saved_identity_not_used_to_reopen':True,'result':result})

    def test_keyless_seed_binding_corruption_records_and_confinement_refuse(self):
        name=self.life.prefix+'-seed-negative';self.life.creation_intent('container',name)
        argv=self.life.args(name,keeper=True)+['-v',SEED.volumes[0]+':/seed:rw','-i',IMAGE,'python','-B','-c']
        code=r'''import sys,json,copy,os
from pathlib import Path
sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts")
import qualify_disposable_runtime as Q
v=json.loads(sys.stdin.read());expected=v['binding'];results={};seed=Path('/seed')
def reject(label,binding=None,image=None,name='plain'):
 try:Q.materialize_keyless_seed(seed,name,Path('/tmp/rejected-'+str(len(results))),binding or expected,image or v['image']);results[label]={'refused':False}
 except ValueError as error:results[label]={'refused':True,'reason':str(error)}
wrong=copy.deepcopy(expected);wrong['source']['revision']='0'*40;reject('independent source mismatch',wrong)
reject('image mismatch',image='sha256:'+'0'*64)
target=seed/'plain/octon';saved=target.read_bytes();target.write_bytes(saved+b'\n# corruption\n');reject('corrupt source-owned bytes');target.write_bytes(saved)
record=seed/'plain/.octon/agent/tasks/TASK-9999.md';record.parent.mkdir(exist_ok=True);record.write_text('project fact');reject('project record injection');record.unlink()
link=seed/'unsafe-link';link.symlink_to('/tmp');reject('seed symlink');link.unlink()
reject('writable custody')
print(json.dumps(results))'''
        value=run(argv+[code],input=json.dumps({'binding':SEED.binding,'image':SEED.image}));self.life.creation_observed('container',name,value.returncode);results=json.loads(value.stdout)
        self.assertTrue(all(row['refused'] for row in results.values()),results)
        self.assertEqual(results['writable custody']['reason'],'keyless seed requires readonly owned kernel volume')
        readonly=self.life.prefix+'-seed-readonly-negative';self.life.creation_intent('container',readonly)
        code=r'''import sys,json
from pathlib import Path
sys.path.insert(0,"/source/skills/octon-project-bootstrap/scripts")
import qualify_disposable_runtime as Q
v=json.loads(sys.stdin.read());target=Path('/tmp/outside')
try:Q.materialize_keyless_seed(Path('/seed'),'../outside',target,v['binding'],v['image']);result={'refused':False}
except ValueError as error:result={'refused':True,'reason':str(error),'target_absent':not target.exists()}
print(json.dumps(result))'''
        value=run(self.life.args(readonly,seed=True)+['-i',IMAGE,'python','-B','-c',code],input=json.dumps({'binding':SEED.binding,'image':SEED.image}))
        self.life.creation_observed('container',readonly,value.returncode);results['portable traversal']=json.loads(value.stdout)
        self.assertTrue(results['portable traversal']['refused']);self.assertTrue(results['portable traversal']['target_absent'])
        self.assertEqual(results['portable traversal']['reason'],'fresh exact seed destination required')
        selector=self.life.prefix+'-public-durable-selector';self.life.creation_intent('container',selector)
        code=r'''import hashlib,json,subprocess,sys
from pathlib import Path
source=Path('/source');target=Path('/tmp/public-durable-selector');expected=json.loads(sys.stdin.read())
assert not target.exists()
commands=[]
def command(argv,cwd):
 value=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,check=False)
 row={'argv':argv,'exit':value.returncode,'stdout':value.stdout,'stderr':value.stderr};commands.append(row)
 assert value.returncode==0,row
 return value
generation=command([sys.executable,'-B',str(source/'skills/octon-project-bootstrap/scripts/qualify_disposable_runtime.py'),'--target',str(target),'--disposable-qualification','--admission-qualification','--protected-fixture-qualification','--durable-fixture-qualification'],source)
command([sys.executable,'-I','-B',str(target/'octon'),'check'],target)
inspection=command([sys.executable,'-I','-B',str(target/'.octon/runtime/durable_fixture.py'),'--inspect-root',str(target)],target)
load=lambda path:json.loads(path.read_text())
manifest=load(target/'.octon/manifest.json');protected=load(target/'.octon/protected-profile.json');durable=load(target/'.octon/durable-profile.json');inspected=json.loads(inspection.stdout)
assert json.loads(generation.stdout)['source_revision']==expected['revision']
assert manifest['source_revision']==protected['source_revision']==durable['source_revision']==expected['revision']
assert manifest['schema_version']=='octon.disposable-installation.v2'
assert protected['schema_version']=='octon.protected-fixture-profile.v1' and durable['schema_version']=='octon.durable-fixture-profile.v2'
assert all(row['permission_grant'] is False for row in [manifest,protected,durable,inspected])
assert inspected['execution_authorized'] is False and inspected['profile']==durable and durable['parent_profile']==protected
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert protected['installation_digest']==digest(target/'.octon/manifest.json')
assets=manifest['assets']+protected['assets']+durable['assets']
inputs=manifest['inputs']+protected['source_inputs']+durable['source_inputs']
assert len(durable['assets'])==3 and len(durable['source_inputs'])==4
assert all(digest(target/row['path'])==row['sha256'] for row in assets)
assert all(digest(source/row['path'])==row['sha256']==expected['inputs'][row['path']] for row in inputs)
unexpected=[]
for path in target.rglob('*'):
 if not path.is_file():continue
 relative=path.relative_to(target).as_posix()
 if path.suffix=='.pem' or path.name in {'bootstrap.json','anchor.json','index.json','authority-owner.json','authority.json'} or relative.startswith('.octon/agent/transactions/') or path.name.startswith(('TASK-','DEC-','EVD-','RCPT-','WCR-')) and '/tests/fixtures/' not in '/'+relative:unexpected.append(relative)
assert not unexpected,unexpected
print(json.dumps({'public_selector_commands':commands,'source_revision':expected['revision'],'manifest':manifest,'protected_profile':protected,'durable_profile':durable,'asset_bindings_verified':len(assets),'source_bindings_verified':len(inputs),'fresh_tmpfs_target':str(target),'no_key_enrollment_currentness_consumption_records':not unexpected,'execution_authorized':False,'permission_grant':False},sort_keys=True))'''
        value=run(self.life.args(selector)+['-i',IMAGE,'python','-B','-c',code],input=json.dumps(SEED.binding['source']))
        self.life.creation_observed('container',selector,value.returncode);packaging=json.loads(value.stdout)
        self.assertEqual(packaging['source_revision'],SEED.binding['source']['revision'])
        self.assertTrue(packaging['no_key_enrollment_currentness_consumption_records']);self.assertFalse(packaging['execution_authorized'])
        self.assertTrue(all(row['exit']==0 for row in packaging['public_selector_commands']))
        self.evidence.append({'case':self._testMethodName,'noncurrent_seed_only':True,'actual_denials':results,'fresh_public_durable_selector':packaging})

    def test_internal_deadline_exports_partial_and_cleans_owned_keys(self):
        with tempfile.TemporaryDirectory(prefix='octon-owned-soft-deadline-') as temporary:
            area=Path(temporary);barrier=area/'ready.json';output=area/'partial.json';log=area/'deadline.log'
            with log.open('w') as stream:
                process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--qualify-owned-durable-fixture','--qualification-seconds','180','--launch-barrier',str(barrier),'--output',str(output),'test_actual_narrow_committer_and_container_replacement'],stdout=stream,stderr=stream)
                try:exit=process.wait(timeout=310)
                finally:
                    if process.poll() is None:process.send_signal(signal.SIGTERM);process.wait(timeout=130)
            self.assertTrue(barrier.is_file(),'deadline fixture did not reach real enrolled key-bearing state')
            owned=json.loads(barrier.read_text());record=json.loads(output.read_text())
            self.assertEqual(exit,130);self.assertTrue(record['aborted']);self.assertFalse(record['qualified']);self.assertFalse(record['cleanup_unknown'])
            self.assertTrue(all(inspect_owned('volume',name,owned['prefix']) is None for name in owned['volumes']))
            self.assertIn('OCTON_DURABLE_CHECKPOINT',log.read_text())
            self.evidence.append({'case':self._testMethodName,'internal_deadline_seconds':180,'elapsed_seconds':record['elapsed_seconds'],'actual_key_state_reached':True,'partial_unqualified':True,'owned_cleanup_verified':True})


def main():
    global LAUNCH_BARRIER,SEED,DEADLINE,CLEANUP_UNTIL
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualify-owned-durable-fixture',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--emit-evidence',action='store_true')
    parser.add_argument('--launch-barrier',type=Path)
    parser.add_argument('--qualification-seconds',type=float,default=2400)
    parser.add_argument('tests',nargs='*')
    args=parser.parse_args()
    if not args.qualify_owned_durable_fixture:
        print(json.dumps({'qualified':False,'permission_grant':False,'consequential_execution':'disabled','reason':'explicit owned durable fixture qualification required'}));return 0
    started=time.monotonic();DEADLINE=started+args.qualification_seconds
    if args.qualification_seconds<=0 or args.qualification_seconds>2400:raise ValueError('qualification deadline must leave cleanup/export margin before45m')
    subject=source_subject()
    names=args.tests or [name for name in DurableTests.__dict__ if name.startswith('test_')];LAUNCH_BARRIER=args.launch_barrier
    class Runner(unittest.TextTestRunner):
        def _makeResult(self):self.current_result=super()._makeResult();return self.current_result
    runner=Runner(verbosity=2);aborted=False;preparation_error=None;cleanup_unknown=[];result=unittest.TestResult()
    def interrupted(*_):raise QualificationDeadline
    signal.signal(signal.SIGTERM,interrupted)
    if hasattr(signal,'SIGALRM'):signal.signal(signal.SIGALRM,interrupted);signal.setitimer(signal.ITIMER_REAL,args.qualification_seconds)
    try:
        SEED=KeylessSeed()
        result=runner.run(unittest.TestSuite(DurableTests(name) for name in names))
    except KeyboardInterrupt:aborted=True;result=getattr(runner,'current_result',unittest.TestResult())
    except Exception as error:
        preparation_error={'type':type(error).__name__,'reason':str(error)}
        result=getattr(runner,'current_result',result)
        checkpoint('preparation_failed',error=preparation_error)
    finally:
        if hasattr(signal,'SIGALRM'):signal.setitimer(signal.ITIMER_REAL,0)
        CLEANUP_UNTIL=time.monotonic()+120
        for lifetime in list(reversed(ACTIVE_LIFETIMES)):
            try:RESOURCE_EVENTS.append({'interruption_cleanup':lifetime.cleanup(),'prefix':lifetime.prefix})
            except BaseException as error:
                unknown={'prefix':lifetime.prefix,'resources':lifetime.volumes+lifetime.containers,'reason':str(error)}
                cleanup_unknown.append(unknown);checkpoint('owned_cleanup_unknown',**unknown)
    complete=set(names)=={name for name in DurableTests.__dict__ if name.startswith('test_')} and result.testsRun==len(names) and not aborted and preparation_error is None
    try:unchanged=source_subject()==subject
    except (OSError,subprocess.SubprocessError):unchanged=False;cleanup_unknown.append({'reason':'final local source observation unavailable'})
    passed=result.wasSuccessful() and not aborted and preparation_error is None and not cleanup_unknown and unchanged and result.testsRun==len(names)
    evidence={'schema_version':'octon.durable-fixture-qualification.v1','permission_grant':False,'qualified':passed and complete,'targeted_passed':passed,'complete_suite':complete,'aborted':aborted,'preparation_error':preparation_error,'cleanup_unknown':cleanup_unknown,
              'tests_run':result.testsRun,'tests_expected':len(names),'errors':len(result.errors)+(1 if preparation_error else 0),'failures':len(result.failures),'cases':DurableTests.evidence,
              'source_revision':subject['revision'],'resource_intents_and_cleanup':RESOURCE_EVENTS,
              'source_subject':subject,'source_unchanged':unchanged,
              'elapsed_seconds':round(time.monotonic()-started,6),'qualification_deadline_seconds':args.qualification_seconds,'keyless_seed_compile_seconds':SEED.seconds if SEED else None,
              'supported_replacement':'actual committer containers only; original independent keeper/launch handle/engine boot retained',
              'unqualified':['keeper/all-anchor rollback','engine restart','host reboot','power loss','live grants/providers/consumers']}
    if args.output:args.output.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
    if args.emit_evidence:print('OCTON_DURABLE_EVIDENCE_BEGIN\n'+json.dumps(evidence,sort_keys=True)+'\nOCTON_DURABLE_EVIDENCE_END')
    print(json.dumps({key:evidence[key] for key in ['schema_version','qualified','targeted_passed','tests_run','errors','failures','aborted','preparation_error','cleanup_unknown','source_revision','supported_replacement','unqualified']}));return 130 if aborted else 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
