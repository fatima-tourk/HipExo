import csv
import logging
import os
import sys
import time
import warnings
from dataclasses import dataclass, field, InitVar
#from scipy import interpolate
from typing import Type
import numpy as np
import pandas as pd
import config_util
import constants
import filters
from flexsea import fxEnums as fxe
from flexsea import flexsea as flex
from flexsea import fxUtils as fxu

# Instantiate Dephy's FlexSEA object, which contains important functions
fxs = flex.FlexSEA()


def connect_to_exos(IS_HARDWARE_CONNECTED,file_ID: str,
                    config: Type[config_util.ConfigurableConstants],
                    sync_detector=None, offline_data_left = None, offline_data_right = None):
    '''Connect to Exos, instantiate Exo objects.'''

    # Load Ports and baud rate
    if fxu.is_win():		# Need for WebAgg server to work in Python 3.8
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        port_cfg_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "ports.yaml")
        ports, baud_rate = fxu.load_ports_from_file(port_cfg_path)
    elif fxu.is_pi64() or fxu.is_pi():
        ports = ['/dev/ttyACM0', '/dev/ttyACM1']
        baud_rate = constants.DEFAULT_BAUD_RATE
    else:
        raise ValueError('Code only supports Windows or pi64 so far')
    if IS_HARDWARE_CONNECTED:
        print('Detected win32')
        print(f"Using ports:\t{ports}")

    exo_list = []
    count = 0
    print('Hardware connected: ', IS_HARDWARE_CONNECTED)
    for port in ports:
        try:
            if IS_HARDWARE_CONNECTED:
                print(IS_HARDWARE_CONNECTED)
                dev_id = fxs.open(port, baud_rate, log_level=3)
                print(dev_id)
                fxs.start_streaming(
                    dev_id=dev_id, freq=config.ACTPACK_FREQ, log_en=config.DO_DEPHY_LOG)
                print(config.ACTPACK_FREQ)
                print(config.DO_DEPHY_LOG)
                exo_list.append(Exo(IS_HARDWARE_CONNECTED,dev_id=dev_id, file_ID=file_ID,
                                    target_freq=config.TARGET_FREQ,
                                    max_allowable_current=config.MAX_ALLOWABLE_CURRENT,
                                    min_allowable_current=config.MIN_ALLOWABLE_CURRENT,
                                    do_include_gen_vars=config.DO_INCLUDE_GEN_VARS,
                                    sync_detector=sync_detector))
                print('exo',exo_list)
                print('connected port: ', port)
            else:
                port_numbers = [4321, 1234]
                exo_list.append(Exo(IS_HARDWARE_CONNECTED, dev_id=int(port_numbers[count]), file_ID=file_ID,
                                            target_freq=config.TARGET_FREQ,
                                            max_allowable_current=config.MAX_ALLOWABLE_CURRENT,
                                            min_allowable_current=config.MIN_ALLOWABLE_CURRENT,
                                            do_include_gen_vars=config.DO_INCLUDE_GEN_VARS,
                                            sync_detector=sync_detector,
                                            offline_data_left= offline_data_left,
                                            offline_data_right= offline_data_right))
                count = count + 1
        except IOError:
            print('Unable to open exo on port: ', port,
                  ' This is okay if only one exo is connected!')
    if not exo_list:  # (if empty)
        raise RuntimeError('No Exos connected')
    return exo_list


