import controllers2
import unittest
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import hip_gait_state_estimators_test
from hip_exo import Exo
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# Set the log level for matplotlib to WARNING
logging.getLogger('matplotlib').setLevel(logging.WARNING)
class Test_PositionController(unittest.TestCase):

    def test_spline_controller(self):
        exo_instance = Exo(IS_HARDWARE_CONNECTED=False, dev_id=1234, max_allowable_current=10000)
        data=exo_instance.DataContainer()
        spline_controller = controllers2.HipSplineController(exo=exo_instance)
        # Create an instance of HipTestGaitEventDetectors
        gait_event_detectors = hip_gait_state_estimators_test.HipTestGaitEventDetectors()
        # Call the test_StrideAverageGaitPhaseEstimator method on the instance
        gait_phases = gait_event_detectors.test_StrideAverageGaitPhaseEstimator()
        desired_currents = []
        reset=True
        for gait_phase in gait_phases:
            print('before setting data.gait_phase', data.gait_phase)
            data.gait_phase = gait_phase
            print('after setting data.gait_phase', data.gait_phase)
            desired_currents.append(spline_controller.command(reset))
            reset=False
        #logging.debug('Code 1 exo_instance memory address: %s', id(exo_instance))
        print('Code 1 data_container memory address:', id(data))
        plt.plot(gait_phases)
        plt.plot(desired_currents)
        plt.show()

if __name__ == '__main__':
    unittest.main()
