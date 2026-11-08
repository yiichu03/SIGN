"""Bounded episode RGB memories. No simulator, task metrics or policy encoder."""
from collections import deque
import hashlib
import json
import random
import numpy as np


def rgb_sha(image):
    return hashlib.sha256(np.ascontiguousarray(image,dtype=np.uint8).tobytes()).hexdigest()


def physical_commands(commands):
    a=np.asarray(commands,dtype=np.float32)
    if a.ndim!=2 or a.shape[1]!=2 or not np.isfinite(a).all():
        raise ValueError('Expected actual canonical velocity commands')
    return np.stack([(a[:,0]+1)*.125,a[:,1]*15],axis=1)


def forward_observation(before,after,commands):
    physical=physical_commands(commands)
    aligned=bool(len(physical) and np.all(np.abs(physical[:,1])<=1.5)
        and np.all(physical[:,0]>=.10))
    change=float(np.abs(np.asarray(after,dtype=np.float32)-np.asarray(before,dtype=np.float32)).mean()/255)
    return dict(forward_only=aligned,visual_mae=change if aligned else None,
        summed_yaw_command_deg=float(physical[:,1].sum()),
        forward_command_sum_m=float(physical[:,0].sum()),
        note='Commanded motion and observed image change; no measured displacement or success label.')


class VisualMatcher:
    """Conservative appearance correspondence, explicitly not a place oracle."""
    def __init__(self):
        import cv2
        self.cv=cv2
        cv2.setNumThreads(1)
        self.orb=cv2.ORB_create(nfeatures=256,edgeThreshold=7,patchSize=15,fastThreshold=10)
        self.matcher=cv2.BFMatcher(cv2.NORM_HAMMING)

    def view(self,image):
        a=np.asarray(image)
        if a.ndim!=3 or a.shape[2]!=3 or min(a.shape[:2])<32 or not np.isfinite(a).all() or a.min()<0 or a.max()>255:
            raise ValueError('Memory expects finite full-view RGB')
        image=a.astype(np.uint8,copy=True)
        small=self.cv.resize(image,(160,160),interpolation=self.cv.INTER_AREA)
        gray=self.cv.cvtColor(small,self.cv.COLOR_RGB2GRAY)
        points,descriptors=self.orb.detectAndCompute(gray,None)
        xy=np.asarray([p.pt for p in points],dtype=np.float32).reshape(-1,2)
        return dict(image=image,small=small,gray=gray,points=xy,descriptors=descriptors,rgb_sha256=rgb_sha(image))

    def match(self,query,stored):
        fail=lambda reason:dict(valid=False,reason=reason,score=0.)
        if query['descriptors'] is None or stored['descriptors'] is None:
            return fail('insufficient_texture')
        pairs=self.matcher.knnMatch(query['descriptors'],stored['descriptors'],k=2)
        good=[a for pair in pairs if len(pair)==2 for a,b in [pair] if a.distance<.75*b.distance]
        if len(good)<12:return fail('too_few_descriptor_matches')
        src=query['points'][[m.queryIdx for m in good]]
        dst=stored['points'][[m.trainIdx for m in good]]
        # OpenCV-only seed; does not touch NumPy/Torch policy random streams.
        self.cv.setRNGSeed(100)
        homography,inlier=self.cv.findHomography(src,dst,self.cv.RANSAC,3.0,maxIters=1000,confidence=.995)
        if homography is None or inlier is None or not np.isfinite(homography).all():return fail('invalid_homography')
        keep=inlier[:,0].astype(bool);count=int(keep.sum());ratio=count/len(good)
        if count<10 or ratio<.6:return fail('weak_geometric_consensus')
        # Avoid accepting a small repeated logo or isolated object as full-view evidence.
        def area(points):
            return float(self.cv.contourArea(self.cv.convexHull(points.astype(np.float32)))/(160*160))
        spread=min(area(src[keep]),area(dst[keep]))
        if spread<.15:return fail('localized_feature_cluster')
        warped=self.cv.warpPerspective(query['small'],homography,(160,160))
        mask=self.cv.warpPerspective(np.ones((160,160),np.uint8),homography,(160,160),flags=self.cv.INTER_NEAREST)>0
        overlap=float(mask.mean())
        if overlap<.5:return fail('insufficient_image_overlap')
        error=float(np.abs(warped.astype(np.float32)-stored['small'].astype(np.float32))[mask].mean()/255)
        if error>.12:return fail('photometric_mismatch')
        return dict(valid=True,reason='appearance_correspondence_only',score=float(ratio*min(1,count/30)*(1-error)),
            matches=len(good),inliers=count,inlier_ratio=ratio,spatial_coverage=spread,overlap=overlap,photometric_mae=error)


