from scipy import interpolate
import matplotlib.pyplot as plt
import numpy as np

'''https://www.cambridge.org/core/journals/wearable-technologies/article/
comparing-optimized-exoskeleton-assistance-of-the-hip-knee-and-ankle-in-single-and-multijoint
-configurations/9FBC1580F11614B388BE621D716800AD
figure 4'''

another_min = 0.05
min_fraction = 0.12
first_zero = 0.37
peak_fraction = 0.66
second_zero = 0.95
spline_x = [0, another_min, min_fraction, first_zero, peak_fraction, second_zero, 1]
#spline_x = [0, first_zero, peak_fraction, second_zero, min_fraction,1]
start = -0.15
extension_min = -0.4
zero = 0
flexion_peak = 0.25
#spline_y = [start, extension_min, zero, flexion_peak, zero, start]
spline_y = [0, flexion_peak, 0, 0.9*extension_min, extension_min, 0.9*extension_min,0]
spline = interpolate.pchip(spline_x, spline_y, extrapolate=False)

# Evaluate the spline over a range of x-values
x_values = np.linspace(0, 1, 100)  # Adjust the number of points as needed
y_values = spline(x_values)

plt.plot(x_values, y_values)

# Customize the plot
plt.xlabel('x')
plt.ylabel('y')
plt.title('Spline Function')
plt.show()
