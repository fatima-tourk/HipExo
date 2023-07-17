import hip_exo
import config_util
import util
import time
import parameter_passers
import threading

config, offline_test_time_duration= config_util.load_config(config_filename ='test_config.py', offline_value=None, hardware_connected='True')

IS_HARDWARE_CONNECTED = config.IS_HARDWARE_CONNECTED
print('hardware connected: ',IS_HARDWARE_CONNECTED)
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
        print('Stand still to get hip zero position')
        input('Press enter to start')
        exo.hip_standing_calibration(config=config, max_seconds_to_calibrate= 2)
        print('Hip zero position acquired!', config.HIP_ZERO_POSITION)
config_saver = config_util.ConfigSaver(
    file_ID=file_ID, config=config)  # Saves config updates

input('Press any key to begin')
print('Start!')



timer = util.FlexibleTimer(
    target_freq=config.TARGET_FREQ)  # attempts constants freq
t0 = time.perf_counter()
config_saver.write_data(loop_time=0)  # Write first row on config

#Select controller
print('What controller would you like to use?')
print('0: no controller \n 1: current \n 2: voltage \n 3: motor angle \n 4: impedance \n 5: torque')
controller = int(input('Enter the number of the controller you would like to use'))
while True:
    try:
        timer.pause()
        loop_time = time.perf_counter() - t0

        for exo in exo_list:
            print()
            # Enter input values for chosen controller
            if controller==0:
                print('no controller selected, reading data only')
            elif controller==1:
                desired_mA = int(input('Enter desired current in mA'))
                exo.command_current(desired_mA=desired_mA)
            elif controller==2:
                desired_mV = int(input('Enter desired voltage in mV'))
                exo.command_voltage(desired_mV=desired_mV)
            elif controller==3:
                desired_motor_angle = int(input('Enter desired motor angle'))
                exo.command_motor_angle(desired_motor_angle=desired_motor_angle)
            elif controller==4:
                theta0 = int(input('Enter theta0'))
                k_val = int(input('Enter k value'))
                b_val= int(input('Enter b value'))
                exo.command_impedance(theta0=theta0, k_val=k_val, b_val=b_val)
            elif controller==5:
                desired_torque = float(input('Enter desired torque in Nm'))
                exo.command_motor_torque(desired_torque=desired_torque)
            
            # Read and write exo data
            exo.read_data(loop_time=loop_time)
            hip_angle = exo.motor_angle_to_hip_angle(config=config)
            print('motor angle', exo.data.motor_angle, 'hip_angle: ', hip_angle, 'at time: ', loop_time)
            print('hip angle table', exo.data.hip_angle)
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