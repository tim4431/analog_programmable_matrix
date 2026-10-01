"""Read ordinary LTspice binary real/complex raw files (no external parser)."""
from pathlib import Path
import numpy as np
def read_raw(path):
    data=Path(path).read_bytes()
    marker='Binary:\n'.encode('utf-16le')
    if marker in data:
        pos=data.index(marker)+len(marker);header=data[:pos].decode('utf-16le')
    else:
        marker=b'Binary:\n';pos=data.index(marker)+len(marker);header=data[:pos].decode('utf-8')
    info={}
    for line in header.splitlines():
        if ': ' in line:
            key,value=line.split(': ',1);info[key]=value.strip()
    nv=int(info['No. Variables']);npnt=int(info['No. Points'])
    names=[]
    for line in header.split('Variables:\n',1)[1].split('Binary:')[0].splitlines():
        if line.strip():names.append(line.split()[1].lower())
    assert len(names)==nv
    assert 'FastAccess' not in info.get('Flags',''),info
    if 'complex' in info['Flags']:
        arr=np.frombuffer(data,offset=pos,dtype='<c16',count=nv*npnt).reshape(npnt,nv)
        return info,{n:arr[:,i] for i,n in enumerate(names)}
    if 'double' in info['Flags']:
        arr=np.frombuffer(data,offset=pos,dtype='<f8',count=nv*npnt).reshape(npnt,nv)
        return info,{n:arr[:,i] for i,n in enumerate(names)}
    dt=np.dtype([('x','<f8'),('y','<f4',(nv-1,))])
    arr=np.frombuffer(data,offset=pos,dtype=dt,count=npnt)
    return info,{names[0]:abs(arr['x']),**{n:arr['y'][:,i-1] for i,n in enumerate(names[1:],1)}}
if __name__=='__main__':
    import sys
    info,v=read_raw(sys.argv[1]);print(info)
    for n,a in v.items():print(n,len(a),'first',a[0],'last',a[-1])
