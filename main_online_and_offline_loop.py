'''
This is the main GT program for running the Dephy exos. Read the Readme.
'''
import hip_exo
import threading
import controllers
import state_machines
import hip_gait_state_estimators
import constants
import filters
import time
import util
import config_util
import parameter_passers
import control_muxer
import plotters
import traceback
import offline_testing_file
import pandas as pd


#config, offline_test_time_duration, past_data_file_names = config_util.load_config_from_args()   # loads config from passed args
config, offline_test_time_duration= config_util.load_config(config_filename ='test_config.py', offline_value=None, hardware_connected='True')

IS_HARDWARE_CONNECTED = config.IS_HARDWARE_CONNECTED
print('Hardware connected: ', IS_HARDWARE_CONNECTED)
offline_data_left, offline_data_right = None, None
if not IS_HARDWARE_CONNECTED:
    offline_data_left, offline_data_right = offline_testing_file.get_offline_past_data_files(config.IS_HARDWARE_CONNECTED, past_data_file_names, offline_test_time_duration)

file_ID = input(
    'Other than the date, what would you like added to the filename?')

'''if sync signal is used, this will be gpiozero object shared between exos.'''
sync_detector = config_util.get_sync_detector(config)

'''Connect to Exos, instantiate Exo objects.'''
exo_list = hip_exo.connect_to_exos(IS_HARDWARE_CONNECTED,
    file_ID=file_ID, config=config, sync_detector=sync_detector, offline_data_left=offline_data_left, offline_data_right=offline_data_right)
if IS_HARDWARE_CONNECTED:
    print('Battery Voltage: ', 0.001*exo_list[0].get_batt_voltage(), 'V')
print(config.VARS_TO_PLOT)
config_saver = config_util.ConfigSaver(
    file_ID=file_ID, config=config)  # Saves config updates

'''Instantiate gait_state_estimator and state_machine objects, store in lists.'''
gait_state_estimator_list, state_machine_list = control_muxer.get_gse_and_sm_lists(
    exo_list=exo_list, config=config)

'''Prep parameter passing.'''
lock = threading.Lock()
quit_event = threading.Event()
new_params_event = threading.Event()
# v0.2,15,0.56,0.6!

input('Press any key to begin')
print('Start!')

'''Main Loop: Check param updates, Read data, calculate gait state, apply control, write data.'''
timer = util.FlexibleTimer(
    target_freq=config.TARGET_FREQ)  # attempts constants freq
t0 = time.perf_counter()
keyboard_thread = parameter_passers.ParameterPasser(
    lock=lock, config=config, quit_event=quit_event,
    new_params_event=new_params_event)
config_saver.write_data(loop_time=0)  # Write first row on config

iteration_count=0
while True:
    try:
        timer.pause()
        loop_time = time.perf_counter() - t0

        lock.acquire()
        if new_params_event.is_set():
            config_saver.write_data(loop_time=loop_time)  # Update config file
            for state_machine in state_machine_list:  # Make sure up to date
                state_machine.update_ctrl_params_from_config(config=config)
            for gait_state_estimator in gait_state_estimator_list:  # Make sure up to date
                gait_state_estimator.update_params_from_config(config=config)
            new_params_event.clear()
        if quit_event.is_set():  # If user enters "quit"
            break
        lock.release()

        for exo in exo_list:
            if not IS_HARDWARE_CONNECTED:
                if len(offline_data_left) < len(offline_data_right):
                    length=len(offline_data_left)
                else:
                    length=len(offline_data_right)
                # Check if there are more lines to read
                if iteration_count < length:
                    exo.read_data(loop_time=loop_time, iteration_count=iteration_count)
                    iteration_count += 1  # Increment the iteration count
                else:
                    # No more lines to read, break out of the loop
                    break
            else:
                exo.read_data(loop_time=loop_time)

        if not IS_HARDWARE_CONNECTED:    
            if iteration_count >= length:
                # Reached the end of the document, break out of the main loop
                break
        
        for gait_state_estimator in gait_state_estimator_list:
            gait_state_estimator.detect()
        if not config.READ_ONLY:
            for state_machine in state_machine_list:
                state_machine.step(read_only=config.READ_ONLY)
        for exo in exo_list:
            exo.write_data()

    except KeyboardInterrupt:
        print('Ctrl-C detected, Exiting Gracefully')
        break
    except Exception as err:
        print(traceback.print_exc())
        print("Unexpected error:", err)
        break

'''Safely close files, stop streaming, optionally saves plots'''
config_saver.close_file()
for exo in exo_list:
    exo.close()
if config.VARS_TO_PLOT:
    plotters.save_plot(filename=exo_list[0].filename.replace(
        '_LEFT.csv', '').replace('_RIGHT.csv', ''), vars_to_plot=config.VARS_TO_PLOT)

print('Done!!!')