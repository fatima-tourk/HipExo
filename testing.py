import hip_exo
import config_util
import util
import time
import parameter_passers
import threading
import control_muxer
import traceback
import constants
import offline_testing_file

config, offline_test_time_duration= config_util.load_config(config_filename ='test_config.py', offline_value=None, hardware_connected='True')

IS_HARDWARE_CONNECTED = config.IS_HARDWARE_CONNECTED
offline_data_left, offline_data_right = None, None

file_ID = input(
    'Other than the date, what would you like added to the filename?')

'''if sync signal is used, this will be gpiozero object shared between exos.'''
sync_detector = config_util.get_sync_detector(config)

'''Connect to Exos, instantiate Exo objects.'''
exo_list = hip_exo.connect_to_exos(IS_HARDWARE_CONNECTED,
    file_ID=file_ID, config=config, sync_detector=sync_detector, offline_data_left=offline_data_left, offline_data_right=offline_data_right)
if IS_HARDWARE_CONNECTED:
    print('Battery Voltage: ', 0.001*exo_list[0].get_batt_voltage(), 'V')
    for exo in exo_list:
        exo.hip_standing_calibration(config=config, max_seconds_to_calibrate= 2)
        print('Hip zero position acquired!', config.HIP_ZERO_POSITION)
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



timer = util.FlexibleTimer(
    target_freq=constants.TARGET_FREQ)  # attempts constants freq
print(constants.TARGET_FREQ)
t0 = time.perf_counter()
'''keyboard_thread = parameter_passers.ParameterPasser(
    lock=lock, config=config, quit_event=quit_event,
    new_params_event=new_params_event)'''
config_saver.write_data(loop_time=0)  # Write first row on config


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
            # Read exo data
            exo.read_data(loop_time=loop_time)
            hip_angle = exo.motor_angle_to_hip_angle(config=config)
            print('hip angle', exo.data.hip_angle)
        
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
    exo.command_controller_off()
    exo.close()
if config.VARS_TO_PLOT:
    plotters.save_plot(filename=exo_list[0].filename.replace(
        '_LEFT.csv', '').replace('_RIGHT.csv', ''), vars_to_plot=config.VARS_TO_PLOT)

print('Done!!!')