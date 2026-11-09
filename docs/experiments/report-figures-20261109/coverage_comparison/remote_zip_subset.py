import io, json, zipfile, requests, argparse, hashlib
from pathlib import Path

class RemoteFile(io.RawIOBase):
    def __init__(self, url):
        self.url=url; self.pos=0; self.transferred=0
        with requests.get(url, headers={'Range':'bytes=-22'}, stream=True, timeout=45) as r:
            if r.status_code!=206: raise RuntimeError('Server does not support ranges; refusing whole download')
            self.size=int(r.headers['Content-Range'].split('/')[-1])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        return self.pos
    def read(self,n=-1):
        n=min(n if n>=0 else self.size-self.pos,self.size-self.pos)
        if n<=0:return b''
        if self.transferred+n>2_000_000_000:raise RuntimeError('2 GB transfer cap')
        sep='&' if '?' in self.url else '?'
        with requests.get(self.url+sep+f'range_start={self.pos}&range_n={n}',headers={'Range':f'bytes={self.pos}-{self.pos+n-1}'},stream=True,timeout=90) as r:
            if r.status_code!=206:raise RuntimeError(f'Range refused: {r.status_code}')
            assert r.headers['Content-Range'].startswith(f'bytes {self.pos}-'),r.headers['Content-Range']
            b=r.content
        assert len(b)==n
        self.transferred+=n;self.pos+=n;return b

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('--match',nargs='+',required=True);p.add_argument('--out');a=p.parse_args()
    f=RemoteFile(a.url)
    with zipfile.ZipFile(f) as z:
        entries=[i for i in z.infolist() if any(m in i.filename for m in a.match) and not i.is_dir()]
        print(json.dumps([{'name':i.filename,'compressed_bytes':i.compress_size,'bytes':i.file_size} for i in entries],indent=2),flush=True)
        total=sum(i.compress_size for i in entries);print('SELECTED_BYTES',total,flush=True)
        if a.out:
            assert total<2_000_000_000
            Path(a.out).mkdir(parents=True,exist_ok=True)
            for i in entries:
                b=z.read(i);dest=Path(a.out)/Path(i.filename).name
                assert not dest.exists(),dest
                dest.write_bytes(b);print(dest,len(b),hashlib.sha256(b).hexdigest(),flush=True)
    print('TRANSFERRED_BYTES',f.transferred,flush=True)
