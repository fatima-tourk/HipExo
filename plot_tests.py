import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV file and extract 'hip_angle' and 'gait_phase' columns
filename = 'exo_data/20230829_1335_all speeds angles no torque_LEFT.csv'
df = pd.read_csv(filename)

# Create a figure with two subplots stacked vertically
fig, (ax1, ax2, ax4, ax5) = plt.subplots(4, 1, figsize=(10, 6), sharex=True)
#fig, (ax1) = plt.subplots(1, 1, figsize=(10, 6), sharex=True)

# Plot 'hip_angle' on the first subplot
ax1.plot(df.loop_time, df.hip_angle, color='blue')
ax1.plot(df.loop_time, df.hip_angle_filtered, color='orange')
ax1.set_ylabel('Hip Angle')
ax1.set_title('Hip Angle vs. Time')
ax1.grid(True)

# Plot the true or false variable as a line whenever it's true
true_indices = df.index[df['did_toe_off']]
for index in true_indices:
    ax1.axvline(x=df.loc[index, 'loop_time'], color='green', linestyle='dashed', alpha=0.5)
    ax4.axvline(x=df.loc[index, 'loop_time'], color='green', linestyle='dashed', alpha=0.5)

ax1.legend()

# Plot 'gait_phase' on the second subplot
ax2.plot(df.loop_time, df.gait_phase, color='green')
ax2.set_ylabel('Gait Phase')
ax2.set_xlabel('Time')
ax2.grid(True)

'''# Plot 'commanded_current' on the third subplot
ax3.plot(df.loop_time, df.commanded_current, color='purple')
ax3.set_ylabel('Commanded Current')
ax3.set_xlabel('Time')
ax3.grid(True)'''

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

'''# Plot the accel_x on the sixth subplot
ax6.plot(df.loop_time, df.accel_x, color='red')
ax6.set_ylabel('accel_x')
ax6.set_xlabel('Time')
ax6.grid(True)

# Plot the accel_y on the sixth subplot
ax7.plot(df.loop_time, df.accel_y, color='red')
ax7.set_ylabel('accel_y')
ax7.set_xlabel('Time')
ax7.grid(True)

# Plot the accel_z on the sixth subplot
ax8.plot(df.loop_time, df.accel_z, color='red')
ax8.set_ylabel('accel_z')
ax8.set_xlabel('Time')
ax8.grid(True)

# Plot the gyro_x on the sixth subplot
ax9.plot(df.loop_time, df.gyro_x, color='red')
ax9.set_ylabel('gyro_x')
ax9.set_xlabel('Time')
ax9.grid(True)

# Plot the gyro_y on the sixth subplot
ax10.plot(df.loop_time, df.gyro_y, color='red')
ax10.set_ylabel('gyro_y')
ax10.set_xlabel('Time')
ax10.grid(True)

# Plot the gyro_z on the sixth subplot
ax11.plot(df.loop_time, df.gyro_z, color='red')
ax11.set_ylabel('gyro_z')
ax11.set_xlabel('Time')
ax11.grid(True)'''

# Adjust layout to prevent overlapping
plt.tight_layout()

# Show the plot
plt.show()
