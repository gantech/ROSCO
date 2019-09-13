# Copyright 2019 NREL

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

import numpy as np
from WTC_toolbox import turbine as wtc_turbine
from WTC_toolbox import control_interface as ci
import matplotlib.pyplot as plt
import sys

# Some useful constants
deg2rad = np.deg2rad(1)
rad2deg = np.rad2deg(1)
rpm2RadSec = 2.0*(np.pi)/60.0

class Sim():
    """
    Define interface to a given controller
    """

    def __init__(self, turbine, controller_int):
        """
        Setup the simulator
        """
        self.turbine = turbine
        self.controller_int = controller_int

        # TOTAL TEMPORARY HACK
        self.gb_eff = 0.95
        self.gen_eff = 0.95


    def sim_ws_series(self,t_array,ws_array,rotor_rpm_init=10,init_pitch=0.0):
        
        # Store some for conveniente
        dt = t_array[1] - t_array[0]
        R = self.turbine.RotorRad
        GBRatio = self.turbine.Ng


        # Declare output arrays
        pitch = np.ones_like(t_array) * init_pitch 
        rot_speed = np.ones_like(t_array) * rotor_rpm_init * rpm2RadSec # represent rot speed in rad / s
        gen_speed = np.ones_like(t_array) * rotor_rpm_init * GBRatio # represent gen speed in rad/s
        aero_torque = np.ones_like(t_array) * 1000.0
        gen_torque = np.ones_like(t_array) # * trq_cont(turbine_dict, gen_speed[0])
        gen_power = np.ones_like(t_array) * 0.0


        try: 
            self.turbine.cc_rotor.evaluate(ws_array[1], [rot_speed[0]/rpm2RadSec], 
                                                        [pitch[0]], 
                                                        coefficients=True)
            use_interpolated = False
        except: 
            use_interpolated = True
            print('CCBLADE Error -- attempting to use interpolated Cp, Ct, Cq, tables')

        # Loop through time
        for i, t in enumerate(t_array):
            if i == 0:
                continue # Skip the first run

            ws = ws_array[i]
            if use_interpolated:
                tsr = rot_speed[i-1] * self.turbine.RotorRad / ws
                cq = self.turbine.Cq.interp_surface([pitch[i-1]],tsr)
            if not use_interpolated:
                P, T, Q, M, Cp, Ct, cq, CM = self.turbine.cc_rotor.evaluate([ws], 
                                                        [rot_speed[i-1]/rpm2RadSec], 
                                                        [pitch[i-1]], 
                                                        coefficients=True)
            # try:
            #     P, T, Q, M, Cp, Ct, cq, CM = self.turbine.rotor.evaluate([ws], 
            #                                             [rot_speed[i-1]/rpm2RadSec], 
            #                                             [pitch[i-1]], 
            #                                             coefficients=True)
            # except:
            #     print('CC BLADE PROBLEM')
            #     e = sys.exc_info()[0]
            #     print(e)
            #     # carry through the past values and continue
            #     pitch[i] = pitch[i-1]
            #     rot_speed[i] = rot_speed[i-1]
            #     gen_speed[i] = gen_speed[i-1]
            #     aero_torque[i] = aero_torque[i-1]
            #     gen_torque[i] = gen_torque[i-1]
            #     gen_power[i] = gen_power[i-1]
            #     continue

            aero_torque[i] = 0.5 * self.turbine.rho * (np.pi * R**2) * cq * R * ws**2

            # # Save these values for plotting
            # cq_array[i] = cq
            # cp_array[i] = Cp[0]
            # ct_array[i] = Ct[0]
            # tsr_array[i] = tsr

            # Update the rotor speed and generator speed
            rot_speed[i] = rot_speed[i-1] + (dt/self.turbine.J)*(aero_torque[i] * self.gb_eff - self.turbine.Ng * gen_torque[i-1])
            gen_speed[i] = rot_speed[i] * self.turbine.Ng 

            # Call the controller
            gen_torque[i], pitch[i] = self.controller_int.call_controller(t,dt,pitch[i-1],gen_speed[i],rot_speed[i],ws)

            # Calculate the power
            gen_power[i] = gen_speed[i] * np.pi/30.0 * gen_torque[i] * self.gen_eff

        # Save these values
        self.pitch = pitch
        self.rot_speed = rot_speed
        self.gen_speed = gen_speed
        self.aero_torque = aero_torque
        self.gen_torque = gen_torque
        self.gen_power = gen_power
        self.t_array = t_array
        self.ws_array = ws_array


        fig, axarr = plt.subplots(4,1,sharex=True,figsize=(6,10))



        ax = axarr[0]
        ax.plot(self.t_array,self.ws_array,label='Wind Speed')
        ax.grid()
        ax.legend()

        ax = axarr[1]
        ax.plot(self.t_array,self.rot_speed,label='Rot Speed')
        ax.grid()
        ax.legend()

        ax = axarr[2]
        ax.plot(self.t_array,self.gen_torque,label='Gen Torque')
        ax.grid()
        ax.legend()

        ax = axarr[3]
        ax.plot(self.t_array,self.pitch,label='Bld Pitch')
        ax.grid()
        ax.legend()
        