import constants
from hip_exo import Exo
from scipy import signal, interpolate
import time
import copy
import filters
import config_util
import util
from collections import deque
from typing import Type


class Controller(object):
    '''Parent controller object. Child classes inherit methods.'''

    def __init__(self, exo: Exo):
        self.exo = exo

    def command(self, reset):
        '''For modularity, new controllers will ideally not take any arguments with
        their command() function. The exo object stored on self will have updated
        data, which is accessible to controller objects.'''
        raise ValueError('command() not defined in child class of Controller')

    def update_controller_gains(self, Kp: int, Ki: int, Kd: int = 0, ff: int = 0):
        '''Updated internal controller gains. Note: None (default) means no change will be commanded.'''
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.ff = ff

    def command_gains(self):
        self.exo.update_gains(Kp=self.Kp, Ki=self.Ki, Kd=self.Kd, ff=self.ff)

    def update_ctrl_params_from_config(self, config: Type[config_util.ConfigurableConstants]):
        '''For modularity, new controllers ideally use this function to update internal
        control params (e.g., k_val, or rise_time) from the config object. If needed, add
        new ctrl params to ConfigurableConstants.'''
        raise ValueError(
            'update_ctrl_params_from_config() not defined in child class of Controller')

    def __init__(self,
                 exo: Exo,
                 k_val: int,
                 b_val: int = 0,
                 Kp: int = constants.DEFAULT_KP,
                 Ki: int = constants.DEFAULT_KI,
                 Kd: int = constants.DEFAULT_KD,
                 ff: int = constants.DEFAULT_FF):
        self.exo = exo
        self.k_val = k_val
        self.b_val = b_val
        super().update_controller_gains(Kp=Kp, Ki=Ki, Kd=Kd, ff=ff)
        self.hip_angles = deque(maxlen=5)  # looking for peak in pf
        self.hip_angle_filter = filters.Butterworth(N=2, Wn=0.1)

    def command(self, reset=False):
        if reset:
            self.is_taught = False
            self.found_setpt = False
            self.do_engage = False
            self.hip_angles.clear()  # Reset the hip angle deque
            self.hip_angle_filter.restart()  # Reset the filter
            super().command_gains()
            self.exo.data.gen_var2 = None
        self.hip_angles.appendleft(
            self.hip_angle_filter.filter(self.exo.data.hip_angle))
        self.exo.data.gen_var3 = self.hip_angles[0]

        if self.found_setpt is False:
            # TODO(maxshep) see if you want to change min val
            if len(self.hip_angles) == 5 and (self.hip_angles[1] > self.hip_angles[0] and
                                                self.hip_angles[1] > self.hip_angles[2]) and (
                    self.hip_angles[0] > 5):
                self.exo.data.gen_var2 = self.hip_angles[1]
                self.found_setpt = True
                self._update_setpoint(theta0=self.hip_angles[1])

        if self.is_taught and self.found_setpt:
            self.exo.update_gains(Kp=20, Ki=200, Kd=0, ff=60)
            # super().command_gains()
            # print('engaged..., desired k_val: ', self.k_val,
            #       'setpoint: ', self.hip_angles[0])
            self.exo.command_motor_impedance(
                theta0=self.theta0_motor, k_val=self.k_val, b_val=self.b_val)
            self.exo.data.gen_var1 = 6

        else:
            mv_to_apply = 1500  # 1500
            self.exo.command_voltage(
                desired_mV=self.exo.motor_sign * mv_to_apply)
            # self.exo.command_torque(desired_torque=1)
            self.exo.data.gen_var1 = 5

    def _update_setpoint(self, theta0):
        '''Take in desired hip setpoint (deg) and stores equivalent motor angle.'''
        if theta0 > constants.MAX_HIP_ANGLE or theta0 < constants.MIN_HIP_ANGLE:
            raise ValueError(
                'Attempted to command a set point outside the range of motion')
        self.theta0_motor = self.exo.hip_angle_to_motor_angle(theta0)

    def update_ctrl_params_from_config(self, config: Type[config_util.ConfigurableConstants]):
        'Updates controller parameters from the config object.'''
        if self.k_val != config.K_VAL:
            self.k_val = config.K_VAL
            print('K updated to: ', self.k_val)
        # TODO(maxshep) see what val you like for this in params
        self.b_val = config.B_VAL



