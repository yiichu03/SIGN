"""Boundary cases which must not be misreported as semantic failure causes."""
import json
from pathlib import Path
import unittest
import numpy as np
from analyze import classify, observed_stage, validate_trace, projection_audit

HERE = Path(__file__).resolve().parent
FIELDS = ['distance_to_goal','distance_to_view','view_angle','success','view_match',
          'collisions','collision_step','coverage_delta_m2','coverage_new_area_m2',
          'stop_called','step_limit_reached','environment_episode_over']


def example(positions, yaw, lin=.1):
    n = len(positions)
    metrics = np.zeros((n, len(FIELDS)))
    metrics[:, 0] = 10.
    metrics[:, 5] = np.arange(n)
    metrics[1:, 6] = 1
    q = np.zeros((n, 4));q[:, 1] = np.sin(yaw/2);q[:, 3] = np.cos(yaw/2)
    cmd = np.zeros((n, 2));cmd[1:, 0] = lin
    trace = dict(position_xyz=positions, rotation_xyzw=q, command_mps_degps=cmd,
                 metrics=metrics, metric_fields=np.asarray(FIELDS))
    row = dict(steps=n-1, success=0, stop_called=False, step_limit_reached=True,
               goal_views_xyzw=[[0,0,0,1]], goal_position=[10,0,0])
    return trace, row


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads((HERE/'analysis_rules.json').read_text())

    def test_blocked_motion_is_not_a_search_loop(self):
        trace, row = example(np.zeros((65,3)), np.zeros(65))
        result = classify(trace, row, self.rules)
        self.assertTrue(result['strong_blocked_tail_candidate'])
        self.assertFalse(result['low_gain_closed_loop_candidate'])

    def test_pure_rotation_is_not_blocked_forward_or_search_loop(self):
        trace, row = example(np.zeros((65,3)), np.linspace(0,4*np.pi,65), lin=0.)
        result = classify(trace, row, self.rules)
        self.assertFalse(result['strong_blocked_tail_candidate'])
        self.assertFalse(result['low_gain_closed_loop_candidate'])
        self.assertTrue(result['stationary_turn_tail_candidate'])

    def test_moving_closed_loop_is_only_a_candidate(self):
        yaw = np.linspace(0,4*np.pi,97)
        positions = np.c_[np.cos(yaw),np.zeros(97),np.sin(yaw)]
        trace, row = example(positions, yaw)
        result = classify(trace, row, self.rules)
        self.assertTrue(result['low_gain_closed_loop_candidate'])
        self.assertNotIn('human_primary_cause', result)

    def test_different_floors_do_not_make_a_closed_loop(self):
        yaw = np.linspace(0,4*np.pi,97)
        positions = np.c_[np.cos(yaw),np.arange(97)*.05,np.sin(yaw)]
        trace, row = example(positions, yaw)
        self.assertFalse(classify(trace, row, self.rules)['low_gain_closed_loop_candidate'])

    def test_near_goal_then_leaving_without_stop(self):
        row = dict(success=0,stop_called=False,step_limit_reached=True)
        self.assertEqual(observed_stage(row,np.array([3.,.5,2.]),1.),'time_limit_after_leaving_goal_region')

    def test_stop_on_limit_has_stop_precedence_and_near_boundary_is_strict(self):
        row = dict(success=0,stop_called=True,step_limit_reached=True)
        self.assertEqual(observed_stage(row,np.array([3.,1.]),1.),'stop_without_ever_entering_goal_region')
        self.assertEqual(observed_stage(row,np.array([3.,.5,2.]),1.),'stop_after_leaving_goal_region')

    def test_at_goal_timeout_and_invalid_distance_are_separate(self):
        row = dict(success=0,stop_called=False,step_limit_reached=True)
        self.assertEqual(observed_stage(row,np.array([3.,.5]),1.),'time_limit_in_goal_region_without_stop')
        self.assertEqual(observed_stage(row,np.array([3.,np.inf]),1.),'other_or_invalid')

    def telemetry(self):
        trace,row=example(np.zeros((65,3)),np.zeros(65))
        trace['action_normalized_linear_angular']=np.zeros((65,2))
        trace['action_normalized_linear_angular'][1:,0]=-.2
        trace['metrics'][-1,10:]=1
        row.update(case='test',episode_id='1')
        return trace,row

    def test_physical_velocity_audit_rejects_swapped_gym_action_order(self):
        trace,row=self.telemetry()
        validate_trace(trace,row)
        trace['action_normalized_linear_angular'][1:]=trace['action_normalized_linear_angular'][1:,::-1]
        with self.assertRaises(AssertionError):validate_trace(trace,row)

    def test_telemetry_audit_rejects_wrong_stop_and_episode_boundary(self):
        trace,row=self.telemetry()
        trace['metrics'][-1,9]=1
        with self.assertRaises(AssertionError):validate_trace(trace,row)
        trace,row=self.telemetry()
        trace['metrics'][10,11]=1
        with self.assertRaises(AssertionError):validate_trace(trace,row)

    def test_coverage_cannot_reset_inside_a_trace(self):
        trace,row=self.telemetry()
        trace['metrics'][1:,8]=1
        trace['metrics'][1,7]=1
        validate_trace(trace,row)
        trace['metrics'][32:,8]=0
        with self.assertRaises(AssertionError):validate_trace(trace,row)

    def projection_example(self):
        grid=np.ones((2,2),dtype=np.uint8);grid[0,0]=0
        return dict(position_xyz=np.array([[.4,0,.4],[.6,0,.6]],dtype=np.float32),
                    initial_grid=grid,final_grid=grid.copy(),meters_per_pixel=np.asarray(.1),
                    map_bounds_xyz=np.array([[0,0,0],[2,2,2]],dtype=float))

    def test_raster_caveat_does_not_label_navigation_invalid(self):
        result=projection_audit(self.projection_example())
        self.assertEqual(result['coverage_projected_nonvalid_fraction'],1.)
        self.assertNotIn('navigation_invalid',result)

    def test_missing_intermediate_height_maps_are_unknown(self):
        trace=self.projection_example();trace['position_xyz'][1,1]=.2
        result=projection_audit(trace)
        self.assertEqual(result['coverage_projection_audit'],'intermediate_height_maps_unknown')
        self.assertIsNone(result['coverage_projected_nonvalid_fraction'])

    def test_stop_boundary_uses_native_float32_scaling(self):
        trace,row=self.telemetry()
        trace['action_normalized_linear_angular']=trace['action_normalized_linear_angular'].astype(np.float32)
        trace['action_normalized_linear_angular'][-1]=[-.92,.099999994]
        action=trace['action_normalized_linear_angular'][-1].astype(float)
        trace['command_mps_degps'][-1]=[(action[0]+1)*.125,action[1]*15]
        # FP64 nominal angle is below1.5, but native float32 arithmetic is
        # exactly1.5 and therefore does not trigger STOP.
        self.assertLess(trace['command_mps_degps'][-1,1],1.5)
        validate_trace(trace,row)


if __name__ == '__main__':
    unittest.main()
