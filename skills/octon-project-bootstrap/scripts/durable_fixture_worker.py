#!/usr/bin/env python3
"""Non-secret producing fixture client, never an authority evaluator or signer."""
from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import socket
import time
import sys

def worker_child(mode,argument,output):
    """Clean exec after real privilege/FD/environment drop; no worker key."""
    import errno
    if os.geteuid()!=65534:raise ValueError('worker entry requires dropped identity')
    status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if ':' in line}
    if mode=='probe':
        value=json.loads(Path(argument).read_text());denied={}
        for path in value['targets']:
            for mode in ['read','write']:
                try:Path(path).open('rb' if mode=='read' else 'ab').close();denied[path+' '+mode]=False
                except OSError as error:denied[path+' '+mode]=error.errno in {errno.EACCES,errno.EPERM,errno.EROFS}
        for suffix in ['mem','environ','fd/0','root','cwd']:
            try:Path('/proc/'+str(value['owner_pid'])+'/'+suffix).open('rb').close();denied['proc '+suffix]=False
            except OSError as error:denied['proc '+suffix]=error.errno in {errno.EACCES,errno.EPERM}
        try:os.fstat(value['inherited_fd']);denied['inherited credential fd']=False
        except OSError as error:denied['inherited credential fd']=error.errno==errno.EBADF
        try:Path('/source/skills/octon-project-bootstrap/scripts/durable_fixture.py').open('ab').close();denied['read-only source write']=False
        except OSError as error:denied['read-only source write']=error.errno in {errno.EACCES,errno.EPERM,errno.EROFS}
        try:
            with socket.socket(socket.AF_UNIX) as channel:channel.connect('/ipc/keeper.sock')
            denied['protected keeper socket']=False
        except OSError as error:denied['protected keeper socket']=error.errno in {errno.EACCES,errno.EPERM}
        for label,operation in [('setuid',lambda:os.setuid(0)),('groups',lambda:os.setgroups([0])),('clock',lambda:time.clock_settime(time.CLOCK_REALTIME,0)),('SIGCONT',lambda:os.kill(value['owner_pid'],18))]:
            try:operation();denied[label]=False
            except OSError as error:denied[label]=error.errno==errno.EPERM
        libc=ctypes.CDLL(None,use_errno=True);denied['ptrace']=libc.ptrace(16,value['owner_pid'],0,0)==-1 and ctypes.get_errno() in {errno.EPERM,errno.EACCES}
        denied['stdio disconnected']=all(os.readlink('/proc/self/fd/'+str(fd))=='/dev/null' for fd in [0,1,2])
        denied['docker socket absent']=not Path('/var/run/docker.sock').exists()
        Path(output).parent.joinpath('proposal').write_text('worker-owned proposal')
        result={'denials':denied,'privileges':{key:status[key] for key in ['Uid','Gid','Groups','CapInh','CapPrm','CapEff','CapBnd','CapAmb','NoNewPrivs','Seccomp']},'environment_clean':dict(os.environ)=={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','LC_CTYPE':'C.UTF-8'}}
    else:
        value=json.loads(Path(argument).read_text());request=value['request'];responses=[]
        invalid=[dict(request,actor_ref='agent:other'),dict(request,action_digest='0'*64),dict(request,issuer_ref='self-enrolled'),dict(request,command='rollback'),dict(request,permission_grant=True)]
        for item in invalid+[request,request]:
            with socket.socket(socket.AF_UNIX) as channel:
                channel.connect(value['socket']);channel.sendall((json.dumps(item,sort_keys=True,separators=(",",":"))+"\n").encode())
                with channel.makefile('rb') as stream:responses.append(json.loads(stream.readline(1024*1024+1)))
        result={'responses':responses,'worker_uid':os.geteuid(),'credentials_created':False}
        orphan=os.fork()
        if orphan==0:
            os.setsid();ctypes.CDLL(None).prctl(4,0,0,0,0)
            while True:time.sleep(1)
    Path(output).write_text(json.dumps(result));Path(output).chmod(0o644)


if __name__=='__main__':
    worker_child(sys.argv[1],sys.argv[2],sys.argv[3])
