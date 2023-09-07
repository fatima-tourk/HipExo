import numpy as np
from scipy import interpolate
import constants



def calculate_rms_current(spline_x, spline_y):
    torque_points = np.array(spline_y) / constants.MOTOR_CURRENT_TO_MOTOR_TORQUE

    spline_function = interpolate.PchipInterpolator(spline_x, torque_points, extrapolate=False)
    time_samples = np.linspace(spline_x[0], spline_x[-1], num=1000)
    torque_samples = spline_function(time_samples)

    squared_currents = torque_samples * constants.MOTOR_CURRENT_TO_MOTOR_TORQUE
    rms_current = np.sqrt(np.mean(np.square(squared_currents)))

    return rms_current

# Example spline x and y values
spline_x = [0, 0.12, 0.4, 0.75, 0.9, 1]
spline_y = [0, 14, 0, -10, 0, 0]

rms_current = calculate_rms_current(spline_x, spline_y)
print("RMS Current:", rms_current)
