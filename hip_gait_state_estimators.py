import numpy as np
import filters
import hip_exo
from scipy import signal
from collections import deque
import time
import constants
from typing import Type
import util
import config_util
import ml_util


class GaitStateEstimator():
    def __init__(self,
                 data_container: Type[hip_exo.Exo.DataContainer],
                 heel_strike_detector,
                 gait_phase_estimator,
                 toe_off_detector,
                 do_print_toe_offs: bool = False,
                 side: Type[constants.Side] = constants.Side.NONE):
        '''Looks at the exo data, applies logic to detect HS, gait phase, and TO, and adds to exo.data'''
        self.side = side
        self.data_container = data_container
        self.toe_off_detector = toe_off_detector
        self.gait_phase_estimator = gait_phase_estimator
        self.heel_strike_detector = heel_strike_detector
        self.do_print_toe_offs = do_print_toe_offs

    def detect(self):
        data = self.data_container  # For convenience
        data.did_toe_off = self.toe_off_detector.detect(data)
        data.did_heel_strike = self.heel_strike_detector.detect(data)
        data.gait_phase = self.gait_phase_estimator.estimate(data)
        if self.do_print_toe_offs and data.did_toe_off:
            print('Toe off detected on side: %-*s  at time: %s' %
                  (10, self.side, data.loop_time))

    def update_params_from_config(self, config: Type[config_util.ConfigurableConstants]):
        pass


class HipToeOffDetector():
    def __init__(self, maximum_angle: float, angle_filter: Type[filters.Filter], delay=0):
        self.maximum_angle = maximum_angle
        self.angle_filter = angle_filter
        self.angle_history = deque([0, 0, 0], maxlen=3)
        self.delay = delay
        # self.timer_active = False
        self.timer = util.DelayTimer(delay_time=self.delay)

    def detect(self, data: Type[hip_exo.Exo.DataContainer]):
        self.angle_history.appendleft(-1*self.angle_filter.filter(data.hip_angle))
        #print(self.angle_history)
        if (self.angle_history[1] < self.maximum_angle and
            self.angle_history[1] < self.angle_history[0] and
                self.angle_history[1] < self.angle_history[2]):
            self.timer.start()
            print('Toe off: ',self.angle_history)
        if self.timer.check():
            self.timer.reset()
            return True
        else:
            return False

class GaitPhaseBasedHipHeelStrikeDetector():
    def __init__(self, fraction_of_gait):
        '''Uses gait phase estimated from toe-off to estimate heel strikes.'''
        self.fraction_of_gait = fraction_of_gait
        self.has_heel_strike_occurred = False

    def detect(self, data: Type[hip_exo.Exo.DataContainer]):
        gait_phase = data.gait_phase
        if gait_phase is None:
            did_heel_strike = False
        else:
            if gait_phase < self.fraction_of_gait:
                self.has_heel_strike_occurred = False
            if gait_phase > (1- self.fraction_of_gait) and self.has_heel_strike_occurred is False:
                did_heel_strike = True
                self.has_heel_strike_occurred = True
            else:
                did_heel_strike = False
        return did_heel_strike


class StrideAverageGaitPhaseEstimator():
    '''Calculates gait phase based on average of recent stride durations.'''

    def __init__(self,
                 num_strides_required: int = 2,
                 num_strides_to_average: int = 2,
                 min_allowable_stride_duration: float = 0.0006,
                 max_allowable_stride_duration: float = 2,  
                 mean_stride_duration: float = 1):
        ''' Returns gait phase, which is either None or in [0, 1]
        Arguments:
        num_strides_required: int, number of acceptable strides in a row before gait is deemed steady
        num_strides_to_average: int, number of strides to average
        min_allowable_stride_duration: minimum allowable duration of a stride
        max_allowable_stride_duration: maximum allowable duration of a stride
        Returns: gait_phase, which is either None or in [0, 1].'''
        if num_strides_required < 1:
            raise ValueError('num_strides_required must be >= 1')
        if num_strides_to_average > num_strides_required:
            raise ValueError(
                'num_strides_to_average must be >= num_strides_required')
        self.num_strides_required = num_strides_required
        self.min_allowable_stride_duration = min_allowable_stride_duration
        self.max_allowable_stride_duration = max_allowable_stride_duration
        self.time_of_last_toe_off = 0  # something a long time ago
        self.last_stride_durations = deque(
            [1000] * self.num_strides_required, maxlen=self.num_strides_required)
        self.mean_stride_duration = mean_stride_duration 
        self.stride_duration_filter = filters.MovingAverage(
            window_size=num_strides_to_average)

    def estimate(self, data: Type[hip_exo.Exo.DataContainer]):
        time_now = time.perf_counter()
        if data.did_toe_off:
            stride_duration = time_now - self.time_of_last_toe_off
            self.last_stride_durations.append(stride_duration)
            self.time_of_last_toe_off = time_now
            self.mean_stride_duration = self.stride_duration_filter.filter(
                stride_duration)
            print('stride duration', stride_duration)

        time_since_last_toe_off = time_now - self.time_of_last_toe_off
        if all(self.min_allowable_stride_duration < last_stride_duration
                < self.max_allowable_stride_duration for last_stride_duration
                in self.last_stride_durations) and (time_since_last_toe_off
                                                    < 1.2 * self.max_allowable_stride_duration):
            gait_phase = min(1, time_since_last_toe_off /
                             self.mean_stride_duration)
        else:
            gait_phase = None
        return gait_phase