class Exo():
    def __init__(self,
                 IS_HARDWARE_CONNECTED,
                 dev_id: int,
                 max_allowable_current: int,
                 min_allowable_current: int,
                 file_ID: str = None,
                 target_freq: float = 200,
                 do_include_gen_vars: bool = False,
                 sync_detector=None,
                 offline_data_left=None,
                 offline_data_right=None):
        '''Exo object is the primary interface with the Dephy hip exos, and corresponds to a single physical actpack.
        Args:
            dev_id: int. Unique integer to identify the exo in flexsea's library. Returned by connect_to_exo
            file_ID: str. Unique string added to filename. If None, no file will be saved.
            sync_detector: gpiozero class for sync line, created in config_util '''
        self.IS_HARDWARE_CONNECTED = IS_HARDWARE_CONNECTED
        self.left_side_offline_data = offline_data_left
        self.right_side_offline_data = offline_data_right
        self.dev_id = dev_id
        self.max_allowable_current = max_allowable_current
        self.min_allowable_current = min_allowable_current
        self.file_ID = file_ID
        self.do_include_sync = True if sync_detector else False
        self.sync_detector = sync_detector
        if self.dev_id is None:
            print('Exo obj created but no hip_exo connected. Some methods available')
        elif self.dev_id in constants.LEFT_EXO_DEV_IDS:
            self.side = constants.Side.LEFT
            self.motor_sign = -1
            if not self.IS_HARDWARE_CONNECTED: 
                self.actpack_data = offline_data_left
        elif self.dev_id in constants.RIGHT_EXO_DEV_IDS:
            self.side = constants.Side.RIGHT
            self.motor_sign = 1
            if not self.IS_HARDWARE_CONNECTED: 
                self.actpack_data = offline_data_right
        else:
            raise ValueError(
                'dev_id: ', self.dev_id, 'not found in constants.LEFT_EXO_DEV_IDS or constants.RIGHT_EXO_DEV_IDS')
        self.motor_offset = 0
        # hip velocity filter is hardcoded for simplicity, but can be factored out if necessary
        self.hip_velocity_filter = filters.Butterworth(
            N=2, Wn=10, fs=target_freq)
        self.angle_filter = filters.Butterworth(
            N=2, Wn=2, fs=target_freq)

        self.data = self.DataContainer(
            do_include_gen_vars=do_include_gen_vars, do_include_sync=self.do_include_sync)
        self.is_clipping = False
        if self.file_ID is not None:
            self.setup_data_writer(file_ID=file_ID)
        if self.dev_id is not None:
            self.update_gains(Kp=constants.DEFAULT_KP,
                              Ki=constants.DEFAULT_KI,
                              Kd=constants.DEFAULT_KD,
                              k_val=0,
                              b_val=0,
                              ff=constants.DEFAULT_FF)
            self.TR = 9

    @dataclass
    class DataContainer:
        '''A nested dataclass within Exo, reserving space for instantaneous data.'''
        do_include_sync: InitVar[bool] = False
        do_include_gen_vars: InitVar[bool] = False
        state_time: float = 0
        loop_time: float = 0
        accel_x: float = 0
        accel_y: float = 0
        accel_z: float = 0
        gyro_x: float = 0
        gyro_y: float = 0
        gyro_z: float = 0
        motor_angle: int = 0
        motor_velocity: float = 0
        motor_current: int = 0
        hip_angle: float = 0
        hip_angle_filtered: float = 0
        hip_velocity: float = 0
        hip_torque_from_current: float = 0
        did_heel_strike: bool = False
        gait_phase: float = None
        did_toe_off: bool = False
        commanded_current: int = None
        commanded_position: int = None
        commanded_torque: float = None
        commanded_voltage: int = None
        temperature: int = None
        # Optional fields--init in __post__init__
        sync: bool = field(init=False)
        gen_var1: float = field(init=False)
        gen_var2: float = field(init=False)
        gen_var3: float = field(init=False)

        def __post_init__(self, do_include_sync, do_include_gen_vars):
            # Important! The order of these args need to match their order as InitVars above
            if do_include_gen_vars:
                self.gen_var1 = None
                self.gen_var2 = None
                self.gen_var3 = None
            if do_include_sync:
                self.sync = True

    def close(self):
        self.update_gains()
        self.command_current(desired_mA=0)
        time.sleep(0.1)
        self.command_controller_off()
        time.sleep(0.05)
        if self.IS_HARDWARE_CONNECTED:
            fxs.stop_streaming(self.dev_id)
        time.sleep(0.2)
        if self.IS_HARDWARE_CONNECTED:
            fxs.close(self.dev_id)
        self.close_file()
        if self.do_include_sync:
            self.sync_detector.close()

    def update_gains(self, Kp=None, Ki=None, Kd=None, k_val=None, b_val=None, ff=None):
        '''Optionally updates individual exo gain values, and sends to Actpack.'''
        if Kp is not None:
            self.Kp = Kp
        if Ki is not None:
            self.Ki = Ki
        if Kd is not None:
            self.Kd = Kd
        if k_val is not None:
            self.k_val = k_val
        if b_val is not None:
            self.b_val = b_val
        if ff is not None:
            self.ff = ff
        if self.IS_HARDWARE_CONNECTED:
            fxs.set_gains(dev_id=self.dev_id, kp=self.Kp, ki=self.Ki,
                      kd=self.Kd, k_val=self.k_val, b_val=self.b_val, ff=self.ff)

    def read_data(self, hip_exo_side=None, iteration_count=None, loop_time=None):
        '''Read data from Dephy Actpack, store in exo.data Data Container.

        IMU data comes from Dephy in RHR, with positive XYZ pointing
        backwards, downwards, and rightwards on the right side and forwards,
        downwards, and leftwards on the left side. It is converted here
        to LHR on left side and RHR on right side. XYZ axes now point
        forwards, upwards, and outwards (laterally).'''
        if loop_time is not None:
            self.data.loop_time = loop_time

        last_hip_angle = self.data.hip_angle
        self.last_state_time = self.data.state_time

        if self.IS_HARDWARE_CONNECTED:
            actpack_data = fxs.read_device(self.dev_id)
            # Check to see if values are reasonable
            hip_angle_temp = (self.motor_sign * actpack_data.mot_ang *
                                constants.MOTOR_CLICKS_TO_DEG)
            self.data.hip_angle = hip_angle_temp
            self.data.state_time = actpack_data.state_time * constants.MS_TO_SECONDS
            self.data.temperature = actpack_data.temperature

            self.data.accel_x = -1 * self.motor_sign * \
                actpack_data.accelx * constants.ACCEL_GAIN
            self.data.accel_y = -1 * actpack_data.accely * constants.ACCEL_GAIN
            self.data.accel_z = -1* actpack_data.accelz * constants.ACCEL_GAIN
            self.data.gyro_x = 1 * actpack_data.gyrox * constants.GYRO_GAIN
            self.data.gyro_y = 1 * self.motor_sign * \
                actpack_data.gyroy * constants.GYRO_GAIN
            self.data.gyro_z = 1* self.motor_sign * actpack_data.gyroz * constants.GYRO_GAIN
            '''Motor angle and current are kept in Dephy's orientation, but hip
            angle and torque are converted to positive = plantarflexion.'''
            self.data.motor_angle = actpack_data.mot_ang
            self.data.motor_velocity = actpack_data.mot_vel
            self.data.motor_current = actpack_data.mot_cur
            self.data.hip_torque_from_current = self._motor_current_to_hip_torque(
                self.data.motor_current)
            #self.data.hip_angle_filtered = (-1*self.angle_filter.filter(self.data.hip_angle))

        else:
            hip_ang = self.actpack_data['hip_angle'][iteration_count]
            hip_angle_temp = hip_ang
            self.data.state_time = self.actpack_data['state_time'][iteration_count]
            self.data.hip_angle = hip_angle_temp
            self.data.temperature = self.actpack_data['temperature'][iteration_count]
            self.data.accel_x = self.actpack_data['accel_x'][iteration_count]
            self.data.accel_y = self.actpack_data['accel_y'][iteration_count]
            self.data.accel_z = self.actpack_data['accel_z'][iteration_count]
            self.data.gyro_x = self.actpack_data['gyro_x'][iteration_count]
            self.data.gyro_y = self.actpack_data['gyro_y'][iteration_count]
            self.data.gyro_z = self.actpack_data['gyro_z'][iteration_count]
            '''Motor angle and current are kept in Dephy's orientation, but hip
            angle and torque are converted to positive = flexion.'''
            self.data.motor_angle = self.actpack_data['motor_angle'][iteration_count]
            self.data.motor_velocity = self.actpack_data['motor_velocity'][iteration_count]
            self.data.motor_current = self.actpack_data['motor_current'][iteration_count]
            self.data.hip_torque_from_current = self._motor_current_to_hip_torque(
                self.data.motor_current) 
            self.data.did_heel_strike = self.actpack_data['did_heel_strike'][iteration_count]
            self.data.gait_phase = self.actpack_data['gait_phase'][iteration_count]
            self.data.did_toe_off = self.actpack_data['did_toe_off'][iteration_count]
            self.data.temperature = self.actpack_data['temperature'][iteration_count]

        # self.data.gen_var4 = iteration_count

        if self.IS_HARDWARE_CONNECTED:
            if (self.last_state_time is None or last_hip_angle is None or self.data.state_time-self.last_state_time > 20):
                self.data.hip_velocity = 0
            elif self.data.state_time == self.last_state_time:
                pass  # Keep old velocity
            else:
                angular_velocity = (self.data.hip_angle - last_hip_angle)/(self.data.state_time-self.last_state_time)
                self.data.hip_velocity = self.hip_velocity_filter.filter(angular_velocity)
        else:
            if self.last_state_time is None or last_hip_angle is None or self.data.state_time - self.last_state_time > 20:
                self.data.hip_velocity = 0
            elif self.data.state_time == self.last_state_time:
                pass  # Keep old velocity
            else:
                self.data.hip_velocity = float(self.actpack_data['hip_velocity'][iteration_count])

        if self.do_include_sync:
            self.data.sync = self.sync_detector.value
            if self.data.sync==0 and self.only_first_sync_detected:
                print('Sync Detected!')
                self.only_first_sync_detected = False

    def get_batt_voltage(self):
        actpack_data = fxs.read_device(self.dev_id)
        return actpack_data.batt_volt

    def setup_data_writer(self, file_ID: str):
        '''file_ID is used as a custom file identifier after date.'''
        if file_ID is not None:
            subfolder_name = 'exo_data/'
            self.filename = subfolder_name + \
                time.strftime("%Y%m%d_%H%M_") + file_ID + \
                '_' + self.side.name + '.csv'
            self.my_file = open(self.filename, 'w', newline='')
            self.writer = csv.DictWriter(
                self.my_file, fieldnames=self.data.__dict__.keys())
            self.writer.writeheader()
            self._did_heel_strike_hold = False
            self._did_toe_off_hold = False

    def write_data(self):
        if self.file_ID is not None:
            self.writer.writerow(self.data.__dict__)

    def close_file(self):
        if self.file_ID is not None:
            self.my_file.close()

    def command_current(self, desired_mA: int):
        if abs(desired_mA) > self.max_allowable_current:
            self.command_controller_off()
            raise ValueError(
                'abs(desired_mA) must be < config.max_allowable_current')
        if self.IS_HARDWARE_CONNECTED:
            fxs.send_motor_command(
                dev_id=self.dev_id, ctrl_mode=fxe.FX_CURRENT, value=desired_mA)
        self.data.commanded_current = desired_mA
        self.data.commanded_position = None
        self.data.commanded_voltage = None
    
    def run_angle_safety(self, hip_angle: float):
        if (hip_angle > constants.MAX_HIP_ANGLE) or (hip_angle < constants.MIN_HIP_ANGLE):
            self.command_controller_off()
            raise ValueError(
                'Hip angle outside of acceptable range')

    def command_voltage(self, desired_mV: int):
        '''Commands voltage (mV), with positive = DF on right, PF on left.
        DIFFERENT FROM OLD BOOTS'''
        if abs(desired_mV) > constants.MAX_ALLOWABLE_VOLTAGE_COMMAND:
            raise ValueError(
                'abs(desired_mV) must be < constants.MAX_ALLOWABLE_VOLTAGE_COMMAND')
        if self.IS_HARDWARE_CONNECTED:
            fxs.send_motor_command(
                dev_id=self.dev_id, ctrl_mode=fxe.FX_VOLTAGE, value=desired_mV)
        self.data.commanded_current = None
        self.data.commanded_position = None
        self.data.commanded_torque = None
        self.data.commanded_voltage = int(desired_mV)
        # print('desired_mV:', desired_mV, self.data.commanded_voltage)

    def command_motor_angle(self, desired_motor_angle: int):
        '''Commands motor angle (counts). Pay attention to the sign!'''
        if self.IS_HARDWARE_CONNECTED:
            fxs.send_motor_command(
                dev_id=self.dev_id, ctrl_mode=fxe.FX_POSITION, value=desired_motor_angle)
        self.data.commanded_current = None
        self.data.commanded_position = desired_motor_angle
        self.data.commanded_torque = None
        self.data.commanded_voltage = None

    def command_motor_impedance(self, theta0: int, k_val: int, b_val: int):
        '''Commands motor impedance, with theta0 a motor position (int).'''
        # k_val and b_val are modified by updating gains (weird, yes)
        if k_val > constants.MAX_ALLOWABLE_K_COMMAND or k_val < 0:
            raise ValueError(
                'k_val must be positive, and less than max. tested k_val in constants.py')
        if b_val > constants.MAX_ALLOWABLE_B_COMMAND or b_val < 0:
            raise ValueError(
                'b_val must be positive, and less than max. tested b_val in constants.py')
        if self.k_val != k_val or self.b_val != b_val:
            # Only send gains when necessary
            self.update_gains(k_val=int(k_val), b_val=int(b_val))
        if self.IS_HARDWARE_CONNECTED:
            fxs.send_motor_command(
                dev_id=self.dev_id, ctrl_mode=fxe.FX_IMPEDANCE, value=int(theta0))
        self.data.commanded_current = None
        self.data.commanded_position = None
        self.data.commanded_torque = None

    def command_torque(self, desired_torque: float, do_return_command_torque=False):
        self.data.commanded_torque = desired_torque
        max_allowable_torque = self.calculate_max_allowable_torque()
        min_allowable_torque = self.calculate_min_allowable_torque()
        if abs(desired_torque) > max_allowable_torque:
            if self.is_clipping is False:  # Only print once when clipping occurs before reset
                logging.warning('Torque was clipped!')
            desired_torque = min(desired_torque, max_allowable_torque)
            desired_torque = max(desired_torque, min_allowable_torque)
            self.is_clipping = True
        else:
            self.is_clipping = False
        desired_current = self._hip_torque_to_motor_current(torque=desired_torque)
        self.command_current(desired_mA = desired_current)
        if do_return_command_torque:
            return desired_torque

    # CHECK IF IMPEDANCE CONTROLLER AND STIFFNESS WORK THE SAME WAY, EDIT IF THIS DOES NOT WORK FOR HIP
    def command_hip_impedance(self, theta0_hip: float, K_hip: float, B_hip: float = 0):
        raise ValueError('Not implemented')
        theta0_motor = self.hip_angle_to_motor_angle(theta0_hip)
        K_dephy = K_hip / constants.DEPHY_K_TO_HIP_K
        # B_dephy = B_hip / constants.DEPHY_B_TO_HIP_B
        self.command_motor_impedance(
            theta0=theta0_motor, k_val=K_dephy, b_val=0)

    def command_controller_off(self):
        if self.IS_HARDWARE_CONNECTED:
            fxs.send_motor_command(
            dev_id=self.dev_id, ctrl_mode=fxe.FX_NONE, value=0)

    def calculate_max_allowable_torque(self):
        '''Calculates max allowable torque from self.max_allowable_current and hip_angle.'''
        max_allowable_torque = max(
            0, self._motor_current_to_hip_torque(current=self.max_allowable_current))
        return max_allowable_torque
    
    def calculate_min_allowable_torque(self):
        '''Calculates min allowable torque from self.min_allowable_current and hip_angle.'''
        min_allowable_torque = min(
            0, self._motor_current_to_hip_torque(current=self.min_allowable_current))
        return min_allowable_torque

    def _motor_current_to_hip_torque(self, current: int) -> float:
        '''Converts current (mA) to torque (Nm), based on side and transmission ratio (no dynamics)'''
        motor_torque = current*constants.MOTOR_CURRENT_TO_MOTOR_TORQUE
        hip_torque = motor_torque * self.TR
        return hip_torque

    def _hip_torque_to_motor_current(self, torque: float) -> int:
        '''Converts torque (Nm) to current (mA), based on side and transmission ratio (no dynamics)'''
        motor_torque = torque / self.TR
        motor_current = int(self.motor_sign*
            motor_torque / constants.MOTOR_CURRENT_TO_MOTOR_TORQUE)
        return motor_current

    def motor_angle_to_hip_angle(self, config: Type[config_util.ConfigurableConstants]):
        '''Calculate hip angle from motor angle.'''
        if config.HIP_ZERO_POSITION==None:
            raise ValueError(
                'Must perform standing calibration before performing this task')
        else:
            hip_angle = (self.motor_sign)*(self.data.motor_angle-config.HIP_ZERO_POSITION)*constants.MOTOR_CLICKS_TO_DEG
            self.data.hip_angle = hip_angle
        return hip_angle 
    
    def hip_angle_to_motor_angle(self):
        '''Calculate hip angle from motor angle.'''
        motor_angle = (self.data.hip_angle)/constants.MOTOR_CLICKS_TO_DEG
        return motor_angle 
    
    def hip_standing_calibration(self, config: Type[config_util.ConfigurableConstants],
                                max_seconds_to_calibrate: float = 2):
        input(['Press Enter to calibrate exo on ' + str(self.side)])
        time.sleep(0.2)
        print('Calibrating...')
        t0 = time.time()
        calibration_angles = []
        while time.time()-t0 < max_seconds_to_calibrate:
            time.sleep(0.01)
            self.read_data()
            current_calibration_angle = self.angle_filter.filter(self.data.motor_angle)
            calibration_angles.append(current_calibration_angle)
        hip_zero_position = np.mean(calibration_angles)
        config.HIP_ZERO_POSITION = hip_zero_position
    
    def standing_calibration_offline(self, past_motor_offset):
        '''Brings motor offset angles.'''
        self.motor_offset = past_motor_offset