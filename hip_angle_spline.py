import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline

def generate_hip_angle():
    # Define parameters
    cycle_duration = 1.0  # Duration of each gait cycle in seconds
    num_cycles = 10  # Number of cycles to repeat
    total_duration = cycle_duration * num_cycles
    sampling_rate = 100  # Number of samples per second

    # Generate time vector for one gait cycle
    t_cycle = np.linspace(0, cycle_duration, int(cycle_duration * sampling_rate))

    # Generate hip angle values for one gait cycle
    hip_angle_cycle = np.zeros_like(t_cycle)

    # Calculate corresponding sample indices based on percentages of the gait cycle
    start_index = 0
    end_index_1 = int(0.05 * len(t_cycle)) - 1
    end_index_2 = int(0.3 * len(t_cycle)) - 1
    end_index_3 = int(0.6 * len(t_cycle)) - 1
    end_index_4 = int(0.8 * len(t_cycle)) - 1
    end_index_5 = int(0.9 * len(t_cycle)) - 1
    end_index_6 = len(t_cycle) - 1

    # Set the desired angles for each phase of the gait cycle
    angle_1 = 15.0
    angle_2 = 12.5
    angle_3 = 0
    angle_4 = -15.5
    angle_5 = 15.0
    angle_6 = 15.0

    # Assign time and angle values for each phase of the gait cycle
    interpolation_x = [t_cycle[start_index], t_cycle[end_index_1], t_cycle[end_index_2], t_cycle[end_index_3], t_cycle[end_index_4], t_cycle[end_index_5], t_cycle[end_index_6]]
    interpolation_y = [angle_1, angle_2, angle_3, angle_4, angle_5, angle_6, angle_6]

    # Interpolate the hip angle values for one gait cycle using cubic spline
    cs = CubicSpline(interpolation_x, interpolation_y)
    hip_angle_cycle = cs(t_cycle)

    # Repeat the hip angle values for the desired number of cycles
    hip_angle = np.tile(hip_angle_cycle, num_cycles)

    # Generate time vector for the total duration
    t = np.linspace(0, total_duration, len(hip_angle))

    '''# Plot the hip angle
    plt.plot(t, hip_angle)
    plt.xlabel('Time (s)')
    plt.ylabel('Hip Angle (degrees)')
    plt.title('Hip Flexion and Extension Angle during Gait Cycle')
    plt.show()'''

    return hip_angle

generate_hip_angle()
