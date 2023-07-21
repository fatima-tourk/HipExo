import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV file and extract 'hip_angle' and 'gait_phase' columns
filename = 'C:/Users/ft700/Documents/Shepherd Lab/Hip Exo Code/Exoboot_Code/HipExo/exo_data/20230718_1732_extended walking 2_LEFT.csv'
data = pd.read_csv(filename)
hip_angle = data['hip_angle']
gait_phase = data['gait_phase']

# Create a figure with two subplots stacked vertically
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

# Plot 'hip_angle' on the first subplot
ax1.plot(hip_angle, color='blue')
ax1.set_ylabel('Hip Angle (degrees)')
ax1.set_title('Hip Angle vs. Time')
ax1.grid(True)  # Add gridlines to the first subplot

# Plot 'gait_phase' on the second subplot
ax2.plot(gait_phase, color='green')
ax2.set_ylabel('Gait Phase')
ax2.set_xlabel('Time')
ax2.grid(True)

# Adjust layout to prevent overlapping
plt.tight_layout()

# Show the plot
plt.show()
