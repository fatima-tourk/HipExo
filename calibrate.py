import os
import sys
import hip_exo
import time
import csv
import util
import constants


def calibrate_encoder_to_ankle_conversion(exo: hip_exo.Exo):
    '''This routine can be used to manually calibrate the relationship
    between ankle and motor angles. Move through the full RoM!!!'''
    exo.update_gains(Kp=constants.DEFAULT_KP, Ki=constants.DEFAULT_KI,
                     Kd=constants.DEFAULT_KD, ff=constants.DEFAULT_FF)
    exo.command_current(exo.motor_sign*2000)
    print('begin!')
    for _ in range(1000):
        time.sleep(0.02)
        exo.read_data()
        exo.write_data()
    print('Done! File saved.')


if __name__ == '__main__':
    exo_list = hip_exo.connect_to_exos(file_ID='calibration2')
    if len(exo_list) > 1:
        raise ValueError("Just turn on one exo for calibration")
    exo = exo_list[0]
    exo.standing_calibration()
    calibrate_encoder_to_ankle_conversion(exo=exo)
    exo.close()
