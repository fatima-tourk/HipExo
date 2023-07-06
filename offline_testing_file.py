import pandas as pd
import os

def get_offline_past_data_files(IS_HARDWARE_CONNECTED, past_data_file_names, offline_test_time_duration):

    if not IS_HARDWARE_CONNECTED:
        print('''
Offline Testing Detected.
''')
        if (str(past_data_file_names) + '_LEFT.csv' in list(os.listdir())) and (str(past_data_file_names) + '_RIGHT.csv' in list(os.listdir())):
            print('Using Files: ' +  str(past_data_file_names) + '_LEFT.csv and ' + str(past_data_file_names) + '_RIGHT.csv\n')
            offline_data_left= pd.read_csv(str(past_data_file_names) + '_LEFT.csv')
            offline_data_right = pd.read_csv(str(past_data_file_names) + '_RIGHT.csv')
        else:
            # print('''No Files found by given name.''')
            raise ValueError('Past Filenames passed as arguments not found in local directory.')
    else:
        if offline_test_time_duration:
            print('Offline Test Duration argument will not be considered, since hardware is connected.')
        offline_data_left = None
        offline_data_right = None

    return offline_data_left, offline_data_right