class GenericSplineController(Controller):
    def __init__(self,
                 exo: Type[Exo],
                 spline_x: list,
                 spline_y: list,
                 use_gait_phase: bool = True,
                 fade_duration: float = 5,
                 Kp: int = constants.DEFAULT_KP,
                 Ki: int = constants.DEFAULT_KI,
                 Kd: int = constants.DEFAULT_KD,
                 ff: int = constants.DEFAULT_FF):
        self.exo = exo
        self.spline = None  # Placeholds so update_spline can fill self.last_spline
        self.update_spline(spline_x, spline_y, first_call=True)
        self.fade_duration = fade_duration
        self.use_gait_phase = use_gait_phase  # if False, use time (s)
        super().update_controller_gains(Kp=Kp, Ki=Ki, Kd=Kd, ff=ff)
        # Fade timer goes from 0 to fade_duration, active if below fade_duration (starts inactive)
        self.fade_start_time = time.perf_counter()-100
        self.t0 = None

    def command(self, reset=False):
        '''Commands appropriate control. If reset=True, this controller was just switched to.'''
        if reset:
            super().command_gains()
            self.t0 = time.perf_counter()

        if self.use_gait_phase:
            phase = self.exo.data.gait_phase
        else:
            phase = time.perf_counter()-self.t0

        if phase is None:
            # Gait phase is sometimes None
            desired_torque = 0
        elif phase > self.spline_x[-1]:
            # If phase (elapsed time) is longer than spline is specified, use last spline point
            print('phase is longer than specified spline')
            desired_torque = self.spline(self.spline_x)
        elif time.perf_counter() - self.fade_start_time < self.fade_duration:
            # If fading splines
            desired_torque = self.fade_splines(
                phase=phase, fraction=(time.perf_counter()-self.fade_start_time)/self.fade_duration)
        else:
            desired_torque = self.spline(phase)

        self.exo.command_torque(desired_torque)

    def update_spline(self, spline_x, spline_y, first_call=False):
        if first_call or self.spline_x != spline_x or self.spline_y != spline_y:
            self.spline_x = spline_x
            self.spline_y = spline_y
            print('Splines updated: ', 'x = ', spline_x, 'y = ', spline_y)
            self.fade_start_time = time.perf_counter()
            self.last_spline = copy.deepcopy(self.spline)
            self.spline = interpolate.pchip(
                spline_x, spline_y, extrapolate=False)

    def fade_splines(self, phase, fraction):
        torque_from_last_spline = self.last_spline(phase)
        torque_from_current_spline = self.spline(phase)
        desired_torque = (1-fraction)*torque_from_last_spline + \
            fraction*torque_from_current_spline
        return desired_torque


class FourPointSplineController(GenericSplineController):
    def __init__(self,
                 exo: Exo,
                 rise_fraction: float = 0.2,
                 peak_torque: float = 5,
                 peak_fraction: float = 0.55,
                 fall_fraction: float = 0.6,
                 Kp: int = constants.DEFAULT_KP,
                 Ki: int = constants.DEFAULT_KI,
                 Kd: int = constants.DEFAULT_KD,
                 ff: int = constants.DEFAULT_FF,
                 fade_duration: float = 5,
                 bias_torque: float = 5,
                 use_gait_phase: bool = True,
                 peak_hold_time: float = 0):
        '''Inherits from GenericSplineController, and adds a update_spline_with_list function.'''
        self.bias_torque = bias_torque  # Prevents rounding issues near zero and keeps cord taught
        self.peak_hold_time = peak_hold_time  # can be used to hold a peak
        super().__init__(exo=exo,
                         spline_x=self._get_spline_x(
                             rise_fraction, peak_fraction, fall_fraction),
                         spline_y=self._get_spline_y(peak_torque),
                         Kp=Kp, Ki=Ki, Kd=Kd, ff=ff,
                         fade_duration=fade_duration,
                         use_gait_phase=use_gait_phase)

    def update_ctrl_params_from_config(self, config: Type[config_util.ConfigurableConstants]):
        'Updates controller parameters from the config object.'''
        super().update_spline(spline_x=self._get_spline_x(rise_fraction=config.RISE_FRACTION,
                                                          peak_fraction=config.PEAK_FRACTION,
                                                          fall_fraction=config.FALL_FRACTION),
                              spline_y=self._get_spline_y(peak_torque=config.PEAK_TORQUE))

    def _get_spline_x(self, rise_fraction, peak_fraction, fall_fraction) -> list:
        if self.peak_hold_time > 0:
            return [0, rise_fraction, peak_fraction, peak_fraction+self.peak_hold_time, fall_fraction, 1]
        else:
            return [0, rise_fraction, peak_fraction, fall_fraction, 1]

    def _get_spline_y(self, peak_torque) -> list:
        if self.peak_hold_time > 0:
            return [self.bias_torque, self.bias_torque, peak_torque, peak_torque, self.bias_torque, self.bias_torque]
        else:
            return [self.bias_torque, self.bias_torque, peak_torque, self.bias_torque, self.bias_torque]

