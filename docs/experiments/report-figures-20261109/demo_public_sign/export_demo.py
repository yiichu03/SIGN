"""CPU-only presentation export from an existing Public SIGN recording.

No Habitat, checkpoint loading, frame interpolation, inference or evaluation.
Use --source-dir pointing at this published folder to reproduce in a NEW --out.
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont


VIDEO_SHA = '7af7612fe26b3758264c2af08aa113af5a3bade20b0c1f3f4d831ab5e2a37e0b'
VIDEO_NAME = 'success_03_interior_0651_841463_ep0.mp4'
KEY_STEPS = (0, 16, 33, 50)
FPS, REPEATS, FINAL_HOLD = 30, 12, 120
CURRENT_BOX, GOAL_BOX = (0, 64, 384, 448), (384, 64, 768, 448)
BG, WHITE, MUTED, GREEN = '#101822', '#f5f7fa', '#a5b4c5', '#57d9aa'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def font(size):
    # Use the already-installed, versioned Matplotlib font; no system font fetch.
    import matplotlib
    return ImageFont.truetype(str(Path(matplotlib.get_data_path()) / 'fonts/ttf/DejaVuSans.ttf'), size)


def compose(current, goal, step):
    image = Image.new('RGB', (1280, 720), BG)
    image.paste(current.resize((640, 640), Image.Resampling.BILINEAR), (24, 64))
    image.paste(goal.resize((300, 300), Image.Resampling.BILINEAR), (940, 64))
    d = ImageDraw.Draw(image)
    d.text((24, 15), 'Public SIGN  |  CURRENT RGB', font=font(28), fill=WHITE)
    d.text((940, 29), 'GOAL IMAGE', font=font(22), fill=GREEN)
    d.text((710, 382), '2.5x simulation time', font=font(24), fill=MUTED)
    d.text((710, 425), 'Step %02d / 50' % step, font=font(40), fill=WHITE)
    d.line((710, 488, 1240, 488), fill='#334458', width=6)
    if step:
        d.line((710, 488, 710 + round(530 * step / 50), 488), fill=GREEN, width=6)
    if step == 50:
        d.text((710, 510), 'SUCCESS / STOP', font=font(30), fill=GREEN)
        d.text((710, 552), 'SPL 0.6143  |  final frame held 4 s', font=font(22), fill=WHITE)
    else:
        d.text((710, 516), 'Image-goal navigation', font=font(27), fill=WHITE)
    d.text((710, 592), 'Habitat-GS validation', font=font(23), fill=MUTED)
    d.text((710, 626), 'interior_0651_841463  |  episode 0', font=font(22), fill=MUTED)
    d.text((710, 672), 'Original 128 x 128 inputs, enlarged', font=font(20), fill=MUTED)
    return image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    src, out = args.source_dir.resolve(), args.out.resolve()
    assert not out.exists(), 'Choose a new output directory; existing evidence is not overwritten.'
    source_video = src / 'original_recording.mp4'
    manifest = json.loads((src / 'source_manifest.json').read_text())
    entry = next(x for x in manifest['videos'] if x['video'] == VIDEO_NAME)
    assert sha(source_video) == entry['video_sha256'] == VIDEO_SHA
    assert entry['steps'] == 50 and entry['final_metrics']['success'] == 1.0
    assert manifest['simulation_time_step_s'] == 1.0
    episode = json.loads((src / 'source_episode.json').read_text())
    assert episode['episode_id'] == entry['episode_id'] == '0'
    assert entry['scene'] in episode['scene_id']
    out.mkdir(parents=True)
    for name in ('original_recording.mp4', 'source_manifest.json', 'source_episode.json',
                 'source_provenance.json', 'original_record.py'):
        shutil.copyfile(src / name, out / name)
    shutil.copyfile(Path(__file__), out / 'export_demo.py')

    reader = imageio.get_reader(str(source_video), ffmpeg_params=['-threads', '1'])
    source_meta = reader.get_meta_data()
    frames = [Image.fromarray(frame) for frame in reader]
    reader.close()
    assert len(frames) == entry['video_frames'] == 71
    assert source_meta['size'] == (768, 544) and source_meta['fps'] == 10.0
    # The original renderer places unlabelled RGB at these exact rectangles.
    # Goal is fixed using decoded frame 0, avoiding codec variations across frames.
    goal = frames[0].crop(GOAL_BOX)
    goal.save(out / 'goal.png')
    currents = [frame.crop(CURRENT_BOX) for frame in frames[:51]]
    composed = [compose(current, goal, step) for step, current in enumerate(currents)]
    for step in KEY_STEPS:
        currents[step].save(out / ('rgb_step_%03d.png' % step))
        composed[step].save(out / ('keyframe_step_%03d.png' % step))
    preview = Image.new('RGB', (1280, 720), BG)
    for index, step in enumerate(KEY_STEPS):
        preview.paste(composed[step].resize((640, 360), Image.Resampling.LANCZOS),
                      ((index % 2) * 640, (index // 2) * 360))
    preview.save(out / 'keyframes_overview.png')

    video_path = out / 'public_sign_success_720p.mp4'
    writer = imageio_ffmpeg.write_frames(str(video_path), (1280, 720), fps=FPS,
        codec='libx264', pix_fmt_out='yuv420p', ffmpeg_log_level='error',
        output_params=['-crf', '18', '-preset', 'medium', '-threads', '1', '-movflags', '+faststart'])
    writer.send(None)
    frame_map = []
    try:
        output_index = 0
        for step, frame in enumerate(composed):
            repetitions = FINAL_HOLD if step == 50 else REPEATS
            frame_map.append(dict(step=step, source_frame=step, first_output_frame=output_index,
                output_frame_count=repetitions, start_s=output_index / FPS,
                end_s=(output_index + repetitions) / FPS, final_hold=step == 50))
            for _ in range(repetitions):
                writer.send(np.ascontiguousarray(frame))
            output_index += repetitions
    finally:
        writer.close()
    with (out / 'frame_mapping.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(frame_map[0])); w.writeheader(); w.writerows(frame_map)
    metrics = entry['final_metrics']
    metadata = dict(
        exported_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        policy='Public SIGN full released checkpoint; no Coverage reward training or recovery harness',
        dataset='Habitat-GS', split='val', scene=entry['scene'], scene_id=episode['scene_id'],
        episode_id=entry['episode_id'], checkpoint='ckpt/nav_model.pth',
        checkpoint_sha256=manifest['checkpoint_sha256']['ckpt/nav_model.pth'],
        safety_checkpoint='ckpt/safety_model.pth',
        safety_checkpoint_sha256=manifest['checkpoint_sha256']['ckpt/safety_model.pth'],
        recording_source_commit=manifest['source_commit'], original_job_id=manifest['job_id'],
        recording_created_at=manifest['created_at'], success=metrics['success'], steps=entry['steps'],
        spl=metrics['spl'], final_metrics=metrics,
        path_length_m=None,
        path_length_note='Actual travelled length was not saved by the original recorder; not reconstructed from SPL.',
        shortest_path_length_m=episode['info']['geodesic_distance'],
        shortest_path_source='Dataset episode.info.geodesic_distance (not actual travelled path).',
        stop=dict(step=50, confirmed_by='Success=1 with native Success requiring is_stop_called and distance < 1.0 m; task ended at step 50.',
                  raw_final_action=None, note='Action vectors were not stored in the original video manifest.'),
        seed=manifest['seed'], pythonhashseed=manifest['pythonhashseed'], deterministic_policy=True,
        max_episode_steps=manifest['max_episode_steps'],
        original_recording=dict(file='original_recording.mp4', sha256=VIDEO_SHA,
                                fps=10, frames=71, observation_frames=51, trailing_hold_frames=20),
        output_video=dict(file=video_path.name, sha256=sha(video_path), width=1280, height=720,
            codec='H.264', pixel_format='yuv420p', fps=FPS, frames=output_index, duration_s=output_index / FPS,
            action_playback_rate=2.5, simulation_time_step_s=1.0, simulation_speed_multiplier=2.5,
            final_stop_hold_s=4, interpolation=False, dropped_observation_frames=0, audio=False),
        images=dict(goal='goal.png', raw_rgb=['rgb_step_%03d.png' % s for s in KEY_STEPS],
            labelled_keyframes=['keyframe_step_%03d.png' % s for s in KEY_STEPS], steps=list(KEY_STEPS),
            origin='Cropped from the existing lossy H.264 presentation video, whose 128x128 inputs were enlarged to 384x384. Not original lossless sensor frames.',
            source_goal_raw_pixel_sha256=entry['goal_rgb_sha256'],
            exported_goal_file_sha256=sha(out / 'goal.png'),
            current_crop_xyxy=list(CURRENT_BOX), goal_crop_xyxy=list(GOAL_BOX),
            overlay_note='Original collision border, if present, is retained in the RGB crop.'),
        scope='Previously recorded deterministic illustration on Habitat-GS, not Gibson or an original full-evaluation recording; not a new aggregate evaluation.',
        source_provenance='source_provenance.json', frame_mapping='frame_mapping.csv')
    write_json(out / 'metadata.json', metadata)

    # Decode ALL output frames and check the crop/goal/hold rather than only headers.
    reader = imageio.get_reader(str(video_path), ffmpeg_params=['-threads', '1'])
    output_meta = reader.get_meta_data()
    count, key_errors, hold_errors = 0, [], []
    final_reference = np.asarray(composed[50], dtype=np.int16)
    for index, frame in enumerate(reader):
        assert frame.shape == (720, 1280, 3)
        count += 1
        step = min(index // REPEATS, 50)
        if index % REPEATS == 0 or index == output_index - 1:
            reference = np.asarray(composed[step], dtype=np.int16)
            key_errors.append(float(np.mean(np.abs(frame.astype(np.int16) - reference))))
        if index >= 600:
            hold_errors.append(float(np.mean(np.abs(frame.astype(np.int16) - final_reference))))
    reader.close()
    assert count == 720 and output_meta['codec'] == 'h264'
    assert output_meta['fps'] == FPS and output_meta['duration'] == 24.0
    assert len(hold_errors) == 120 and max(key_errors + hold_errors) < 5.0
    # At t=20s the final hold starts at the true step-50 observation, not an early goal frame.
    assert frame_map[-1]['start_s'] == 20.0
    assert np.array_equal(np.asarray(Image.open(out / 'rgb_step_050.png')), np.asarray(currents[50]))
    probe = Path(imageio_ffmpeg.get_ffmpeg_exe()).with_name('ffprobe')
    probe_data = json.loads(subprocess.check_output([str(probe), '-v', 'error', '-show_streams',
        '-show_format', '-of', 'json', str(video_path)], text=True))
    write_json(out / 'validation.json', dict(passed=True, all_output_frames_decoded=count,
        source_sha_matches_original_manifest=True, source_frames_decoded=len(frames),
        step_mapping_covers_all_51_observations=True, final_hold_frames_checked=len(hold_errors),
        max_frame_mean_absolute_codec_error=max(key_errors + hold_errors),
        exported_rgb_matches_source_crop=True, goal_fixed_from_source_frame=0,
        ffprobe=probe_data,
        files={str(x.relative_to(out)): dict(bytes=x.stat().st_size, sha256=sha(x))
               for x in sorted(out.iterdir()) if x.is_file() and x.name != 'validation.json'}))
    print(json.dumps(dict(output=str(out), frames=count, duration_s=24, success=1, spl=metrics['spl'],
                          bytes=video_path.stat().st_size, validation='passed')))


if __name__ == '__main__':
    main()
