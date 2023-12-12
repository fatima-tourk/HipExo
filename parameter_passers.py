import threading
from typing import Type
import config_util


class ParameterPasser(threading.Thread):
    def __init__(self,
                 lock: Type[threading.Lock],
                 config: Type[config_util.ConfigurableConstants],
                 quit_event: Type[threading.Event],
                 new_params_event: Type[threading.Event],
                 name='keyboard-input-thread'):
        '''This class passes parameters via user input and a parallel thread.

        The general idea is that this thread waits for an input, then grabs a lock (to stop the main thread),
        checks if the message follows the "code" (starts with 'v', ends with '!'), and then updates config
        params, depending on which params your child class wants updated. Then it sets the new_param_event flag
        to signal to the main loop to update the controllers'''
        super().__init__(name=name)
        self.daemon = True  # Thread property
        self.lock = lock
        self.config = config
        self.quit_event = quit_event
        self.new_params_event = new_params_event
        self.start()  # Starts the run() function

    # This run function overrides the run() function in threading.Thread
    def run(self):
        while True:
            msg = input()
            if msg == 'a':
                self.lock.acquire()
                self.new_params_event.set()
                self.lock.release()

            elif len(msg) < 3:
                print('Message must be either "quit" or a string of parameters'
                      ' starting with a letter (v for splines, k for stiffness,'
                      ' s for setpoint) and ending with an exclamation point)')

            elif msg.lower() == 'quit':
                print('Quitting')
                self.lock.acquire()
                self.quit_event.set()
                self.lock.release()
                break

            elif msg[-1] == '!':
                self.lock.acquire()
                first_letter = msg[0]
                msg_content = msg[1:-1]

                if first_letter == 'v':
                    param_list = [float(x) for x in msg_content.split(',')]
                    if len(param_list) != 6:
                        print('Must send six spline points with v<>! message')
                    else:
                        self.config.RISE_FRACTION = param_list[0]
                        self.config.PEAK_TORQUE = param_list[1]
                        self.config.PEAK_FRACTION = param_list[2]
                        self.config.FALL_FRACTION = param_list[3]
                elif first_letter == 'k':
                    if msg_content.isdigit():
                        self.config.K_VAL = int(msg_content)
                        self.config.B_VAL = self.config.B_RATIO * \
                            self.config.K_VAL  # 2.5ish = critically damped
                        print('k_val updated to: ', msg_content)
                    else:
                        print('Must provide single positive integer to update k_val')
                elif first_letter == 's':
                    if msg_content.lstrip('-').isdigit():
                        self.config.SET_POINT = int(msg_content)
                        print('SET_POINT updated to: ', msg_content)
                    else:
                        print('Must provide single integer to update SET_POINT')
                elif first_letter == 'p':
                    if msg_content.isdigit():
                        if 0 <= int(msg_content) <= 40:
                            self.config.PEAK_TORQUE = int(msg_content)
                            print('Peak torque set to: ',
                                  self.config.PEAK_TORQUE)
                    else:
                        print('Must provide single integer to update PEAK_TORQUE')
                elif first_letter == 'f':
                    param_list = [float(x) for x in msg_content.split(',')]
                    if msg_content.isdigit():
                        self.config.FLEXION_MAX_TORQUE = float(msg_content)
                        print('max flexion torque updated to: ', msg_content)
                    elif len(param_list) == 2:
                        self.config.FLEXION_MAX_TORQUE = param_list[0]
                        self.config.PEAK_FRACTION = param_list[1]
                    else:
                        print('Must provide single positive integer OR magnitude and timing to update max flexion torque')
                elif first_letter == 'e':
                    param_list = [float(x) for x in msg_content.split(',')]
                    if msg_content.isdigit():
                        self.config.EXTENSION_MIN_TORQUE = -1*float(msg_content)
                        print('min extension torque updated to: -', msg_content)
                    elif len(param_list) == 2:
                        self.config.EXTENSION_MIN_TORQUE = -1*param_list[0]
                        self.config.MIN_FRACTION = param_list[1]
                    else:
                        print('Must provide single positive integer OR magnitude and timing to update min extension torque')
                elif first_letter == 'c':
                    param_list = [float(x) for x in msg_content.split(',')]
                    if len(param_list) != 4:
                        print('Must send four spline points with c<>! message')
                    else:
                        self.config.FLEXION_MAX_TORQUE = param_list[0]
                        self.config.PEAK_FRACTION = param_list[1]
                        self.config.EXTENSION_MIN_TORQUE = -1*param_list[2]
                        self.config.MIN_FRACTION = param_list[3]
                elif first_letter == 't':
                    param_list = [float(x) for x in msg_content.split(',')]
                    if len(param_list) != 4:
                        print('Must send four spline points with t<>! message')
                    else:
                        self.config.PEAK_FRACTION = param_list[0]
                        self.config.FIRST_ZERO = param_list[1]
                        self.config.MIN_FRACTION = param_list[2]
                        self.config.SECOND_ZERO = param_list[3]
                        '''self.config.MIN_SCALED_START = param_list[0]
                        self.config.FIRST_ZERO = param_list[1]
                        self.config.PEAK_FRACTION = param_list[2]
                        self.config.SECOND_ZERO = param_list[3]
                        self.config.MIN_SCALED_END = param_list[4]'''
                elif first_letter == 'u':
                    param_list = [float(x) for x in msg_content.split(',')]
                    if len(param_list) != 8:
                        print('Must send four spline points with c<>! message')
                    else:
                        self.config.PEAK_FRACTION = param_list[0]
                        self.config.FIRST_ZERO = param_list[1]
                        self.config.MIN_FRACTION = param_list[2]
                        self.config.SECOND_ZERO = param_list[3]
                        self.config.FLEXION_MAX_TORQUE = param_list[4]
                        self.config.PEAK_FRACTION = param_list[5]
                        self.config.EXTENSION_MIN_TORQUE = -1*param_list[6]
                        self.config.MIN_FRACTION = param_list[7]
                        
                elif first_letter == '-':
                    self.config.EXPERIMENTER_NOTES = msg_content
                    print('Added that message to the config.')
                self.new_params_event.set()
                self.lock.release()

            else:
                print('I don\'t know how to interpret your message')
