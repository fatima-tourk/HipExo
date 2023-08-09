import pandas as pd
import matplotlib.pyplot as plt
import config_util

# Read the CSV file and extract 'hip_angle' and 'gait_phase' columns
#filename = 'C:/Users/ft700/Documents/Shepherd Lab/Hip Exo Code/Exoboot_Code/HipExo/exo_data/20230718_1732_extended walking 2_LEFT.csv'
filename = 'exo_data/20230809_1225_plot filtered angle 2_LEFT.csv'
df = pd.read_csv(filename)

# Create a figure with two subplots stacked vertically
fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(10, 6), sharex=True)

# Plot 'hip_angle' on the first subplot
ax1.plot(df.loop_time, df.hip_angle, color='blue')
ax1.plot(df.loop_time, df.hip_angle_filtered, color='orange')
ax1.set_ylabel('Hip Angle')
ax1.set_title('Hip Angle vs. Time')
ax1.grid(True)  # Add gridlines to the first subplot
ax1.legend()

# Plot 'gait_phase' on the second subplot
ax2.plot(df.loop_time, df.gait_phase, color='green')
ax2.set_ylabel('Gait Phase')
ax2.set_xlabel('Time')
ax2.grid(True)

# Plot 'commanded_current' on the third subplot
ax3.plot(df.loop_time, df.commanded_current, color='purple')
ax3.set_ylabel('Commanded Current')
ax3.set_xlabel('Time')
ax3.grid(True)

# Plot 'commanded_torque' on the fourth subplot
ax4.plot(df.loop_time, df.commanded_torque, color='red')
ax4.set_ylabel('Commanded Torque')
ax4.set_xlabel('Time')
ax4.grid(True)

# Calculate the difference between consecutive values of df.loop_time
time_diff = df.loop_time.diff()

# Plot the difference on the sixth subplot
ax5.plot(df.loop_time, time_diff, color='magenta')
ax5.set_ylabel('Time Difference')
ax5.set_xlabel('Time')
ax5.grid(True)

# Adjust layout to prevent overlapping
plt.tight_layout()

# Show the plot
plt.show()
