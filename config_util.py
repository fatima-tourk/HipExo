from typing import Type, List
from dataclasses import dataclass, field
import time
import csv
import sys
import importlib
from enum import Enum
import argparse
import constants


class Task(Enum):
    '''Used to determine gait_event_detector used and state machines used.'''
    WALKING = 0
    WALKINGMLGAITPHASE = 4



@dataclass
class ConfigurableConstants():
    '''Class that stores configuration-related constants.

    These variables serve to allow 1) loadable configurations from files in /custom_constants/, 
    2) online updating of device behavior via parameter_passers.py, and 3) to store calibration 
    details. Below are the default config constants. DO NOT MODIFY DEFAULTS. Write your own short
    script in /custom_constants/ (see default_config.py for example).
    (see )  '''
    # Set by functions... no need to change in config file
    loop_time: float = 0
    actual_time: float = time.time()
    HIP_LEFT_STANDING_ANGLE: float = None # Deg
    HIP_RIGHT_STANDING_ANGLE: float = None # Deg
    HIP_ZERO_POSITION: float = None

    TARGET_FREQ: float = 175  # Hz
    ACTPACK_FREQ: float = 200  # Hz
    DO_DEPHY_LOG: bool = True

    TASK: Type[Task] = Task.WALKING
    MAX_ALLOWABLE_CURRENT = 17000  # mA
    MIN_ALLOWABLE_CURRENT = -17000 # mA

    # Gait State details
    HS_ANGLE_FILTER_N: int = 2
    HS_ANGLE_FILTER_WN: float = 0.1
    HS_ANGLE_DELAY: float = 0.05
    TOE_OFF_FRACTION: float = 0.60
    HEEL_STRIKE_FRACTION: float = 0.40
    NUM_STRIDES_REQUIRED: int = 2
    SWING_ONLY: bool = False
    MAXIMUM_ANGLE: float = 1

    # 4 point Spline
    RISE_FRACTION: float = 0.278
    PEAK_FRACTION: float = 0.543
    FALL_FRACTION: float = 0.641
    PEAK_TORQUE: float = 30
    SPLINE_BIAS: float = 3  # Nm

    # Hip Spline
    MIN_FRACTION: float = 0.12
    FIRST_ZERO: float = 0.37
    PEAK_FRACTION: float = 0.66
    SECOND_ZERO: float = 0.90

    #START_TORQUE: float = -1.5
    #FLEXION_MAX_TORQUE: float = 2.5
    #EXTENSION_MIN_TORQUE: float = -4.0

    START_TORQUE: float = -6
    FLEXION_MAX_TORQUE: float = 10
    EXTENSION_MIN_TORQUE: float = -16.0

    # Impedance
    K_VAL: int = 500
    B_VAL: int = 0
    B_RATIO: float = 0.5  # when B_VAL is a function of B_RATIO. 2.5 is approx. crit. damped
    SET_POINT: float = 0  # Deg

    READ_ONLY: bool = False  # Does not require Lipos
    DO_READ_SYNC: bool = False

    PRINT_HS: bool = True  # Print heel strikes
    PRINT_TO: bool = True  # Print toe offs
    VARS_TO_PLOT: List = field(default_factory=lambda: [])
    DO_INCLUDE_GEN_VARS: bool = False
    DO_FILTER_GAIT_PHASE: bool = False

    # Offline Testing Parameter
    IS_HARDWARE_CONNECTED: bool = True
    LEFT_MOTOR_OFFSET: float = 0
    RIGHT_MOTOR_OFFSET: float = 0

    # Include Additional Exo Data (For Debugging Purposes)
    DO_INCLUDE_EXO_ADD_DATA: bool = False
    
    EXPERIMENTER_NOTES: str = 'Experimenter notes go here'


class ConfigSaver():
    def __init__(self, file_ID: str, config: Type[ConfigurableConstants]):
        '''file_ID is used as a custom file identifier after date.'''
        self.file_ID = file_ID
        self.config = config
        subfolder_name = 'exo_data/'
        filename = subfolder_name + \
            time.strftime("%Y%m%d_%H%M_") + file_ID + \
            '_CONFIG' + '.csv'
        self.my_file = open(filename, 'w', newline='')
        self.writer = csv.DictWriter(
            self.my_file, fieldnames=self.config.__dict__.keys())
        self.writer.writeheader()

    def write_data(self, loop_time):
        '''Writes new row of Config data to Config file.'''
        self.config.loop_time = loop_time
        self.config.actual_time = time.time()
        self.writer.writerow(self.config.__dict__)

    def close_file(self):
        if self.file_ID is not None:
            self.my_file.close()


def load_config(config_filename, offline_value, hardware_connected) -> tuple[any, any]:
    
    try:
        # strip extra parts off
        config_filename = config_filename.lower()
        if config_filename.endswith('_config'):
            config_filename = config_filename[:-7]
        elif config_filename.endswith('_config.py'):
            config_filename = config_filename[:-10]
        elif config_filename.endswith('.py'):
            config_filename = config_filename[:-4]
        elif config_filename.endswith('_config.csv'):
            config_filename = config_filename[:-11]
        config_filename = config_filename + '_config'
        module = importlib.import_module('.' + config_filename, package='custom_configs')
    except:
        error_str = 'Unable to find config file: ' + \
            config_filename + ' in custom_config'
        raise ValueError(error_str)
    config = module.config
    
    if hardware_connected == 'True':
        config.IS_HARDWARE_CONNECTED = True
    elif hardware_connected == 'False':
        config.IS_HARDWARE_CONNECTED = False
    else: 
        print('Hardware Connection Status not interpretable.')
        quit()
    print('Using ConfigurableConstants from: ', config_filename)

    if offline_value:
        try:
            offline_test_time_duration = float(offline_value)
            print('\nOffline Test Time Duration = ' + str(offline_test_time_duration) + ' seconds.\n')
        except: 
            print('Offline Test Time Duration should be an integer or float value.')
            quit()
    else: offline_test_time_duration = offline_value

    return config, offline_test_time_duration


def parse_args():
    # Create the parser
    my_parser = argparse.ArgumentParser(prog='hip_exo Code',
                                        description='Run hip_exo Controllers',
                                        epilog='Enjoy the program! :)')
    # Add the arguments
    my_parser.add_argument('-hd', '--hardwareconnected', action='store',
                           type=str, required=False, default='False')
    my_parser.add_argument('-ot', '--offlinetesttime', action='store',
                           type=str, required=False, default=False)
    my_parser.add_argument('-pf', '--past_data_file_names', action='store',
                           type=str, required=False, default='Default_Past_Data')
    my_parser.add_argument('-c', '--config', action='store',
                           type=str, required=False, default='test_config.py')
    # Execute the parse_args() method
    args = my_parser.parse_args()
    return args


def load_config_from_args():
    args = parse_args()
    config, offline_test_time_duration = load_config(config_filename=args.config, offline_value=args.offlinetesttime,
                                                     hardware_connected=args.hardwareconnected)
    return config, offline_test_time_duration, args.past_data_file_names


def get_sync_detector(config: Type[ConfigurableConstants]):
    if config.DO_READ_SYNC:
        print('Creating sync detector')
        import gpiozero  # pylint: disable=import-error
        sync_detector = gpiozero.InputDevice(
            pin=constants.SYNC_PIN, pull_up=False)
        return sync_detector
    else:
        return None