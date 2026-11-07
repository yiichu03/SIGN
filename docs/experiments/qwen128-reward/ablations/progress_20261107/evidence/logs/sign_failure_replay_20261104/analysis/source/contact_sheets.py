"""Dense, timestamped video review without changing or resampling navigation."""
import argparse
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('case',choices=['baseline','coverage256','coverage32'])
    parser.add_argument('scene')
    parser.add_argument('episode')
    args=parser.parse_args()
    folder=HERE/'full'/args.case/'diagnostic'
    rows=[json.loads(line) for file in (folder/'diagnostics').glob('*.jsonl')
          for line in file.read_text().splitlines()]
    row=next(r for r in rows if Path(r['scene_id']).stem==args.scene and r['episode_id']==args.episode)
    with np.load(folder/row['trace'],allow_pickle=False) as trace:
        distance=trace['metrics'][:,trace['metric_fields'].tolist().index('distance_to_goal')]
    indices=set(range(0,row['steps']+1,8))|{row['steps']}
    near=np.flatnonzero(distance<1)
    if len(near):
        for event in [near[0],near[-1],int(distance.argmin())]:
            indices.update(range(max(0,int(event)-5),min(row['steps'],int(event)+5)+1))
    indices=sorted(indices)
    reader=imageio.get_reader(str(folder/row['video']))
    decoded={}
    count=0
    try:
        for i,frame in enumerate(reader):
            count+=1
            if i in indices:decoded[i]=Image.fromarray(frame[:128,128:256])
    finally:reader.close()
    assert count==row['steps']+1 and set(decoded)==set(indices)
    stem=args.case+'_'+args.scene+'_'+args.episode
    out=HERE/'inspection_previews';out.mkdir(exist_ok=True)
    sheets=[]
    for part,start in enumerate(range(0,len(indices),64)):
        chosen=indices[start:start+64]
        sheet=Image.new('RGB',(1024,36+148*((len(chosen)+7)//8)),'white')
        draw=ImageDraw.Draw(sheet)
        draw.text((8,8),stem+' | every8 actions + dense near-goal events | part'+str(part),fill='black')
        for j,index in enumerate(chosen):
            x=(j%8)*128;y=36+(j//8)*148
            sheet.paste(decoded[index],(x,y))
            draw.text((x+2,y+129),'t=%d d=%.2f'%(index,distance[index]),fill='black')
        name=stem+'_contact_'+str(part)+'.png';sheet.save(out/name);sheets.append(name)
    (out/(stem+'_contact.json')).write_text(json.dumps(dict(case=args.case,scene_id=row['scene_id'],
        episode_id=args.episode,source_video=row['video'],decoded_frames=count,
        sampled_frame_indices=indices,sheets=sheets,
        qualification='AI dense-frame review, not frame-by-frame human ground truth'),indent=2)+'\n')
    print(stem,'decoded',count,'view frames',len(indices),'sheets',sheets)


if __name__=='__main__':main()
