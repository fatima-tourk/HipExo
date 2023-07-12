from typing import Type
import config_util
import state_machines
import hip_gait_state_estimators
import hip_exo
import filters
import controllers
import ml_util
import constants


def get_gse_and_sm_lists(exo_list, config: Type[config_util.ConfigurableConstants]):
    '''depending on config, uses exo list to create gait state estimator and state machine lists.'''
    gait_state_estimator_list = []
    state_machine_list = []
    if config.TASK == config_util.Task.WALKING:
        for exo in exo_list:
            toe_off_detector = hip_gait_state_estimators.HipToeOffDetector(
                maximum_angle=config.MAXIMUM_ANGLE,
                angle_filter=filters.Butterworth(N=config.HS_ANGLE_FILTER_N,
                                                Wn=config.HS_ANGLE_FILTER_WN,
                                                fs=config.TARGET_FREQ),
                delay=config.HS_ANGLE_DELAY)
            gait_phase_estimator = hip_gait_state_estimators.StrideAverageGaitPhaseEstimator(
                num_strides_required=config.NUM_STRIDES_REQUIRED)
            heel_strike_detector = hip_gait_state_estimators.GaitPhaseBasedHipHeelStrikeDetector(
                fraction_of_gait=config.HEEL_STRIKE_FRACTION)
            gait_state_estimator = hip_gait_state_estimators.GaitStateEstimator(
                side=exo.side,
                data_container=exo.data,
                heel_strike_detector=heel_strike_detector,
                gait_phase_estimator=gait_phase_estimator,
                toe_off_detector=toe_off_detector,
                do_print_toe_offs=config.PRINT_TO)
            gait_state_estimator_list.append(gait_state_estimator)

            # Define State Machine
            phase_controller = controllers.HipSplineController(
                exo=exo, min_fraction=config.MIN_FRACTION, first_zero=config.FIRST_ZERO, peak_fraction=config.PEAK_FRACTION,
                second_zero=config.SECOND_ZERO, start_torque=config.START_TORQUE, extension_min_torque=config.EXTENSION_MIN_TORQUE,
                flexion_max_torque=config.FLEXION_MAX_TORQUE)
            state_machine = state_machines.OneStateMachine(exo=exo, phase_controller=phase_controller)
            state_machine_list.append(state_machine)
    return gait_state_estimator_list, state_machine_list