class EpisodeMemory:
    def __init__(self,cfg,kind,episode,emit=None):
        if kind not in ('outcome','visual'):raise ValueError('Unknown episode memory')
        self.kind=kind;self.capacity=int(getattr(cfg,'memory_capacity',24))
        self.stride=int(getattr(cfg,'memory_stride',8));self.age=int(getattr(cfg,'memory_min_age',16))
        if self.capacity<1 or self.stride<1 or self.age<0:raise ValueError('Invalid memory settings')
        self.matcher=VisualMatcher();self.entries=[];self.transitions=deque(maxlen=4)
        self.emit=emit or (lambda row:None);self.serial=0;self.forward_run=0
        seed=int(hashlib.sha256(('100:'+json.dumps(list(episode))).encode()).hexdigest()[:16],16)
        self.random=random.Random(seed)
        self.stats=dict(writes=0,updates=0,evictions=0,retrievals=0,verified_hits=0)

    def _record(self,operation,**fields):
        self.emit(dict(operation=operation,memory_kind=self.kind,**fields))

    def _insert(self,entry):
        self.serial+=1;entry.update(id=self.kind+'_'+str(self.serial),observations=1,uses=0)
        self.entries.append(entry);self.stats['writes']+=1
        self._record('write',entry_id=entry['id'],start_step=entry['start_step'],end_step=entry['end_step'],
            before_rgb_sha256=entry['before']['rgb_sha256'],after_rgb_sha256=entry.get('after',entry['before'])['rgb_sha256'],
            commands=entry.get('commands'),visual_observation=entry.get('observation'))
        if len(self.entries)>self.capacity:
            removed=self.entries.pop(0);self.stats['evictions']+=1;self._record('evict',entry_id=removed['id'])

    def observe(self,before,command,after,end_step,action_kind):
        if self.kind=='visual':
            if action_kind!='sign':return
            last=self.entries[-1] if self.entries else None
            if last and end_step-last['end_step']<self.stride:return
            view=self.matcher.view(after)
            if last:
                novelty=float(np.abs(view['small'].astype(float)-last['before']['small'].astype(float)).mean()/255)
                if novelty<.015:
                    last['observations']+=1;last['last_seen_step']=end_step;self.stats['updates']+=1
                    self._record('update',entry_id=last['id'],step=end_step,reason='near_duplicate_observation')
                    return
                if novelty<.08 and end_step-last['end_step']<32:return
            self._insert(dict(start_step=end_step,end_step=end_step,last_seen_step=end_step,before=view))
            return
        self.transitions.append(dict(before=np.asarray(before,dtype=np.uint8).copy(),after=np.asarray(after,dtype=np.uint8).copy(),
            command=np.asarray(command,dtype=np.float32).copy(),end_step=end_step,kind=action_kind))
        v,w=physical_commands([command])[0]
        self.forward_run=self.forward_run+1 if action_kind in ('recovery','probe','tail') and v>=.10 and abs(w)<=1.5 else 0
        if len(self.transitions)<4:return
        if end_step%self.stride and not (self.forward_run and self.forward_run%4==0):return
        chunk=list(self.transitions)
        if any(x['kind']=='scan' for x in chunk):return
        assert [x['end_step'] for x in chunk]==list(range(end_step-3,end_step+1))
        commands=[x['command'].tolist() for x in chunk]
        view=self.matcher.view(chunk[0]['before']);after_view=self.matcher.view(after)
        observation=forward_observation(chunk[0]['before'],after,commands)
        for entry in reversed(self.entries[-8:]):
            if np.allclose(entry['commands'],commands,rtol=0,atol=.03) and self.matcher.match(view,entry['before'])['valid']:
                entry.update(before=view,after=after_view,commands=commands,observation=observation,end_step=end_step,start_step=end_step-4)
                entry['observations']+=1;self.stats['updates']+=1
                self.entries=[x for x in self.entries if x is not entry]+[entry]
                self._record('update',entry_id=entry['id'],step=end_step,reason='similar_view_same_executed_actions',
                    before_rgb_sha256=view['rgb_sha256'],after_rgb_sha256=after_view['rgb_sha256'],
                    commands=commands,observations=entry['observations'],visual_observation=observation)
                return
        self._insert(dict(start_step=end_step-4,end_step=end_step,before=view,after=after_view,
            commands=commands,observation=observation))

    def retrieve(self,candidates,trigger_step,mode='verified'):
        if mode not in ('verified','recent','random'):raise ValueError('Invalid retrieval mode')
        eligible=[x for x in self.entries if x['end_step']<=trigger_step-self.age]
        selected=[]
        if mode in ('recent','random'):
            chosen=eligible[-2:] if mode=='recent' else self.random.sample(eligible,min(2,len(eligible)))
            selected=[dict(entry=e,matched_candidate=None,match=dict(valid=False,reason='unverified_'+mode+'_ablation',score=0.)) for e in chosen]
        else:
            for side,image in candidates.items():
                view=self.matcher.view(image);best=None
                for entry in eligible:
                    match=self.matcher.match(view,entry['before'])
                    if match['valid'] and (best is None or match['score']>best['match']['score']):
                        best=dict(entry=entry,matched_candidate=side,match=match)
                if best is not None and not any(x['entry']['id']==best['entry']['id'] for x in selected):selected.append(best)
        self.stats['retrievals']+=1;self.stats['verified_hits']+=sum(x['match']['valid'] for x in selected)
        for item in selected:item['entry']['uses']+=1
        self._record('retrieve',trigger_step=trigger_step,mode=mode,eligible_entries=len(eligible),
            selected=[dict(entry_id=x['entry']['id'],matched_candidate=x['matched_candidate'],match=x['match']) for x in selected])
        return selected[:2]

    def clear(self,reason):
        self._record('clear',reason=reason,entries=len(self.entries))
        self.entries.clear();self.transitions.clear();self.forward_run=0


def rule_memory_keep(choice,retrieved,threshold=.01):
    """Explicit ablation: low observed change after matching forward commands."""
    side={'A':'LEFT','B':'RIGHT'}.get(choice)
    for item in retrieved:
        entry=item['entry'];obs=entry.get('observation',{})
        if (item['match']['valid'] and item['matched_candidate']==side and obs.get('forward_only')
                and obs['visual_mae']<threshold):
            return 'C',dict(changed=True,entry_id=entry['id'],reason='matched_forward_experience_low_visual_change')
    return choice,dict(changed=False,reason='no_matching_low_change_forward_experience')