class HipSplineController(GenericSplineController):
    def __init__(self,
                 exo: Exo,
                 min_fraction: float = 0.12,
                 first_zero: float = 0.37,
                 peak_fraction: float = 0.66,
                 second_zero: float = 0.9,
                 Kp: int = constants.DEFAULT_KP,
                 Ki: int = constants.DEFAULT_KI,
                 Kd: int = constants.DEFAULT_KD,
                 ff: int = constants.DEFAULT_FF,
                 fade_duration: float = 5,
                 bias_torque: float = 5,
                 start_torque: float = -1.5,
                 extension_min_torque: float = -4,
                 flexion_max_torque: float = 2.5,
                 use_gait_phase: bool = True,
                 peak_hold_time: float = 0):
        '''Inherits from GenericSplineController, and adds a update_spline_with_list function.'''
        self.peak_hold_time = peak_hold_time  # can be used to hold a peak
        self.bias_torque = bias_torque
        super().__init__(exo=exo,
                         spline_x=self._get_spline_x(
                             min_fraction,first_zero,peak_fraction,second_zero),
                         spline_y=self._get_spline_y(start_torque, extension_min_torque, flexion_max_torque),
                         Kp=Kp, Ki=Ki, Kd=Kd, ff=ff,
                         fade_duration=fade_duration,
                         use_gait_phase=use_gait_phase)

    def update_ctrl_params_from_config(self, config: Type[config_util.ConfigurableConstants]):
        'Updates controller parameters from the config object.'''
        super().update_spline(spline_x=self._get_spline_x(min_fraction=config.MIN_FRACTION,
                                                          peak_fraction=config.PEAK_FRACTION,
                                                          first_zero=config.FIRST_ZERO,
                                                          second_zero=config.SECOND_ZERO),
                              spline_y=self._get_spline_y(start_torque=config.START_TORQUE,
                                                          extension_min_torque=config.EXTENSION_MIN_TORQUE,
                                                          flexion_max_torque=config.FLEXION_MAX_TORQUE))

    def _get_spline_x(self, min_fraction, first_zero, peak_fraction, second_zero) -> list:
        if self.peak_hold_time > 0:
            return [0, min_fraction, min_fraction+self.peak_hold_time, first_zero, peak_fraction, peak_fraction+self.peak_hold_time, second_zero, 1]
        else:
            return [0, min_fraction, first_zero, peak_fraction, second_zero, 1]

    def _get_spline_y(self, start_torque, extension_min_torque, flexion_max_torque) -> list:
        if self.peak_hold_time > 0:
            return [start_torque, extension_min_torque, extension_min_torque, self.bias_torque, flexion_max_torque, flexion_max_torque, self.bias_torque, start_torque]
        else:
            return [start_torque, extension_min_torque, self.bias_torque, flexion_max_torque, self.bias_torque, start_torque]

class GenericImpedanceController(Controller):
    def __init__(self,
                 exo: Exo,
                 setpoint,
                 k_val,
                 b_val=0,
                 Kp: int = constants.DEFAULT_KP,
                 Ki: int = constants.DEFAULT_KI,
                 Kd: int = constants.DEFAULT_KD,
                 ff: int = constants.DEFAULT_FF):
        self.exo = exo
        self.setpoint = setpoint
        self.k_val = k_val
        self.b_val = b_val
        super().update_controller_gains(Kp=Kp, Ki=Ki, Kd=Kd, ff=ff)

    def command(self, reset=False):
        if reset:
            super().command_gains()
        theta0_motor = self.exo.hip_angle_to_motor_angle(self.setpoint)
        self.exo.command_motor_impedance(
            theta0=theta0_motor, k_val=self.k_val, b_val=self.b_val)

    def update_ctrl_params_from_config(self, config: Type[config_util.ConfigurableConstants],
                                       update_k=True, update_b=True, update_setpoint=True):
        'Updates controller parameters from the config object.'''
        if update_k:
            self.k_val = config.K_VAL
        if update_b:
            self.b_val = config.B_VAL
        if update_setpoint:
            self.setpoint = config.SET_POINT
