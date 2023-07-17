import numpy as np
import hip_gait_state_estimators
import unittest
import matplotlib.pyplot as plt
from hip_exo import Exo
import filters
import hip_angle_spline
import time


class HipTestGaitEventDetectors(unittest.TestCase):

    def test_HipToeOffDetector(self):
        data = Exo.DataContainer()
        angle_signal = [0, 0, 0, 5, 3, 1, 2, 3, 0, 0, 0]
        toe_off_detector = hip_gait_state_estimators.HipToeOffDetector(
            maximum_angle=10, angle_filter=filters.Butterworth(N=2, Wn=0.4), delay=0)
        did_toe_offs = []
        for angle_val in angle_signal:
            data.hip_angle = angle_val
            did_toe_offs.append(
                toe_off_detector.detect(data))
        self.assertEqual(did_toe_offs, [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])

    def test_StrideAverageGaitPhaseEstimator(self):
        '''Simultaneously runs roughly simulated gyro through heel strike detector,
         toe off detector, gait phase estimator. Requires looking at the plot to
         confirm.'''
        data = Exo.DataContainer()
        sampling_freq = 100
        time_nows = 1/sampling_freq * np.arange(0, 1300)
        #time_nows = np.arange(1, 1001)
        # about 1 heel strike per second
        angle_values = hip_angle_spline.generate_hip_angle()
        hip_toe_off_detector = hip_gait_state_estimators.HipToeOffDetector(
            maximum_angle=10, angle_filter=filters.Butterworth(N=2, Wn=0.4))
        gait_phase_estimator = hip_gait_state_estimators.StrideAverageGaitPhaseEstimator(
            num_strides_required=2, min_allowable_stride_duration=0.4, max_allowable_stride_duration=1)
        hip_heel_strike_detector = hip_gait_state_estimators.GaitPhaseBasedHipHeelStrikeDetector(
            fraction_of_gait=0.4)
        gait_event_detector = hip_gait_state_estimators.GaitStateEstimator(
            data_container=data,
            heel_strike_detector=hip_heel_strike_detector,
            gait_phase_estimator=gait_phase_estimator,
            toe_off_detector=hip_toe_off_detector)
        did_heel_strikes = []
        gait_phases = []
        did_toe_offs = []
        for time_now, angle_value in zip(time_nows, angle_values):
            data.hip_angle = angle_value
            gait_event_detector.detect()
            did_toe_offs.append(data.did_toe_off)
            gait_phases.append(data.gait_phase)
            did_heel_strikes.append(data.did_heel_strike)
            time.sleep(0.005)
        #print('gait phases: ',gait_phases)
        plt.plot(did_toe_offs, label='toe off')
        plt.plot(did_heel_strikes, label="heel strike")
        plt.plot(gait_phases, label='gait phase', linestyle='--')
        plt.plot(angle_values, label='angle')
        plt.legend()
        plt.show()


if __name__ == '__main__':
    unittest.main()