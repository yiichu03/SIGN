"""Shared offline/online raster area and solid-path rendering. No model imports."""
import numpy as np


class GeometryError(ValueError):
    """A segment cannot be represented faithfully on its fixed initial floor."""


class EpisodeCoverage:
    """Incremental original 2.5cm/3m/90deg union; never cleared at rollout cuts."""
    def __init__(self, grid, mpp=.025, radius=3., fov=90., max_height_range=.5):
        from scipy.ndimage import distance_transform_edt
        self.grid = np.array(grid, copy=True)
        self.valid = self.grid == 1
        if not self.valid.any():
            raise GeometryError('empty_navigable_map')
        self.mpp, self.radius, self.fov = mpp, radius, fov
        self.max_height_range = max_height_range
        self.dist, self.nearest = distance_transform_edt(~self.valid, return_indices=True)
        self.seen = np.zeros_like(self.grid)
        self.prior = None
        self.coords, self.positions, self.headings = [], [], []
        self.segment_start = 0
        self.reason = None
        self.height_min = self.height_max = None
        ys, xs = np.where(self.valid)
        self.bounds = [int(xs.min()-8), int(xs.max()+8), int(ys.max()+100), int(ys.min()-8)]

    def observe(self, rc, heading, position):
        from habitat.utils.visualizations import fog_of_war
        rc = np.asarray(rc, dtype=np.int64)
        xyz = np.asarray(position, dtype=np.float64)
        self.coords.append(rc.copy())
        self.positions.append(xyz.copy())
        self.headings.append(float(heading))
        if self.reason:
            return
        if not np.isfinite(xyz).all() or not np.isfinite(heading):
            self.reason = 'nonfinite_pose'
            return
        height = float(xyz[1])
        self.height_min = height if self.height_min is None else min(self.height_min, height)
        self.height_max = height if self.height_max is None else max(self.height_max, height)
        if self.height_max-self.height_min >= self.max_height_range:
            self.reason = 'episode_height_range_exceeds_fixed_floor'
            return
        if not (0 <= rc[0] < self.grid.shape[0] and 0 <= rc[1] < self.grid.shape[1]):
            self.reason = 'pose_outside_map'
            return
        if self.dist[tuple(rc)] > 2.01:
            self.reason = 'fog_origin_farther_than_5cm_from_navmesh'
            return
        origin = np.asarray([self.nearest[0][tuple(rc)], self.nearest[1][tuple(rc)]], dtype=np.int64)
        self.seen = fog_of_war.reveal_fog_of_war(self.grid, self.seen, origin, float(heading),
                    fov=self.fov, max_line_len=self.radius/self.mpp)
        if self.prior is None:
            self.prior = self.seen.copy()  # The initial view never earns area.

    def snapshot(self):
        end = len(self.coords)-1
        if end <= self.segment_start:
            raise RuntimeError('Empty geometry segment')
        result = dict(valid_geometry=self.reason is None, geometry_reason=self.reason,
                      start=self.segment_start, end=end, action_count=end-self.segment_start)
        if self.reason is None:
            result.update(grid=self.grid.copy(), prior_seen=self.prior.copy(), final_seen=self.seen.copy(),
                          coords=np.asarray(self.coords).copy(), positions=np.asarray(self.positions).copy(),
                          headings=np.asarray(self.headings).copy(), mpp=self.mpp, bounds=list(self.bounds),
                          metadata=area_stats(self.prior, self.seen, self.valid, self.mpp, end-self.segment_start))
        return result

    def cut(self):
        self.segment_start = len(self.coords)-1
        if self.prior is not None:
            self.prior = self.seen.copy()


def area_stats(prior, final, valid, mpp, actions):
    if actions <= 0 or mpp <= 0 or prior.shape != final.shape or prior.shape != valid.shape:
        raise ValueError('Invalid raster or action count')
    prior, final, valid = prior.astype(bool), final.astype(bool), valid.astype(bool)
    if np.any(prior & valid & ~final):
        raise ValueError('Cumulative observation cannot shrink')
    old = int(np.count_nonzero(prior & valid))
    new = int(np.count_nonzero(final & ~prior & valid))
    total = int(np.count_nonzero(final & valid))
    assert old + new == total
    return dict(action_count=actions, new_area_m2=new*mpp*mpp,
                new_area_m2_per_action=new*mpp*mpp/actions,
                prior_seen_area_m2=old*mpp*mpp, total_covered_area_m2=total*mpp*mpp,
                new_valid_cells=new, prior_valid_cells=old, total_valid_cells=total)


def render(path, coords, grid, prior, final, start, end, bounds, title, variant, mpp):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    valid = grid == 1
    rgb = np.ones((*valid.shape, 3))
    rgb[valid] = [.83, .84, .85]
    rgb[prior.astype(bool) & valid] = [.61, .70, .78]
    rgb[final.astype(bool) & ~prior.astype(bool) & valid] = [.65, .84, .92]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(rgb, interpolation='nearest')
    if variant == 'history' and start:
        # Identical stroke style; draw the current path above exact historical overlaps.
        ax.plot(coords[:start+1, 1], coords[:start+1, 0],
                c='#f2bd27', lw=1.5, linestyle='-', zorder=3)
    current = coords[start:end+1]
    ax.plot(current[:, 1], current[:, 0], c='#b82b35', lw=1.5, linestyle='-', zorder=4)
    start_size = 110 if np.array_equal(current[0], current[-1]) else 50
    ax.scatter(current[0, 1], current[0, 0], s=start_size, c='#149253', edgecolors='white', zorder=5)
    ax.scatter(current[-1, 1], current[-1, 0], s=50, c='#222c41', marker='X', zorder=6)
    ax.set_xlim(bounds[:2]); ax.set_ylim(bounds[2:]); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(title, fontsize=12)
    xx, yy = bounds[0]+5, bounds[2]-5
    ax.plot([xx, xx+2/mpp], [yy, yy], c='black', lw=3)
    ax.text(xx+1/mpp, yy-3, '2 m', ha='center', fontsize=9)
    historical = variant != 'legacy'
    legend = [Patch(color=c, label=label) for c, label in [
        ('#d4d6d9', 'Navigable floor'),
        ('#9cb3c7', 'Pre-window coverage' if historical else 'Initial coverage'),
        ('#a6d6eb', 'New coverage')]]
    if historical:
        legend.append(Line2D([0], [0], color='#f2bd27', lw=1.5, linestyle='-',
                             label='History (yellow, when shown)'))
    legend += [Line2D([0], [0], color='#b82b35', label='Current path' if historical else 'Path'),
               Line2D([0], [0], marker='o', color='w', markerfacecolor='#149253', label='Start'),
               Line2D([0], [0], marker='X', color='w', markerfacecolor='#222c41', label='End')]
    # Fixed axes, bounds, pixels, and scale in all matched variants.
    fig.legend(handles=legend, loc='lower center', ncol=4 if historical else 3)
    fig.subplots_adjust(bottom=.12)
    fig.savefig(path, dpi=140)
    plt.close(fig)