class MLGaitStateEstimator():
    def __init__(self,
                 side: Type[constants.Side],
                 data_container: Type[hip_exo.Exo.DataContainer],
                 jetson_interface: Type[ml_util.JetsonInterface],
                 do_print_heel_strikes=True,
                 stance_is_float=True,
                 do_filter_gait_phase=False):
        '''Looks at the exo data, applies logic to detect HS, gait phase, and TO, and adds to exo.data'''
        self.side = side
        self.data = data_container
        self.is_stance_threshold = 0.5
        self.do_print_heel_strikes = do_print_heel_strikes
        self.stance_is_float = stance_is_float
        self.last_is_stance = False
        self.stride_average_gait_state_estimator = StrideAverageGaitPhaseEstimator()
        self.jetson_object = jetson_interface
        print(
            'REMEMBER TO PRESS a TO MAKE CONTROLLER ACTIVE (INACTIVE TO START BY DEFAULT)')

        if do_filter_gait_phase:
            # Hardcoded 8 Hz first order filter
            self.gait_phase_filter = filters.Butterworth(N=1, Wn=0.08)
        else:
            self.gait_phase_filter = filters.PassThroughFilter()

        # SETUP FAKE TBE FOR STANCE/SWING
        self.fake_data = hip_exo.Exo.DataContainer(
            do_include_gen_vars=False, do_include_sync=False)
        default_config = config_util.ConfigurableConstants()
        toe_off_detector = HipToeOffDetector(
            maximum_angle=default_config.MAXIMUM_ANGLE,
            angle_filter=filters.Butterworth(N=default_config.HS_ANGLE_FILTER_N,
                                            Wn=default_config.HS_ANGLE_FILTER_WN,
                                            fs=default_config.TARGET_FREQ),
            delay=default_config.HS_ANGLE_DELAY)
        gait_phase_estimator = StrideAverageGaitPhaseEstimator(
            num_strides_required=default_config.NUM_STRIDES_REQUIRED)
        heel_strike_detector = GaitPhaseBasedHipHeelStrikeDetector(
            fraction_of_gait=default_config.TOE_OFF_FRACTION)
        self.parallel_tbe = GaitStateEstimator(
            data_container=self.fake_data, heel_strike_detector=heel_strike_detector,
            gait_phase_estimator=gait_phase_estimator, toe_off_detector=toe_off_detector)

    def detect(self):
        self.jetson_object.package_and_send_message(
            side=self.side, data_container=self.data)
        self.jetson_object.grab_message_and_parse()
        my_gait_phase_info = self.jetson_object.get_most_recent_gait_phase(
            side=self.side)
        if my_gait_phase_info is not None:
            gait_phase, is_stance = my_gait_phase_info
        else:
            return
        gait_phase = self.gait_phase_filter.filter(gait_phase)
        if gait_phase < 0:
            gait_phase = 0
        elif gait_phase > 1:
            gait_phase = 1
        self.data.did_heel_strike = False
        self.data.did_toe_off = False

        # If Jetson sends stance not as a bool but float:
        if self.stance_is_float:
            self.data.gen_var2 = is_stance
            is_stance = True if is_stance > self.is_stance_threshold else False

        # Add heel strikes and toe-offs from is_stance
        if is_stance and not self.last_is_stance:
            self.data.did_heel_strike = True
        if not is_stance and self.last_is_stance:
            self.data.did_toe_off = True
        self.last_is_stance = is_stance

        # use stride average gait phase estimator to determine if steady state and mask
        self.fake_data.gyro_z = self.data.gyro_z
        self.parallel_tbe.detect()
        if self.fake_data.gait_phase is not None:
            self.fake_data.gait_phase = self.fake_data.gait_phase*1/0.6
            if self.fake_data.gait_phase > 1:
                self.fake_data.gait_phase = 0
        self.data.gen_var3 = self.fake_data.gait_phase
        # if self.fake_data.gait_phase is not None:
        #     self.data.gait_phase = gait_phase
        # else:
        #     self.data.gait_phase = None
        self.data.gait_phase = gait_phase

        if self.do_print_heel_strikes and self.data.did_heel_strike:
            print('heel strike detected on side: ', self.side)

    def update_params_from_config(self, config: Type[config_util.ConfigurableConstants]):
        pass
