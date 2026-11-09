"""Encode all actual RGB observations; repeat frames, never interpolate time."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
import imageio_ffmpeg

BLUE='#003D7C';ORANGE='#EF7C00';GRAY='#536171'
HERE=Path(__file__).resolve().parent
FONT=Path(matplotlib.get_data_path())/'fonts/ttf/DejaVuSans.ttf'
BOLD=FONT.with_name('DejaVuSans-Bold.ttf')
def font(n,bold=False):return ImageFont.truetype(str(BOLD if bold else FONT),n)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=HERE);a=p.parse_args();out=a.source
    summary=json.loads((out/'summary.json').read_text());data=np.load(out/'rgb_all_steps.npz')
    frames=data['rgb'];steps=summary['steps'];assert len(frames)==steps+1
    assert np.array_equal(data['step'],np.arange(steps+1))
    assert np.array_equal(frames[-1],np.asarray(Image.open(out/'terminal.png')))
    fps=30;navigation_frames=975;hold_frames=90;speed=steps/(navigation_frames/fps)
    goal=Image.open(out/'goal.png').resize((320,320),Image.Resampling.BILINEAR)
    with (out/'steps.csv').open() as f:rows=list(csv.DictReader(f))
    assert rows[-1]['episode_over']=='True'
    if summary['success']:assert rows[-1]['stop_called']=='True'
    def render(step):
        canvas=Image.new('RGB',(1280,720),'white');d=ImageDraw.Draw(canvas)
        d.rectangle((0,0,1280,7),fill=BLUE)
        d.text((40,23),'Public SIGN  |  Gibson ImageNav',font=font(29,True),fill=BLUE)
        d.text((40,64),'Cantwell / episode 1703  ·  Recovery off',font=font(18),fill=GRAY)
        d.text((40,98),'CURRENT VIEW',font=font(16,True),fill=BLUE)
        canvas.paste(Image.fromarray(frames[step]).resize((544,544),Image.Resampling.BILINEAR),(40,124))
        d.rectangle((39,123,584,668),outline=BLUE,width=2)
        d.text((774,98),'GOAL IMAGE  ·  FIXED',font=font(16,True),fill=BLUE)
        canvas.paste(goal,(774,124));d.rectangle((773,123,1094,444),outline=ORANGE,width=2)
        d.text((684,475),f'Step {step:03d} / {steps}',font=font(34,True),fill=BLUE)
        terminal=step==steps
        status=('SUCCESS · STOP' if summary['success'] else 'EPISODE ENDED') if terminal else 'Navigating toward the goal'
        d.text((684,528),status,font=font(25,terminal),fill=ORANGE if terminal else GRAY)
        if terminal:
            d.text((684,568),f"Success {int(summary['success'])}  ·  SPL {summary['spl']:.3f}",font=font(22),fill=BLUE)
        d.text((684,614),f'Playback: {speed:.2f}× simulation time',font=font(20,True),fill=BLUE)
        d.text((684,647),'Final observation held for 3 seconds',font=font(17),fill=GRAY)
        d.text((40,689),'Recorded policy RGB and goal: 128 × 128, enlarged for display. Every step is shown; no temporal interpolation.',font=font(15),fill=GRAY)
        return np.asarray(canvas)
    video=out/'public_sign_cantwell1703_720p.mp4'
    writer=imageio_ffmpeg.write_frames(str(video),(1280,720),fps=fps,codec='libx264',pix_fmt_out='yuv420p',
           ffmpeg_log_level='error',output_params=['-crf','20','-preset','medium','-threads','4','-movflags','+faststart'])
    writer.send(None);mapping=[]
    try:
        for step in range(steps+1):
            start=(step*navigation_frames)//steps
            end=((step+1)*navigation_frames)//steps if step<steps else navigation_frames+hold_frames
            assert end>start
            frame=render(step)
            for _ in range(end-start):writer.send(frame)
            mapping.append({'step':step,'video_frame_start':start,'video_frame_end_exclusive':end,
                            'start_seconds':start/fps,'end_seconds':end/fps,'terminal_hold':step==steps})
            if step in [0,steps//2,steps]:Image.fromarray(frame).save(out/f'preview_{step:03d}.png')
    finally:writer.close()
    with (out/'video_frame_mapping.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(mapping[0]),lineterminator='\n');w.writeheader();w.writerows(mapping)
    # Decode the complete file, rather than checking only its container headers.
    result=subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(video),'-f','null','-'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames',
             '-show_entries','stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_read_frames:format=duration,size',
             '-of','json',str(video)],text=True))
    stream=probe['streams'][0]
    assert (stream['codec_name'],stream['width'],stream['height'],stream['pix_fmt'])==('h264',1280,720,'yuv420p')
    assert int(stream['nb_read_frames'])==navigation_frames+hold_frames
    summary['video']={'file':video.name,'fps':fps,'frames':navigation_frames+hold_frames,
          'duration_seconds':(navigation_frames+hold_frames)/fps,'navigation_seconds':navigation_frames/fps,
          'playback_speed_x':speed,'terminal_hold_seconds':hold_frames/fps,
          'all_observations_shown':True,'temporal_interpolation':False,
          'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'bytes':video.stat().st_size}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'video_validation.json').write_text(json.dumps({'passed':True,'complete_decode_exit_code':result.returncode,
             'complete_decode_stderr':result.stderr,'ffprobe':probe,'source_rgb_frames':len(frames),
             'terminal_rgb_equals_archive':True,'terminal_captured_before_reset':summary['terminal_captured_before_reset']},indent=2)+'\n')
    print(json.dumps(summary['video'],indent=2))

if __name__=='__main__':main()
