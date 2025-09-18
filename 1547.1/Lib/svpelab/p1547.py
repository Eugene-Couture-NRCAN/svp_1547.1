"""
Copyright (c) 2018, Sandia National Labs, SunSpec Alliance and CanmetENERGY(Natural Resources Canada)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

Neither the names of the Sandia National Labs, SunSpec Alliance and CanmetENERGY(Natural Resources Canada)
nor the names of its contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Questions can be directed to support@sunspec.org
"""

import os
import xml.etree.ElementTree as ET
import csv
import math
import xlsxwriter
import traceback
from datetime import datetime, timedelta
from collections import OrderedDict
import time
import collections
import numpy as np
import pandas as pd
import random
import pylab
from matplotlib import lines
from matplotlib.lines import Line2D
import timeit
import matplotlib.gridspec as gridspec
# import sys
# import os
# import glob
# import importlib

VERSION = '1.4.3'
LATEST_MODIFICATION = '13th January 2020'

FW  = 'FW'   # Frequency-Watt
CPF = 'CPF'  # Constant Power Factor
VW  = 'VW'   # Volt_Watt
VV  = 'VV'   # Volt-Var
WV  = 'WV'   # Watt-Var
CRP = 'CRP'  # Constant Reactive Power
LAP = 'LAP'  # Limit Active Power
PRI = 'PRI'  # Priority
IOP = 'IOP'  # Interoperability Tests
UI  = 'UI'   # Unintentional Islanding Tests

LV = 'LV'
HV = 'HV'
CAT_2 = 'CAT_2'
CAT_3 = 'CAT_3'
VOLTAGE = 'V'
FREQUENCY = 'F'
FULL_NAME = {'V': 'Voltage',
             'P': 'Active Power',
             'Q': 'Reactive Power',
             'F': 'Frequency',
             'PF': 'Power Factor'}
LFRT = "LFRT"  # Low Frequency Ride Through
HFRT = "HFRT"  # High Frequency Ride Through


class p1547Error(Exception):
    pass


"""
This section is for EUT parameters needed such as V, P, Q, etc.
"""

def VersionValidation(script_version):
    """ 
    Verify the validity of the script version

    Parameters
    ----------
        script_version : str
            version of the script
    """
    if script_version != VERSION:
        raise p1547Error(f'Error in p1547 library version is {VERSION} while script version is {script_version}.'
                         f'Update library and script version accordingly.')


class EutParameters(object):
    """
    A class to represent Equipment Under Test (EUT) parameters.

    
    ATTRIBUTES
    ----------
    
    - ts (object)             : Test script object containing parameter values
    - v_nom (float)           : Nominal voltage of the EUT
    - s_rated (float)         : Rated apparent power of the EUT
    - v_high (float)          : High voltage limit of the EUT
    - v_low (float)           : Low voltage limit of the EUT
    - MRA (dict)              : Minimum Required Accuracy for various parameters
    - MRA_V_trans (float)     : Minimum Required Accuracy for transient voltage measurements
    - MRA_F_trans (float)     : Minimum Required Accuracy for transient frequency measurements
    - MRA_T_trans (float)     : Minimum Required Accuracy for transient time measurements
    - f_nom (float)           : Nominal frequency of the EUT
    - f_max (float)           : Maximum frequency of the EUT
    - f_min (float)           : Minimum frequency of the EUT
    - phases (int)            : Number of phases of the EUT
    - p_rated (float)         : Rated active power of the EUT
    - p_rated_prime (float)   : Rated absorption power of the EUT
    - p_min (float)           : Minimum active power of the EUT
    - var_rated (float)       : Rated reactive power of the EUT
    - absorb (bool)           : Flag indicating if absorption is enabled for the EUT
    """

    def __init__(self, ts):
        """
        Initializes the EutParameters object with the given test script object.

        Parameters
        ----------
        - ts  (object)    : Test script object containing parameter values
        """
        self.ts = ts
        try:
            self.v_nom = ts.param_value('eut.v_nom')
            self.s_rated = ts.param_value('eut.s_rated')
            self.v_high = ts.param_value('eut.v_high')
            self.v_low = ts.param_value('eut.v_low')

            '''
            Minimum required accuracy (MRA) (per Table 3 of IEEE Std 1547-2018)

            Table 3 - Minimum measurement and calculation accuracy requirements for manufacturers
            ______________________________________________________________________________________________
            Time frame                  Steady-state measurements      
            Parameter       Minimum measurement accuracy    Measurement window      Range
            ______________________________________________________________________________________________        
            Voltage, RMS    (+/- 1% Vnom)                   10 cycles               0.5 p.u. to 1.2 p.u.
            Frequency       10 mHz                          60 cycles               50 Hz to 66 Hz
            Active Power    (+/- 5% Srated)                 10 cycles               0.2 p.u. < P < 1.0
            Reactive Power  (+/- 5% Srated)                 10 cycles               0.2 p.u. < Q < 1.0
            Time            1% of measured duration         N/A                     5 s to 600 s 
            ______________________________________________________________________________________________
                                        Transient measurements
            Parameter       Minimum measurement accuracy    Measurement window      Range
            Voltage, RMS    (+/- 2% Vnom)                   5 cycles                0.5 p.u. to 1.2 p.u.
            Frequency       100 mHz                         5 cycles                50 Hz to 66 Hz
            Time            2 cycles                        N/A                     100 ms < 5 s
            ______________________________________________________________________________________________
            '''
            self.MRA = {
                'V': 0.01 * self.v_nom,
                'Q': 0.05 * ts.param_value('eut.s_rated'),
                'P': 0.05 * ts.param_value('eut.s_rated'),
                'F': 0.01,
                'T': 0.01,
                'PF': 0.01
            }

            self.MRA_V_trans = 0.02 * self.v_nom
            self.MRA_F_trans = 0.1
            self.MRA_T_trans = 2. / 60.

            if ts.param_value('eut.f_nom'):
                self.f_nom = ts.param_value('eut.f_nom')
            else:
                self.f_nom = None

            if ts.param_value('eut.f_max'):
                self.f_max = ts.param_value('eut.f_max')
            else:
                self.f_max = None
            if ts.param_value('eut.f_min'):
                self.f_min = ts.param_value('eut.f_min')
            else:
                self.f_min = None

            if ts.param_value('eut.phases') is not None:
                self.phases = ts.param_value('eut.phases')
            else:
                self.phases = None
            if ts.param_value('eut.p_rated') is not None:
                self.p_rated = ts.param_value('eut.p_rated')
                self.p_rated_prime = ts.param_value('eut.p_rated_prime')  # absorption power
                if self.p_rated_prime is None:
                    self.p_rated_prime = -self.p_rated
                self.p_min = ts.param_value('eut.p_min')
                self.var_rated = ts.param_value('eut.var_rated')
            else:
                self.var_rated = None
            # self.imbalance_angle_fix = imbalance_angle_fix
            self.absorb = ts.param_value('eut.abs_enabled')

        except Exception as e:
            self.ts.log_error('Incorrect Parameter value : %s' % e)
            raise


"""
This section is utility function needed to run the scripts such as data acquisition.
"""


class UtilParameters:
    """
    A class to represent utility parameters for test scripts.

    Attributes
    ----------
    - step_label (int)                      : ASCII value of the current step label
    - pwr (float)                           : Power level, default is 1.0 (100%)
    - max_pwr_lim (float)                   : Max power level in percentage, default is 100%
    - curve (int)                           : Current curve number, default is 1
    - filename (str or None)                : Name of the file being processed
    - double_letter_label (bool or None)    : Flag to indicate if step labels should use double letters
    - script_complete_name (str)            : Complete name of the script, default is 'UNDEFINED IN TEST CLASS'


    Methods
    -------
    reset_curve(curve=1):
        Reset the curve number and log the change
    reset_pwr(pwr=1.0):
        Reset the power level and log the change
    reset_filename(filename):
        Reset the filename
    set_step_label(starting_label=None):
        Set the step label
    get_params(function, curve=None):
        Get parameters for a specific function and curve
    get_step_label():
        Get the current step label and increment it
    get_script_name():
        Get the complete script name
    """

    def __init__(self):
        """
        Initialize the UtilParameters object with default values.
        """
        self.step_label = None
        self.pwr = 1.0
        self.max_pwr_lim = 100
        self.curve = 1
        self.filename = None
        self.double_letter_label = None
        self.script_complete_name = 'UNDEFINED IN TEST CLASS'

    def reset_curve(self, curve=1):
        """
        Reset the curve number and log the change.

        Parameters
        ----------
        - curve (int, optional)   : New curve number (default is 1)
        """
        self.curve = curve
        self.ts.log_debug(f'P1547 Librairy curve has been set {curve}')

    def reset_pwr(self, pwr=1.0):
        """
        Reset the power level and log the change.

        Parameters
        ----------
        - pwr (float, optional)   : New power level (default is 1.0, representing 100%)
        """
        self.pwr = pwr
        self.ts.log(f'P1547 Librairy power level has been set {round(pwr * 100)}%')

    def reset_max_pwr_lim(self, max_pwr_lim=100):
        """
        Reset the max power limit and log the change.

        Parameters
        ----------
        - max_pwr_lim (float, optional)   : New maximum power limit (default is 1.0, representing 100%)
        """
        self.max_pwr_lim = max_pwr_lim
        self.ts.log(f'P1547 Librairy power level has been set {round(max_pwr_lim)}%')

    def reset_filename(self, filename):
        """
        Reset the filename.

        Parameters
        ----------
        - filename (str) :  New filename
        """
        self.filename = filename

    def set_step_label(self, starting_label=None):
        """
        Set the initial step label.

        Parameters
        ----------
        - starting_label  (str, optional)  : Starting label (default is None, which sets it to 'A')
        """
        self.double_letter_label = False

        if starting_label is None:
            starting_label = 'a'
        starting_label_value = ord(starting_label)
        self.step_label = starting_label_value

    """
    Getter functions
    """
    def get_params(self, function, curve=None):
        """
        Get parameters for a specific function and curve.

        Parameters
        ----------
        - function (str)        : The function to get parameters for
        - curve (int, optional)   :  The curve number (default is None, which uses the current curve)

        Returns
        -------
        dict
            Parameters for the specified function and curve
        """

        if curve is None:
            return self.param[function]
        else:
            return self.param[function][self.curve]

    def get_step_label(self):
        """
        Get the current step label and increment it.

        Returns
        -------
        str
            The current step label
        """ 
        if self.step_label > 90:
            self.step_label = ord('A')
            self.double_letter_label = True

        if self.double_letter_label:
            step_label = 'Step {}{}'.format(chr(self.step_label), chr(self.step_label))
        else:
            step_label = 'Step {}'.format(chr(self.step_label))

        self.step_label += 1
        return step_label

    def get_script_name(self):
        """
        Get the complete script name.

        Returns
        -------
        str
            The complete script name
        """
        if self.script_complete_name is None:
            self.script_complete_name = 'Script name not initialized'
        return self.script_complete_name


class DataLogging:
    """
    A class for handling data logging and analysis in power systems testing.

    This class manages measurement types, criteria, and time-based data collection
    for power system equipment testing.

    Attributes
    ----------
    - type_meas (dict) : Dictionary mapping measurement types to their corresponding AC measurement labels
    - rslt_sum_col_name (str) : Column names for the result summary
    - sc_points (dict) : Dictionary of points to be recorded by the data acquisition system
    - tr (float) : Time response setting in seconds
    - n_tr (int) : Number of time response cycles
    - initial_value (dict) : Initial values of measurements
    - tr_value (OrderedDict) : Time response values collected during the test
    - current_step_label (str) : Current step label in the test procedure

    Methods
    -------
    reset_time_settings(tr, number_tr=2)
        Reset the time response settings.
    set_sc_points()
        Set up the points to be recorded by the data acquisition system.
    set_result_summary_name()
        Set up the column names for the result summary file.
    get_rslt_param_plot()
        Get parameters for plotting results.
    get_sc_points()
        Get the points to be recorded by the data acquisition system.
    get_measurement_label(type_meas)
        Get the measurement label for a given measurement type.
    get_measurement_total(type_meas, log=False)
        Calculate the total or average measurement across all phases.
    get_rslt_sum_col_name()
        Get the column names for the result summary.
    write_rslt_sum()
        WritF a summary of results for the current step.
    start(step_label)
        Start data collection for a new step.
    record_timeresponse()
        Record time-based response data.
    """

    # def __init__(self, meas_values, x_criteria, y_criteria):
    def __init__(self):
        """
        Initialize the DataLogging object with default values.
        """
        self.type_meas = {'V': 'AC_VRMS', 'I': 'AC_IRMS', 'P': 'AC_P', 'Q': 'AC_Q', 'VA': 'AC_S',
                          'F': 'AC_FREQ', 'PF': 'AC_PF'}
        # Values to be recorded
        # self.meas_values = meas_values
        # Values defined as target/step values which will be controlled as step
        # self.x_criteria = x_criteria
        # Values defined as values which will be controlled as step
        # self.y_criteria = y_criteria
        self.rslt_sum_col_name = ''
        self.sc_points = {}
        # self._config()
        self.set_sc_points()
        self.set_result_summary_name()
        self.tr = None
        self.n_tr = None
        self.initial_value = {}
        self.tr_value = collections.OrderedDict()
        self.current_step_label = None
        self.daq = None

    # def __config__(self):

    def reset_time_settings(self, tr, number_tr=2):
        """
        Reset the time response settings.

        Parameters
        ----------
        - tr (float)                : Time response in seconds.
        - number_tr (int, optional) : Number of time response cycles (default is 2).
        """
        self.tr = tr
        self.ts.log_debug(f'P1547 Time response has been set to {self.tr} seconds')
        self.n_tr = number_tr
        #self.ts.log_debug(f'P1547 Number of Time response has been set to {self.n_tr} cycles')

    def set_daq(self, daq):
        """
        Sets the data aquisition device
        """
        self.daq = daq

    def set_sc_points(self):
        """
        Set up the points to be recorded by the data acquisition system (DAS).

        This method configures the data points that will be collected and stored
        during the test procedure.
        """
        # TODO : The target value are in percentage (0-100) and something in P.U. (0-1.0)
        #       The measure value are in absolute value

        xs = self.x_criteria
        ys = self.y_criteria
        row_data = []

        for meas_value in self.meas_values:


            if meas_value in xs:
                row_data.append('%s_TARGET' % meas_value)

            elif meas_value in ys:
                row_data.append('%s_TARGET' % meas_value)
                row_data.append('%s_TARGET_MIN' % meas_value)
                row_data.append('%s_TARGET_MAX' % meas_value)

            row_data.append('%s_MEAS' % meas_value)

        row_data.append('event')
        self.ts.log_debug('Sc points: %s' % row_data)
        self.sc_points['sc'] = row_data

    def set_result_summary_name(self):
        """
        Set up the column names for the result summary file.

        This method creates a comma-separated string of column names that will
        be used in the results summary file.
        """
        xs = self.x_criteria
        ys = self.y_criteria
        row_data = []

        # Time response criteria will take last placed value of Y variables
        if self.criteria_mode[0]:  # transient response pass/fail
            row_data.append('90%_BY_TR=1')
        if self.criteria_mode[1]:
            row_data.append('WITHIN_BOUNDS_BY_TR=1')
        if self.criteria_mode[2]:  # steady-state accuracy
            row_data.append('WITHIN_BOUNDS_BY_LAST_TR')

        for meas_value in self.meas_values:
            row_data.append('%s_MEAS' % meas_value)

            if meas_value in xs:
                row_data.append('%s_TARGET' % meas_value)

            elif meas_value in ys:
                row_data.append('%s_TARGET' % meas_value)
                row_data.append('%s_TARGET_MIN' % meas_value)
                row_data.append('%s_TARGET_MAX' % meas_value)

        row_data.append('STEP')
        row_data.append('FILENAME')

        self.rslt_sum_col_name = ','.join(row_data) + '\n'
        self.ts.log_debug(f'summary column={self.rslt_sum_col_name}'.rstrip())

    def get_rslt_param_plot(self):
        """
        Get parameters for plotting results.

        Returns
        -------
        dict
            A dictionary containing plot parameters including titles, axis labels,
            and data points to be plotted.
        """
        y_variables = self.y_criteria
        y2_variables = self.x_criteria

        # For VV, VW and FW
        y_points = []
        y2_points = []
        y_title = []
        y2_title = []

        # y_points = '%s_TARGET,%s_MEAS' % (y, y)
        # y2_points = '%s_TARGET,%s_MEAS' % (y2, y2)
        self.ts.log_debug(f'y_variables={y_variables}')
        for y in y_variables:
            self.ts.log_debug('y_temp: %s' % y)
            # y_temp = self.get_measurement_label('%s' % y)
            y_temp = '{}'.format(','.join(str(x) for x in self.get_measurement_label('%s' % y)))
            y_title.append(FULL_NAME[y])
            y_points.append(y_temp)
        self.ts.log_debug('y_points: %s' % y_points)
        y_points = ','.join(y_points)
        y_title = ','.join(y_title)

        for y2 in y2_variables:
            self.ts.log_debug('y2_variable for result: %s' % y2)
            y2_temp = '{}'.format(','.join(str(x) for x in self.get_measurement_label('%s' % y2)))
            y2_title.append(FULL_NAME[y2])
            y2_points.append(y2_temp)
        y2_points = ','.join(y2_points)
        y2_title = ','.join(y2_title)

        result_params = {
            'plot.title': 'title_name',
            'plot.x.title': 'Time (sec)',
            'plot.x.points': 'TIME',
            'plot.y.points': y_points,
            'plot.y.title': y_title,
            'plot.y2.points': y2_points,
            'plot.y2.title': y2_title,
            'plot.%s_TARGET.min_error' % y: '%s_TARGET_MIN' % y,
            'plot.%s_TARGET.max_error' % y: '%s_TARGET_MAX' % y,
        }

        return result_params

    def get_sc_points(self):
        """
        Get the points to be recorded by the data acquisition system.

        Returns
        -------
        dict
            A dictionary of points to be recorded by the data acquisition system.
        """
        return self.sc_points

    def get_measurement_label(self, type_meas):
        """
        Get the measurement label for a given measurement type.

        Parameters
        ----------
        - type_meas (str) : Measurement type ('V', 'I', 'P', 'Q', 'PF', 'F' or 'VA'). 

        Returns
        -------
        list of str
            List of measurement labels for the given type and phase configuration,   e.g. ['AC_VRMS_1', 'AC_VRMS_2', 'AC_VRMS_3'].
        """
        meas_root = self.type_meas[type_meas]
        if self.phases.lower() == 'single phase':
            meas_label = [meas_root + '_1']
        elif self.phases.lower() == 'split phase':
            meas_label = [meas_root + '_1', meas_root + '_2']
        elif self.phases.lower() == 'three phase':
            meas_label = [meas_root + '_1', meas_root + '_2', meas_root + '_3']

        return meas_label

    def get_measurement_total(self, type_meas, log=False):
        """
        Get the total or average measurement across all phases.

        Parameters
        ----------
        - type_meas (str)       :    Measurement type to calculate ('V', 'I', 'P', 'Q', 'PF', 'F' or 'VA'). 
        - log (bool, optional)  :   Whether to log debug information (default is False).

        Returns
        -------
        float
            Total or average measurement value.
        """
        value = None
        nb_phases = None

        self.data = self.daq.data_capture_read()

        self.ts.log_debug(self.data.get(self.get_measurement_label(type_meas)[0]))
        try:
            if self.phases == 'Single phase':
                value = self.data.get(self.get_measurement_label(type_meas)[0])
                if log:
                    self.ts.log_debug('        %s are: %s'
                                      % (self.get_measurement_label(type_meas), value))
                nb_phases = 1

            elif self.phases == 'Split phase':
                value1 = self.data.get(self.get_measurement_label(type_meas)[0])
                value2 = self.data.get(self.get_measurement_label(type_meas)[1])
                if log:
                    self.ts.log_debug('        %s are: %s, %s'
                                      % (self.get_measurement_label(type_meas), value1, value2))
                value = value1 + value2
                nb_phases = 2

            elif self.phases == 'Three phase':
                # self.ts.log_debug(f'type_meas={type_meas}')
                value1 = self.data.get(self.get_measurement_label(type_meas)[0])
                value2 = self.data.get(self.get_measurement_label(type_meas)[1])
                value3 = self.data.get(self.get_measurement_label(type_meas)[2])
                if log:
                    self.ts.log_debug('        %s are: %s, %s, %s'
                                      % (self.get_measurement_label(type_meas), value1, value2, value3))
                value = value1 + value2 + value3
                nb_phases = 3
            # TODO : imbalance_resp should change the way you acquire the data
            if type_meas == 'V':
                # average value of V
                value = value / nb_phases
            elif type_meas == 'F':
                # No need to do data average for frequency
                value = self.data.get(self.get_measurement_label(type_meas)[0])
            return round(value, 4)

        except Exception as e:
            self.ts.log_error('Inverter phase parameter not set correctly.')
            self.ts.log_error('phases=%s' % self.phases)
            return None
            #raise p1547Error('Error in get_measurement_total() : %s' % (str(e)))

    def get_rslt_sum_col_name(self):
        """
        Get the column names for the result summary.

        Returns
        -------
        str
            Comma-separated string of column names for the result summary.
        """
        return self.rslt_sum_col_name

    def write_rslt_sum(self):
        """
        Write a summary of results for the current step.

        Combines the analysis results, the step label and the filename to return
        a row that will go in result_summary.csv

        Returns
        -------
        str
            A comma-separated string of result data for the current step.
        """

        xs = self.x_criteria
        ys = list(self.y_criteria.keys())
        first_iter = self.tr_value['FIRST_ITER']
        last_iter = self.tr_value['LAST_ITER']
        row_data = []

        # Time response criteria will take last placed value of Y variables
        if self.criteria_mode[0]:
            row_data.append(str(self.tr_value['TR_90_%_PF']))
        if self.criteria_mode[1]:
            row_data.append(str(self.tr_value['%s_TR_%s_PF' % (ys[-1], first_iter)]))
        if self.criteria_mode[2]:
            row_data.append(str(self.tr_value['%s_TR_%s_PF' % (ys[-1], last_iter)]))

        # Default measured values are V, P and Q (F can be added) refer to set_meas_variable function
        for meas_value in self.meas_values:
            row_data.append(str(self.tr_value['%s_TR_%d' % (meas_value, last_iter)]))
            # Variables needed for variations
            if meas_value in xs:
                row_data.append(str(self.tr_value['%s_TR_TARG_%d' % (meas_value, last_iter)]))
            # Variables needed for criteria verifications with min max passfail
            if meas_value in ys:
                row_data.append(str(round(self.tr_value['%s_TR_TARG_%s' % (meas_value, last_iter)], 3)))
                row_data.append(str(round(self.tr_value['%s_TR_%s_MIN' % (meas_value, last_iter)], 3)))
                row_data.append(str(round(self.tr_value['%s_TR_%s_MAX' % (meas_value, last_iter)], 3)))

        self.ts.log_debug(f'Writing Event into rslt_summary = {self.current_step_label}')
        row_data.append(self.current_step_label)
        row_data.append(str(self.filename))
        # self.ts.log_debug(f'rowdata={row_data}')
        row_data_str = ','.join(row_data) + '\n'

        return row_data_str

        # except Exception as e:
        #     raise p1547Error('Error in write_rslt_sum() : %s' % (str(e)))

    def start(self, step_label):
        """
        Start data collection for a new step.

        Parameters
        ----------
        - step_label (str)  : Label for the current test step. (e.g "Step G")
        """

        # TODO : In a more sophisticated approach, get_initial['timestamp'] will come from a
        #  reliable secure thread or data acquisition timestamp

        self.initial_value['timestamp'] = datetime.now()
        self.current_step_label = step_label
        self.daq.sc['event'] = self.current_step_label
        self.daq.data_sample()
        self.data = self.daq.data_capture_read()

        if isinstance(self.x_criteria, list):
            for xs in self.x_criteria:
                self.initial_value[xs] = {'x_value': self.get_measurement_total(type_meas=xs, log=False)}
                self.daq.sc['%s_MEAS' % xs] = self.initial_value[xs]['x_value']
        else:
            self.initial_value[self.x_criteria] = {
                'x_value': self.get_measurement_total(type_meas=self.x_criteria, log=False)}
            self.daq.sc['%s_MEAS' % self.x_criteria] = self.initial_value[self.x_criteria]['x_value']

        if isinstance(self.y_criteria, dict):
            for ys in list(self.y_criteria.keys()):
                self.initial_value[ys] = {'y_value': self.get_measurement_total(type_meas=ys, log=False)}
                self.daq.sc['%s_MEAS' % ys] = self.initial_value[ys]["y_value"]
        else:
            self.initial_value[self.y_criteria] = {
                'y_value': self.get_measurement_total(type_meas=self.y_criteria, log=False)}
            self.daq.sc['%s_MEAS' % self.y_criteria] = self.initial_value[self.y_criteria]['y_value']

        """
        elif isinstance(self.y_criteria, list):
            for ys in self.y_criteria:
                self.initial_value[ys] = {'y_value': self.get_measurement_total(data=data, type_meas=ys, log=False)}
                self.daq.sc['%s_MEAS' % ys] = self.initial_value[ys]["y_value"]
        """
        self.daq.data_sample()

    def record_timeresponse(self):
        """
        Record time-based response data.

        This method collects data at specified time intervals and stores it in
        the tr_value attribute.

        Returns
        -------
        OrderedDict
            Time response values collected during the test.
        """

        x = self.x_criteria
        y = list(self.y_criteria.keys())
        # self.tr = tr

        first_tr = self.initial_value['timestamp'] + timedelta(seconds=self.tr)
        tr_list = [first_tr]

        for i in range(self.n_tr):
            tr_list.append(tr_list[i] + timedelta(seconds=self.tr))
            for meas_value in self.meas_values:
                self.tr_value['%s_TR_%s' % (meas_value, i)] = None
                if meas_value in x:
                    self.tr_value['%s_TR_TARG_%s' % (meas_value, i)] = None
                elif meas_value in y:
                    self.tr_value['%s_TR_TARG_%s' % (meas_value, i)] = None
                    self.tr_value['%s_TR_%s_MIN' % (meas_value, i)] = None
                    self.tr_value['%s_TR_%s_MAX' % (meas_value, i)] = None
        tr_iter = 1

        for tr_ in tr_list:
            now = datetime.now()
            if now <= tr_:
                time_to_sleep = tr_ - datetime.now()
                self.ts.log('Waiting %s seconds to get the next Tr data for analysis...' %
                            time_to_sleep.total_seconds())
                self.ts.sleep(time_to_sleep.total_seconds())
            self.daq.sc['event'] = "{0}_TR_{1}".format(self.current_step_label, tr_iter)
            #self.define_target(y_criterias_mod=y_criterias_mod)
            self.daq.data_sample()  # sample new data
            data = self.daq.data_capture_read()  # Return dataset created from last data capture


            # update self.daq.sc values for Y_TARGET, Y_TARGET_MIN, and Y_TARGET_MAX

            # store the self.daq.sc['Y_TARGET'], self.daq.sc['Y_TARGET_MIN'], and self.daq.sc['Y_TARGET_MAX'] in tr_value
            for meas_value in self.meas_values:
                try:
                    self.tr_value['%s_TR_%s' % (meas_value, tr_iter)] = self.get_measurement_total(meas_value) #self.daq.sc['%s_MEAS' % meas_value]

                    self.ts.log('Value %s: %s' % (meas_value, self.daq.sc['%s_MEAS' % meas_value]))

                except Exception as e:
                    self.ts.log_error('Test script exception: %s' % traceback.format_exc())
                    self.ts.log_debug('Measured value (%s) not recorded: %s' % (meas_value, e))

            # self.tr_value[tr_iter]["timestamp"] = tr_
            self.tr_value[f'timestamp_{tr_iter}'] = tr_
            self.tr_value['LAST_ITER'] = tr_iter - 1
            tr_iter = tr_iter + 1

        self.tr_value['FIRST_ITER'] = 1

        return self.tr_value


class CriteriaValidation:
    """
    A class for validating criteria in power systems testing.

    This class handles the definition of targets, calculation of min/max values,
    and evaluation of criteria for various IEEE 1547 test procedures and requirements.

    Attributes
    ----------
    - criteria_mode (list)      :  List of boolean values indicating which criteria modes are active.
    - x_criteria (str or list)  :  Criteria for x-axis values.
    - y_criteria (dict)         :  Criteria for y-axis values.
    - step_dict (dict)          :  Dictionary containing step information.
    - tr_value (dict)           :  Dictionary storing time response values.

    Methods
    -------
    define_target(y_criterias_mod=None):
        Define target values for the data acquisition system.
    update_target_value(function, value=None, step_dict=None):
        Update target values based on the specified function.
    calculate_target_values(function, meas_value=None):
        Calculate target, minimum and maximum values for a given function.
    evaluate_criterias(step_dict=None, y_criterias_mod=None):
        Evaluate all specified criteria.
    calculate_open_loop_value(y0, y_ss, duration, tr):
        Calculate the anticipated Y value based on open loop response.
    open_loop_resp_criteria(tr=1):
        Evaluate open loop response criteria.
    result_accuracy_criteria():
        Evaluate result accuracy criteria.
    """

    def __init__(self, criteria_mode):
        """
        Initialize the CriteriaValidation object.

        Parameters
        ----------
        - criteria_mode (list) :  List of boolean values indicating which criteria modes are active.
        """
        self.criteria_mode = criteria_mode

    def define_target(self, y_criterias_mod=None):
        """
        Define target values for the data acquisition system.

        Parameters
        ----------
        - step_dict : (dict, optional)          :  Dictionary containing step information.
        - y_criterias_mod : (dict, optional)    :  Modified y-axis criteria.
        """

        x = self.x_criteria
        y_criteria = self.y_criteria

        if isinstance(y_criterias_mod, dict):
            y_criteria.update(y_criterias_mod)

        y = list(y_criteria.keys())
        # self.tr = tr
        self.ts.log_debug(f'daq={self.daq.sc}')
        for tr_iter in range(self.n_tr + 1):
            self.ts.log_debug(f'tr_iter={tr_iter}')
            # store the self.daq.sc['Y_TARGET'], self.daq.sc['Y_TARGET_MIN'], and self.daq.sc['Y_TARGET_MAX'] in tr_value
            for meas_value in self.meas_values:
                try:
                    if meas_value in x:

                        if (self.step_dict is not None) and (meas_value in list(self.step_dict.keys())):
                            self.ts.log_debug(f'step_dict')
                            self.daq.sc['%s_TARGET' % meas_value] = self.step_dict[meas_value]
                            self.tr_value['%s_TR_TARG_%s' % (meas_value, tr_iter)] = self.step_dict[meas_value]
                            self.ts.log_debug(f'tr_targ={self.tr_value["%s_TR_TARG_%s" % (meas_value, tr_iter)]}')
                            self.ts.log('X Value (%s) = %s' % (meas_value, self.daq.sc['%s_MEAS' % meas_value]))

                    elif meas_value in y:
                        if self.step_dict is not None:
                            # self.ts.log_debug(f'meas={meas_value} et step_dict={self.step_dict}')
                            self.ts.log_debug(f'function={y_criteria[meas_value]}')

                            (self.daq.sc['%s_TARGET' % meas_value], self.daq.sc['%s_TARGET_MIN' % meas_value],
                             self.daq.sc['%s_TARGET_MAX' % meas_value]) = self.calculate_target_values(
                                function=y_criteria[meas_value])

                        else:
                            #self.ts.log_debug(f'********step_dict is empty = {step_dict}')

                            (self.daq.sc['%s_TARGET' % meas_value], self.daq.sc['%s_TARGET_MIN' % meas_value],
                             self.daq.sc['%s_TARGET_MAX' % meas_value]) = self.calculate_target_values(function=y_criteria[meas_value])
                        self.daq.sc['%s_MEAS' % meas_value] = self.get_measurement_total(type_meas=meas_value, log=False)
                        self.tr_value[f'{meas_value}_TR_TARG_{tr_iter}'] = self.daq.sc['%s_TARGET' % meas_value]
                        self.tr_value[f'{meas_value}_TR_{tr_iter}_MIN'] = self.daq.sc['%s_TARGET_MIN' % meas_value]
                        self.tr_value[f'{meas_value}_TR_{tr_iter}_MAX'] = self.daq.sc['%s_TARGET_MAX' % meas_value]
                        self.ts.log_debug(f"{meas_value}_TR_TARG_{tr_iter}")
                        self.ts.log_debug(f'tr_target={self.tr_value[f"{meas_value}_TR_TARG_{tr_iter}"]}')
                        self.ts.log('Y Value (%s) = %s. Pass/fail bounds = [%s, %s]' %
                                    (meas_value, self.daq.sc['%s_MEAS' % meas_value],
                                     self.daq.sc['%s_TARGET_MIN' % meas_value], self.daq.sc['%s_TARGET_MAX' % meas_value]))
                except Exception as e:
                    self.ts.log_error('Test script exception: %s' % traceback.format_exc())
                    self.ts.log_debug('Measured value (%s) not recorded: %s' % (meas_value, e))

    def update_target_value(self, function, value=None, step_dict=None):
        """
        Update target values based on the specified function.

        Parameters
        ----------
        - function (str)                : The function to use for updating target values (e.g., VV, VW, CPF).
        - value : (float, optional)     : Value to use in calculations.
        - step_dict (dict, optional)    : Dictionary containing step information.

        Returns
        -------
        float
            Updated target value.
        """

        if function == PRI:
            self.ts.log('Priotisation function use FW and VW target function to calculate its target values')
            pass

        if function == VV:
            vv_pairs = self.get_params(function=VV, curve=self.curve)
            x = [vv_pairs['V1'], vv_pairs['V2'],
                 vv_pairs['V3'], vv_pairs['V4']]
            y = [vv_pairs['Q1'], vv_pairs['Q2'],
                 vv_pairs['Q3'], vv_pairs['Q4']]
            if value is not None:
                q_value = float(np.interp(value, x, y))
            elif isinstance(step_dict, dict):
                q_value = float(np.interp(step_dict['V'], x, y))

            q_value *= self.pwr
            return round(q_value, 1)

        if function == VW:
            # self.ts.log_debug(f'VW target calculation')
            vw_pairs = self.get_params(function=VW, curve=self.curve)
            self.ts.log_debug(f'vw_pairs={vw_pairs}')
            x = [vw_pairs['V1'], vw_pairs['V2']]
            y = [vw_pairs['P1'], vw_pairs['P2']]

            if value is not None:
                p_value = float(np.interp(value, x, y))
            elif isinstance(step_dict, dict):
                p_value = float(np.interp(step_dict['V'], x, y))
            if p_value < self.p_min:
                p_value = self.p_min
            p_value *= self.pwr

            #self.ts.log_debug(f'p_value={p_value}')
            return round(p_value, 1)

        if function == CPF:
            # #self.ts.log_debug(f'CPF target calculation')
            sign = None
            if step_dict['PF'] > 0:
                sign = -1.0
            else:
                sign = 1.0
            if value is not None:
                q_value = math.sqrt(pow(value, 2) * ((1 / pow(step_dict['PF'], 2)) - 1))
            else:
                q_value = math.sqrt(pow(step_dict['P'], 2) * ((1 / pow(step_dict['PF'], 2)) - 1))
            return q_value * sign

        if function == CRP:
            # self.ts.log_debug(f'CRP target calculation')
            q_value = step_dict['Q']
            return round(q_value, 1)

        if function == WV:
            # #self.ts.log_debug(f'WV target calculation')
            if value is not None:
                p_value = value
            x = [self.param[WV][self.curve]['P1'], self.param[WV][self.curve]['P2'], self.param[WV][self.curve]['P3']]
            y = [self.param[WV][self.curve]['Q1'], self.param[WV][self.curve]['Q2'], self.param[WV][self.curve]['Q3']]
            if p_value < self.p_min:
                p_value = self.p_min
            elif p_value > self.p_rated:
                p_value = self.p_rated

            #p_value = p_value/self.p_rated
            self.ts.log_debug(f'p_meas={step_dict}')
            #q_value = float(np.interp(value, x, y))
            q_value = float(np.interp(p_value, x, y))
            q_value *= self.pwr
            self.ts.log_debug('Power value: %s --> q_target: %s' % (p_value, q_value))
            return q_value

        if function == FW:
            # self.ts.log_debug(f'FW target calculation')
            p_targ = None
            fw_pairs = self.get_params(function=FW, curve=self.curve)
            f_dob = self.f_nom + fw_pairs['dbf']
            f_dub = self.f_nom - fw_pairs['dbf']
            if self.pwr*100 < self.max_pwr_lim:
                p_db = self.pwr
            else:
                p_db = self.max_pwr_lim/100
            p_avl = self.pwr * self.p_rated
            if value is None and isinstance(step_dict, dict):
                value = step_dict['F']
            self.ts.log_debug(f'value={value}')
            if f_dub <= value <= f_dob:
                p_targ = p_db * self.p_rated
            elif value > f_dob:
                p_targ = (p_db - ((value - f_dob) / (self.f_nom * self.param[FW][self.curve]['kof']))) * self.p_rated
                if p_targ < self.p_min:
                    p_targ = self.p_min
            elif value < f_dub:
                p_targ = (p_db + ((f_dub - value) / (self.f_nom * self.param[FW][self.curve]['kof']))) * self.p_rated
                if p_targ > p_avl:
                    p_targ = p_avl
            return p_targ

        if function == LAP: # Limited active power
            self.ts.log_debug(f'LAP target calculation')
            p_targ = step_dict['P'] * self.p_rated
            return p_targ

    def calculate_target_values(self, function, meas_value=None):
        """
        Calculate target, minimum and maximum values for a given function.

        Parameters
        ----------
        - function (str)             : The function to use for calculations (e.g., VV, VW, CPF).
        - meas_value (str, optional) : Measurement value to use in calculations.

        Returns
        -------
        tuple
            Target, minimum and maximum calculated values.
        """

        step_dict = self.step_dict
        if PRI == function: #
            v_meas = self.get_measurement_total(type_meas='V', log=False)
            f_meas = self.get_measurement_total(type_meas='F', log=False)
            target_vw = self.update_target_value(value=v_meas, function=VW, step_dict=self.step_dict)
            target_min_vw = self.update_target_value(value=v_meas + self.MRA['V'] * 1.5, function=VW, step_dict=self.step_dict) - (
                    self.MRA['P'] * 1.5)
            target_max_vw = self.update_target_value(value=v_meas - self.MRA['V'] * 1.5, function=VW, step_dict=self.step_dict) + (
                    self.MRA['P'] * 1.5)
            target_fw = self.update_target_value(value=f_meas, function=FW, step_dict=self.step_dict)
            target_min_fw = self.update_target_value(value=f_meas + self.MRA['F'] * 1.5, function=FW, step_dict=self.step_dict) - (
                    self.MRA['P'] * 1.5)
            target_max_fw = self.update_target_value(value=f_meas - self.MRA['F'] * 1.5, function=FW, step_dict=self.step_dict)
            if target_vw < target_fw:
                target = target_vw
                target_min = target_min_vw
                target_max = target_max_vw
            else:
                target = target_fw
                target_min = target_min_fw
                target_max = target_max_fw

        if function == VV: #
            v_meas = self.get_measurement_total(type_meas='V', log=False)
            #self.ts.log_debug(f'For VV, v_meas={v_meas}--MRAV={self.MRA["V"]}--MRAQ={self.MRA["Q"]}')
            target = self.update_target_value(value=v_meas, function=VV, step_dict=self.step_dict)
            target_min = self.update_target_value(value=v_meas + self.MRA['V'] * 1.5, function=VV, step_dict=self.step_dict) - (
                        self.MRA['Q'] * 1.5)
            target_max = self.update_target_value(value=v_meas - self.MRA['V'] * 1.5, function=VV, step_dict=self.step_dict) + (
                        self.MRA['Q'] * 1.5)

        elif function == VW: #
            v_meas = self.get_measurement_total(type_meas='V', log=False)
            target = self.update_target_value(value=v_meas, function=VW, step_dict=self.step_dict)
            target_min = self.update_target_value(value=v_meas + self.MRA['V'] * 1.5, function=VW, step_dict=self.step_dict) - (
                        self.MRA['P'] * 1.5)
            target_max = self.update_target_value(value=v_meas - self.MRA['V'] * 1.5, function=VW, step_dict=self.step_dict) + (
                        self.MRA['P'] * 1.5)

        elif function == CPF: #
            p_meas = self.get_measurement_total(type_meas='P', log=False)
            target = self.update_target_value(value=p_meas, function=CPF, step_dict=step_dict)
            target_min = \
                self.update_target_value(value=p_meas + self.MRA['P'] * 1.5, function=CPF, step_dict=step_dict) - 1.5 * \
                self.MRA['Q']
            target_max = \
                self.update_target_value(value=p_meas - self.MRA['P'] * 1.5, function=CPF, step_dict=step_dict) + 1.5 * \
                self.MRA['Q']

        elif function == CRP: #
            target = step_dict['Q']
            target_min = step_dict['Q'] - self.MRA['Q'] * 1.5
            target_max = step_dict['Q'] + self.MRA['Q'] * 1.5

        elif function == WV: #
            p_meas = self.get_measurement_total(type_meas='P', log=False)
            # q_meas = self.get_measurement_total(data=data, type_meas='Q', log=False)
            self.ts.log_debug(f'P_meas for WV_target = {p_meas}')
            target = self.update_target_value(value=p_meas, function=WV, step_dict=step_dict)
            target_min = self.update_target_value(value=p_meas + self.MRA['P'] * 1.5, function=WV, step_dict=step_dict) \
                         - (self.MRA['Q'] * 1.5)
            target_max = self.update_target_value(value=p_meas - self.MRA['P'] * 1.5 , function=WV, step_dict=step_dict) \
                         + (self.MRA['Q'] * 1.5)

        elif function == FW: #
            f_meas = self.get_measurement_total(type_meas='F', log=False)
            target = self.update_target_value(value=f_meas, function=FW, step_dict=self.step_dict)
            target_min = self.update_target_value(value=f_meas + self.MRA['F'] * 1.5, function=FW, step_dict=self.step_dict) - (
                        self.MRA['P'] * 1.5)
            target_max = self.update_target_value(value=f_meas - self.MRA['F'] * 1.5, function=FW, step_dict=self.step_dict) + (
                        self.MRA['P'] * 1.5)

        elif function == LAP: #
            if self.current_step_label == 'Step C': #LAP specific
                target = self.update_target_value(function=LAP, step_dict=self.step_dict)
                target_min = self.update_target_value(function=LAP, step_dict=self.step_dict) - (self.MRA['P'] * 1.5)
                target_max = self.update_target_value(function=LAP, step_dict=self.step_dict) + (self.MRA['P'] * 1.5)
            elif self.current_step_label == 'Step D' or self.current_step_label == 'Step E': #FW
                f_meas = self.get_measurement_total(type_meas='F', log=False)
                target = self.update_target_value(value=f_meas, function=FW, step_dict=self.step_dict)
                target_min = self.update_target_value(value=f_meas + self.MRA['F'] * 1.5, function=FW,
                                                      step_dict=self.step_dict) - (self.MRA['P'] * 1.5)
                target_max = self.update_target_value(value=f_meas - self.MRA['F'] * 1.5, function=FW,
                                                      step_dict=self.step_dict) + (self.MRA['P'] * 1.5)
            elif self.current_step_label == 'Step F': #VW
                p_meas = self.get_measurement_total(type_meas='P', log=False)
                target = self.update_target_value(value=p_meas, function=WV, step_dict=step_dict)
                target_min = self.update_target_value(value=p_meas + self.MRA['P'] * 1.5, function=WV,
                                                      step_dict=step_dict) - (self.MRA['Q'] * 1.5)
                target_max = self.update_target_value(value=p_meas - self.MRA['P'] * 1.5, function=WV,
                                                      step_dict=step_dict) + (self.MRA['Q'] * 1.5)
            else:
                self.ts.log_error(f'Step {self.current_step_label} not analyzed')
                target = None
                target_min = None
                target_max = None


        return target, target_min, target_max

    def evaluate_criterias(self, step_dict=None, y_criterias_mod=None):
        """
        Evaluate all specified criteria.

        Parameters
        ----------
        - step_dict (dict, optional)        : Dictionary containing step information.
        - y_criterias_mod (dict, optional)  : Modified y-axis criteria.
        """

        self.step_dict = step_dict
        self.define_target(y_criterias_mod=y_criterias_mod)

        if self.criteria_mode[0]:
            self.open_loop_resp_criteria()
        if self.criteria_mode[1] or self.criteria_mode[2]:
            self.result_accuracy_criteria()

    def calculate_open_loop_value(self, y0, y_ss, duration, tr):
        """
        Calculate the anticipated Y value based on open loop response.

        Parameters
        ----------
        - y0 (float) : Initial Y value
        - y_ss (float) : Steady-state Y value
        - duration (float) : Duration since the change in input parameter
        - tr (float) : Open loop response time


        Returns
        -------
        float
            Calculated Y value.
        """
        # Note: for a unit step response Y(t) = 1 - exp(-t/tau) where tau is the time constant
        # This function calculates the anticipated Y(Tr +/- MRA_T) values based on duration and Tr

        time_const = tr / (-(math.log(0.1)))  # ~2.3 * time constants to reach the open loop response time in seconds
        number_of_taus = duration / time_const  # number of time constants into the response
        resp_fraction = 1 - math.exp(-number_of_taus)  # fractional response after the duration, e.g. 90%

        # Y must be 90% * (Y_final - Y_initial) + Y_initial
        resp = (y_ss - y0) * resp_fraction + y0  # expand to y units

        return resp

    def open_loop_resp_criteria(self, tr=1):
        """
        Evaluate open loop response criteria.

        Parameters
        ----------
        - tr (int, optional) : Time response index (default is 1).
        """
        
        """   
        TRANSIENT: Open Loop Time Response (OLTR) = 90% of (y_final-y_initial) + y_initial
        
            The variable y_tr is the value used to verify the time response requirement.
            |----------|----------|----------|----------|
                        1st tr     2nd tr     3rd tr     4th tr
            |          |          |
            y_initial  y_tr       y_final_tr
    
        (1547.1) After each step, the open loop response time, Tr, is evaluated.
        The expected output, Y(Tr), at one times the open loop response time,
        is calculated as 90%*(Y_final_tr - Y_initial ) + Y_initial 
        """
        y = list(self.y_criteria.keys())[0]
        mra_y = self.MRA[y]

        duration = self.tr_value[f"timestamp_{tr}"] - self.initial_value['timestamp']
        duration = duration.total_seconds()
        self.ts.log('Calculating pass/fail for Tr = %s sec, with a target of %s sec' %
                    (duration, tr))

        # Given that Y(time) is defined by an open loop response characteristic, use that curve to
        # calculated the target, minimum, and max, based on the open loop response expectation
        if self.script_name == CRP:  # for those tests with a flat 90% evaluation
            y_start = 0.0  # only look at 90% of target
            mra_t = 0  # direct 90% evaluation without consideration of MRA(time)
        else:
            y_start = self.initial_value[y]['y_value']
            # y_start = tr_value['%s_INITIAL' % y]
            mra_t = self.MRA['T'] * duration  # MRA(X) = MRA(time) = 0.01*duration
        # self.ts.log_debug(f'tr_value={self.tr_value}')
        y_ss = self.tr_value[f'{y}_TR_TARG_{tr}']
        y_target = self.calculate_open_loop_value(y0=y_start, y_ss=y_ss, duration=duration, tr=tr)  # 90%
        y_meas = self.tr_value[f'{y}_TR_{tr}']
        self.ts.log_debug(
            f'y_target = {y_target:.2f}, y_ss [{y_ss:.2f}], y_start [{y_start:.2f}], duration = {duration}, tr={tr}')

        if y_start <= y_target:  # increasing values of y
            increasing = True
            # Y(time) = open loop curve, so locate the Y(time) value on the curve
            y_min = self.calculate_open_loop_value(y0=y_start, y_ss=y_ss,
                                                   duration=duration - 1.5 * mra_t, tr=tr) - 1.5 * mra_y
            # Determine maximum value based on the open loop response expectation
            y_max = self.calculate_open_loop_value(y0=y_start, y_ss=y_ss,
                                                   duration=duration + 1.5 * mra_t, tr=tr) + 1.5 * mra_y
        else:  # decreasing values of y
            increasing = False
            # Y(time) = open loop curve, so locate the Y(time) value on the curve
            y_min = self.calculate_open_loop_value(y0=y_start, y_ss=y_ss,
                                                   duration=duration + 1.5 * mra_t, tr=tr) - 1.5 * mra_y
            # Determine maximum value based on the open loop response expectation
            y_max = self.calculate_open_loop_value(y0=y_start, y_ss=y_ss,
                                                   duration=duration - 1.5 * mra_t, tr=tr) + 1.5 * mra_y

        # pass/fail applied to the open loop time response
        if self.script_name == CRP:  # 1-sided analysis
            # Pass: Ymin <= Ymeas when increasing y output
            # Pass: Ymeas <= Ymax when decreasing y output
            if increasing:
                if y_min <= y_meas:
                    self.tr_value['TR_90_%_PF'] = 'Pass'
                else:
                    self.tr_value['TR_90_%_PF'] = 'Fail'
                self.ts.log_debug('Transient y_targ = %s, y_min [%s] <= y_meas [%s] = %s' %
                                  (y_target, y_min, y_meas, self.tr_value['TR_90_%_PF']))
            else:  # decreasing
                if y_meas <= y_max:
                    self.tr_value['TR_90_%_PF'] = 'Pass'
                else:
                    self.tr_value['TR_90_%_PF'] = 'Fail'
                self.ts.log_debug('Transient y_targ = %s, y_meas [%s] <= y_max [%s] = %s'
                                  % (y_target, y_meas, y_max, self.tr_value['TR_90_%_PF']))

        else:  # 2-sided analysis
            # Pass/Fail: Ymin <= Ymeas <= Ymax
            if y_min <= y_meas <= y_max:
                self.tr_value['TR_90_%_PF'] = 'Pass'
            else:
                self.tr_value['TR_90_%_PF'] = 'Fail'
            display_value_p1 = f'Transient y_targ ={y_target:.2f}, y_min [{y_min:.2f}] <= y_meas'
            display_value_p2 = f'[{y_meas:.2f}] <= y_max [{y_max:.2f}] = {self.tr_value["TR_90_%_PF"]}'

            self.ts.log_debug(f'{display_value_p1} {display_value_p2}')

    def result_accuracy_criteria(self):
        """
        Evaluate result accuracy criteria.
        """
        # Note: Note sure where criteria_mode[1] (Steady-state accuracy after 1 Tr) is used in IEEE 1547.1
        self.ts.log_debug(f'RESULT_ACCURACY')
        for y in self.y_criteria:
            for tr_iter in range(self.tr_value['FIRST_ITER'], self.tr_value['LAST_ITER'] + 1):

                if (self.tr_value['FIRST_ITER'] == tr_iter and self.criteria_mode[1]) or \
                        (self.tr_value['LAST_ITER'] == tr_iter and self.criteria_mode[2]):

                    # pass/fail assessment for the steady-state values
                    # self.ts.log_debug(f'current iter={tr_iter}')
                    if self.tr_value['%s_TR_%s_MIN' % (y, tr_iter)] <= \
                            self.tr_value['%s_TR_%s' % (y, tr_iter)] <= self.tr_value['%s_TR_%s_MAX' % (y, tr_iter)]:
                        self.tr_value['%s_TR_%s_PF' % (y, tr_iter)] = 'Pass'
                    else:
                        self.tr_value['%s_TR_%s_PF' % (y, tr_iter)] = 'Fail'

                    self.ts.log('  Steady state %s(Tr_%s) evaluation: %0.1f <= %0.1f <= %0.1f  [%s]' % (
                        y,
                        tr_iter,
                        self.tr_value['%s_TR_%s_MIN' % (y, tr_iter)],
                        self.tr_value['%s_TR_%s' % (y, tr_iter)],
                        self.tr_value['%s_TR_%s_MAX' % (y, tr_iter)],
                        self.tr_value['%s_TR_%s_PF' % (y, tr_iter)]))


class ImbalanceComponent:
    """
    A class to represent imbalance components for voltage test cases.

    Attributes
    ----------
    - mag (dict)  : Dictionary to store magnitude values for imbalance cases
    - ang (dict)  : Dictionary to store angle values for imbalance cases

    Methods
    -------
    set_imbalance_config(imbalance_angle_fix=None):
        Configure imbalance test cases with fixed or calculated angles
    set_grid_asymmetric(grid, case, imbalance_resp='AVG_3PH_RMS'):
        Configure the grid simulator for asymmetric voltage conditions
    """

    def __init__(self):
        """
        Initialize the ImbalanceComponent object with empty dictionaries for magnitude and angle.
        """
        self.mag = {}
        self.ang = {}

    def set_imbalance_config(self, imbalance_angle_fix=None):
        """
        Configure imbalance test cases with fixed or calculated angles.

        Parameters
        ----------
        - imbalance_angle_fix (str, optional) : Configuration option for angle fixing
            'std'     : Standard fixed angles at 120 degrees
            'fix_mag' : Fixed magnitudes with calculated angles
            'fix_ang' : Fixed angles with calculated magnitudes
            'not_fix' : Both magnitudes and angles calculated

        Raises
        ------
        Exception
            If an incorrect parameter value is provided
        """

        '''
                                            Table 24 - Imbalanced Voltage Test Cases
                +-----------------------------------------------------+-----------------------------------------------+
                | Phase A (p.u.)  | Phase B (p.u.)  | Phase C (p.u.)  | In order to keep V0 magnitude                 |
                |                 |                 |                 | and angle at 0. These parameter can be used.  |
                +-----------------+-----------------+-----------------+-----------------------------------------------+
                |       Mag       |       Mag       |       Mag       | Mag   | Ang  | Mag   | Ang   | Mag   | Ang    |
        +-------+-----------------+-----------------+-----------------+-------+------+-------+-------+-------+--------+
        |Case A |     >= 1.07     |     <= 0.91     |     <= 0.91     | 1.08  | 0.0  | 0.91  |-126.59| 0.91  | 126.59 |
        +-------+-----------------+-----------------+-----------------+-------+------+-------+-------+-------+--------+
        |Case B |     <= 0.91     |     >= 1.07     |     >= 1.07     | 0.9   | 0.0  | 1.08  |-114.5 | 1.08  | 114.5  |
        +-------+-----------------+-----------------+-----------------+-------+------+-------+-------+-------+--------+

        For tests with imbalanced, three-phase voltages, the manufacturer shall state whether the EUT responds
        to individual phase voltages, or the average of the three-phase effective (RMS) values or the positive
        sequence of voltages. For EUTs that respond to individual phase voltages, the response of each
        individual phase shall be evaluated. For EUTs that response to the average of the three-phase effective
        (RMS) values mor the positive sequence of voltages, the total three-phase reactive and active power
        shall be evaluated.
        '''
        try:
            if imbalance_angle_fix == 'std':
                # Case A
                self.mag['case_a'] = [1.07 * self.v_nom, 0.91 * self.v_nom, 0.91 * self.v_nom]
                self.ang['case_a'] = [0.0, -120.0, 120.0]
                # Case B
                self.mag['case_b'] = [0.91 * self.v_nom, 1.07 * self.v_nom, 1.07 * self.v_nom]
                self.ang['case_b'] = [0.0, -120.0, 120.0]
                self.ts.log("Setting test with imbalanced test with FIXED angles/values")
            elif imbalance_angle_fix == 'fix_mag':
                # Case A
                self.mag['case_a'] = [1.07 * self.v_nom, 0.91 * self.v_nom, 0.91 * self.v_nom]
                self.ang['case_a'] = [0.0, -126.59, 126.59]
                # Case B
                self.mag['case_b'] = [0.91 * self.v_nom, 1.07 * self.v_nom, 1.07 * self.v_nom]
                self.ang['case_b'] = [0.0, -114.5, 114.5]
                self.ts.log("Setting test with imbalanced test with NOT FIXED angles/values")
            elif imbalance_angle_fix == 'fix_ang':
                # Case A
                self.mag['case_a'] = [1.08 * self.v_nom, 0.91 * self.v_nom, 0.91 * self.v_nom]
                self.ang['case_a'] = [0.0, -120.0, 120.0]
                # Case B
                self.mag['case_b'] = [0.9 * self.v_nom, 1.08 * self.v_nom, 1.08 * self.v_nom]
                self.ang['case_b'] = [0.0, -120.0, 120.0]
                self.ts.log("Setting test with imbalanced test with NOT FIXED angles/values")
            elif imbalance_angle_fix == 'not_fix':
                # Case A
                self.mag['case_a'] = [1.08 * self.v_nom, 0.91 * self.v_nom, 0.91 * self.v_nom]
                self.ang['case_a'] = [0.0, -126.59, 126.59]
                # Case B
                self.mag['case_b'] = [0.9 * self.v_nom, 1.08 * self.v_nom, 1.08 * self.v_nom]
                self.ang['case_b'] = [0.0, -114.5, 114.5]
                self.ts.log("Setting test with imbalanced test with NOT FIXED angles/values")

            # return (self.mag, self.ang)
        except Exception as e:
            self.ts.log_error('Incorrect Parameter value : %s' % e)
            raise

    def set_grid_asymmetric(self, grid, case, imbalance_resp='AVG_3PH_RMS'):
        """
        Configure the grid simulator for asymmetric voltage conditions.

        Parameters
        ----------
        - grid (object)               : A gridsim object from the svpelab library
        - case (str)                  : The imbalance case to apply ('case_a' or 'case_b')
        - imbalance_resp (str, optional) : The type of imbalance response to calculate
            'AVG_3PH_RMS'                 : Average three-phase RMS (default)
            'INDIVIDUAL_PHASES_VOLTAGES'  : Individual phase voltages
            'POSITIVE_SEQUENCE_VOLTAGES'  : Positive sequence voltages

        Returns
        -------
        float or None
            The calculated imbalance response value, if applicable
        """
        self.ts.log_debug(f'mag={self.mag}')
        self.ts.log_debug(f'mag={self.ang}')
        self.ts.log_debug(f'grid={grid}')
        self.ts.log_debug(f'imbalance_resp={imbalance_resp}')

        if grid is not None:
            grid.config_asymmetric_phase_angles(mag=self.mag[case], angle=self.ang[case])
        if imbalance_resp == 'AVG_3PH_RMS':
            self.ts.log_debug(f'mag={self.mag[case]}')
            return round(sum(self.mag[case]) / 3.0, 2)
        elif imbalance_resp is 'INDIVIDUAL_PHASES_VOLTAGES':
            # TODO TO BE COMPLETED
            return None
        elif imbalance_resp is 'POSITIVE_SEQUENCE_VOLTAGES':
            # TODO to be completed
            return None
        return None


"""
Section for criteria validation
"""
"""
class PassFail:
    def __init__(self):
"""
"""
Section reserved for HIL model object
"""


class HilModel(object):
    """
    A class to represent a Hardware-in-the-Loop (HIL) model for IEEE 1547 testing.

    Attributes
    ----------
    - params (dict)                : Dictionary to store parameters
    - parameters_dic (dict)        : Dictionary to store parameters for different modes
    - mode (list)                  : List to store modes
    - ts                           : Test script object
    - start_time (float or None)   : Start time of the simulation
    - stop_time (float or None)    : Stop time of the simulation
    - hil                          : HIL interface object
    - f_nom (float)                : Nominal frequency (assumed to be defined elsewhere)
    - phases (str)                 : Phase configuration (assumed to be defined elsewhere)

    Methods
    -------
    set_nominal_values():
        Set nominal voltage and frequency values in the HIL simulation
    set_time_path():
        Set the time path signal for the HIL simulation
    set_input_scale_offset():
        Set input scale and offset for voltage and current in the HIL simulation
    get_model_parameters(current_mode):
        Get HIL parameters for a specific mode
    """

    def __init__(self, ts, support_interfaces):
        """
        Initialize the HilModel object.

        Parameters
        ----------
        - ts                : Test script object
        - support_interfaces: Dictionary of support interfaces
        """
        self.params = {}
        self.parameters_dic = {}
        self.mode = []
        self.ts = ts
        self.start_time = None
        self.stop_time = None
        if support_interfaces.get('hil') is not None:
            self.hil = support_interfaces.get('hil')
            self.ts.log(f"P1547 has a hil support_interfaces : {self.hil}")

        else:
            self.hil = None
            self.ts.log(f"P1547 has no hil support_interfaces")

        self.set_time_path()
        self.set_nominal_values()
        #self.set_input_scale_offset()

        # recommend changing these in simulink for each lab to verify the HIL simulation is safe and
        # operational before executing in the SVP - Jay
        
    def set_nominal_values(self):
        """
        Set nominal voltage and frequency values in the HIL simulation.
        """
        parameters = []
        parameters.append((f"VNOM", 1.0))
        parameters.append((f"FNOM", self.f_nom))
        self.hil.set_matlab_variables(parameters)

    def set_time_path(self):
        """
        Set the time path signal for the HIL simulation.
        """
        self.hil.set_time_sig("/SM_Source/IEEE_1547_TESTING/Clock/port1")

    def set_input_scale_offset(self):
        """
        Set input scale and offset for voltage and current in the HIL simulation.

        This method reads scale and offset values from test parameters and applies them to the HIL model.
        """
        # .replace(" ", "") removes the space 
        # .split(",") split with the comma
        scale_current = self.ts.param_value('eut.scale_current').replace(" ", "").split(",")
        offset_current = self.ts.param_value('eut.offset_current').replace(" ", "").split(",")
        scale_voltage = self.ts.param_value('eut.scale_voltage').replace(" ", "").split(",")
        offset_voltage = self.ts.param_value('eut.offset_voltage').replace(" ", "").split(",")

        if self.phases == "Single Phase":
            phases = ["A"]
        elif self.phases == "Split phase":
            phases = ["A", "B"]
        else:
            phases = ["A", "B", "C"]

        parameters = []
        i = 0
        for ph in phases:
            parameters.append((f"CURRENT_INPUT_SCALE_PH{ph}", float(scale_current[i])))
            parameters.append((f"VOLT_INPUT_SCALE_PH{ph}", float(scale_voltage[i])))
            parameters.append((f"VOLT_INPUT_OFFSET_PH{ph}", float(offset_voltage[i])))
            parameters.append((f"CURRENT_INPUT_OFFSET_PH{ph}", float(offset_current[i])))
            i = i + 1

        self.hil.set_matlab_variables(parameters)

    def get_model_parameters(self, current_mode):
        """
        Get HIL parameters for a specific mode.

        Parameters
        ----------
        - current_mode (str) : The mode for which to retrieve parameters

        Returns
        -------
        tuple
            A tuple containing the parameters dictionary, start time, and stop time for the specified mode
        """
        self.ts.log(f'Getting HIL parameters for {current_mode}')
        return self.parameters_dic[current_mode], self.start_time, self.stop_time

"""
This section is for Voltage stabilization function such as VV, VW, CPF and CRP
"""

class VoltVar(EutParameters, UtilParameters):
    """
    A class to represent the Volt-Var function for Distributed Energy Resources (DER) testing according to IEEE 1547 standards.

    
    Parameters 
    ----------
    - EutParameters (object)  :  A class to represent Equipment Under Test (EUT) parameters.
    - UtilParameters (object) :  A class to represent utility parameters for test scripts.


    Attributes
    ----------
    - meas_values (list)            : A list of measurement values, typically including voltage (V), reactive power (Q), and active power (P).
    - x_criteria (list)             : A list of criteria for the x-axis, typically representing voltage (V).
    - y_criteria (dict)             : A dictionary mapping reactive power (Q) to the Volt-Var function (VV).
    - script_complete_name (str)    : A string representing the full name of the Volt-Var script.

    Methods
    -------
    unctions:
    set_params(self): 
        Sets the Volt-Var curve points based on IEEE 1547.1-2020 standards.
    create_vv_dict_steps(self, v_ref, mode='Normal'): 
        Creates a dictionary of voltage steps for the Volt-Var tests, depending on the mode.
    """
    meas_values = ['V', 'Q', 'P']
    x_criteria = ['V']
    y_criteria = {'Q': VV}
    script_complete_name = 'Volt-Var'

    def __init__(self, ts):
        """
        Initialize the VoltVar object.

        Parameters
        ----------
        - ts (object) : Test script object that provides necessary parameters and logging.
        """
        # self.criteria_mode = [True, True, True]
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)
        VoltVar.set_params(self)

    def set_params(self):
        """
        Set the parameters for the Volt-Var curves based on the IEEE 1547 standard.
        """

        """
        Table 25 - Characteristic 1: Default voltage-reactive power settings for normal operating performance
        +------------------------+-------------------------------------+-------------------------------------+
        |                        |                        Default values for DER                             |
        |    Voltage-reactive    +-------------------------------------+-------------------------------------+
        |    power parameters    |                                     |                                     |
        |                        |            Category A               |              Category B             |
        +------------------------+-------------------------------------+-------------------------------------+
        |        VRef            |                VN                   |                  VN                 |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V2             |                VN                   |              0.98 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q2             |                0                    |                  0                  |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V3             |                VN                   |              1.02 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q3             |                0                    |                  0                  |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V1             |               0.9 VN                |              0.92 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q1             | 25% of nameplate apparent power     | 44% of nameplate apparent power     |
        |                        | rating, injection                   | rating, injection                   |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V4             |               1.1 VN                |              1.08 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q4             | 25% of nameplate apparent power     | 44% of nameplate apparent power     |
        |                        | rating, absorption                  | rating, absorption                  |
        +------------------------+-------------------------------------+-------------------------------------+
        | Open loop              |               10 s                  |                5 s                  |
        | response time, Tr      |                                     |                                     |
        +------------------------+-------------------------------------+-------------------------------------+
        """
        # From Table 25 IEEE Std 1547.1-2020 - Categorie B
        self.param[VV] = {}
        self.param[VV][1] = {
            'V1': round(0.92 * self.v_nom, 2),
            'V2': round(0.98 * self.v_nom, 2),
            'V3': round(1.02 * self.v_nom, 2),
            'V4': round(1.08 * self.v_nom, 2),
            'Q1': round(self.s_rated * 0.44, 2),
            'Q2': round(self.s_rated * 0.0, 2),
            'Q3': round(self.s_rated * 0.0, 2),
            'Q4': round(self.s_rated * -0.44, 2),
            'TR': 5.0
        }

        """
        Table 26 - Characteristic 2: Voltage-reactive power settings for normal operating performance
                   Category A and Category B DER
        +------------------------+-------------------------------------+-------------------------------------+
        |                        |                             Values for DER                                |
        |    Voltage-reactive    +-------------------------------------+-------------------------------------+
        |    power parameters    |                                     |                                     |
        |                        |            Category A               |              Category B             |
        +------------------------+-------------------------------------+-------------------------------------+
        |        VRef            |               1.05 VN               |               1.05 VN               |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V2             |               1.04 VN               |               1.04 VN               |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q2             |  50% of nameplate reactive power    |  50% of nameplate reactive power    |
        |                        |  capability, injection              |  capability, injection              |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V3             |              1.07  VN               |              1.07 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q3             |  50% of nameplate reactive power    |  50% of nameplate reactive power    |
        |                        |  capability, injection              |  capability, injection              |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V1             |              0.88 VN                |              0.88 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q1             | 100% of nameplate reactive power    | 100% of nameplate reactive power    |
        |                        | capability, injection               | capability, injection               |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V4             |               1.1 VN                |               1.1 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q4             | 100% of nameplate reactive power    | 44% of nameplate apparent power     |
        |                        | capability, absorption              | capability, absorption              |
        +------------------------+-------------------------------------+-------------------------------------+
        | Open loop              |              1 s                    |                1 s                  |
        | response time, Tr      |                                     |                                     |
        +------------------------+-------------------------------------+-------------------------------------+
        """

        # From Table 26 IEEE Std 1547.1-2020 - Categorie B
        self.param[VV][2] = {
            'V1': round(0.88 * self.v_nom, 2),
            'V2': round(1.04 * self.v_nom, 2),
            'V3': round(1.07 * self.v_nom, 2),
            'V4': round(1.10 * self.v_nom, 2),
            'Q1': round(self.var_rated * 1.0, 2),
            'Q2': round(self.var_rated * 0.5, 2),
            'Q3': round(self.var_rated * 0.5, 2),
            'Q4': round(self.var_rated * -1.0, 2),
            'TR': 1.0
        }
       
        """
        Table 27 - Characteristic 2: Voltage-reactive power settings for normal operating performance
                   Category A and Category B DER
        +------------------------+-------------------------------------+-------------------------------------+
        |                        |                             Values for DER                                |
        |    Voltage-reactive    +-------------------------------------+-------------------------------------+
        |    power parameters    |                                     |                                     |
        |                        |            Category A               |              Category B             |
        +------------------------+-------------------------------------+-------------------------------------+
        |        VRef            |               0.95 VN               |               0.95 VN               |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V2             |               0.93 VN               |               0.93 VN               |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q2             |  50% of nameplate reactive power    |  50% of nameplate reactive power    |
        |                        |  capability, absorption             |  capability, absorption             |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V3             |              0.96  VN               |              0.96  VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q3             |  50% of nameplate reactive power    |  50% of nameplate reactive power    |
        |                        |  capability, absorption             |  capability, absorption             |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V1             |               0.9 VN                |               0.9 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q1             | 100% of nameplate reactive power    | 100% of nameplate reactive power    |
        |                        | capability, injection               | capability, injection               |
        +------------------------+-------------------------------------+-------------------------------------+
        |         V4             |               1.1 VN                |               1.1 VN                |
        +------------------------+-------------------------------------+-------------------------------------+
        |         Q4             | 100% of nameplate reactive power    | 44% of nameplate apparent power     |
        |                        | capability, absorption              | capability, absorption              |
        +------------------------+-------------------------------------+-------------------------------------+
        | Open loop              |              90 s                   |                90 s                 |
        | response time, Tr      |                                     |                                     |
        +------------------------+-------------------------------------+-------------------------------------+
        """

        # From Table 27 IEEE Std 1547.1-2020 - Categorie B
        self.param[VV][3] = {
            'V1': round(0.90 * self.v_nom, 2),
            'V2': round(0.93 * self.v_nom, 2),
            'V3': round(0.96 * self.v_nom, 2),
            'V4': round(1.10 * self.v_nom, 2),
            'Q1': round(self.var_rated * 1.0, 2),
            'Q2': round(self.var_rated * -0.5, 2),
            'Q3': round(self.var_rated * -0.5, 2),
            'Q4': round(self.var_rated * -1.0, 2),
            'TR': 90.0
        }

    def create_vv_dict_steps(self, mode='Normal', ul1547=None):
        """
        Create a dictionary of voltage steps based on the mode of operation.

        This method generates the voltage steps for different test modes, such as Normal, Vref-test, and Imbalanced grid,
        as specified in IEEE Std 1547.1-2020. The voltage steps are used to evaluate the Volt-Var function under
        different conditions.

        Parameters
        ----------
        - v_ref (float) : The reference voltage used in the Volt-Var function.
        - mode (str, optional) : The mode of operation, default is 'Normal'.

        Returns
        -------
        dict
            A dictionary containing the voltage steps for the specified mode of operation.
        """
        
        v_ref = self.running_test_script_parameters["VREF"]
        v_steps_dict = collections.OrderedDict()
        a_v = self.MRA['V'] * 1.5
        v_pairs = self.get_params(function=VV, curve=self.curve)
        self.set_step_label(starting_label='G')
        if mode == 'Vref-test':             # IEEE Std 1547.1-2020 - Section 5.14.5
            return None
        elif mode == 'Imbalanced grid':     # IEEE Std 1547.1-2020 - Section 5.14.6
            return None
            # TODO to be decided if we can put imbalanced steps in here
        else:                               # IEEE Std 1547.1-2020 - Section 5.14.4

            # Capacitive test
            v_steps_dict[self.get_step_label()] = v_pairs['V3'] - a_v                   # Step G
            v_steps_dict[self.get_step_label()] = v_pairs['V3'] + a_v                   # Step H
            v_steps_dict[self.get_step_label()] = (v_pairs['V3'] + v_pairs['V4']) / 2   # Step I
            v_steps_dict[self.get_step_label()] = v_pairs['V4'] - a_v                   # Step J
            v_steps_dict[self.get_step_label()] = v_pairs['V4'] + a_v                   # Step K
            v_steps_dict[self.get_step_label()] = self.v_high - a_v                     # Step L
            v_steps_dict[self.get_step_label()] = v_pairs['V4'] + a_v                   # Step M
            v_steps_dict[self.get_step_label()] = v_pairs['V4'] - a_v                   # Step N
            v_steps_dict[self.get_step_label()] = (v_pairs['V3'] + v_pairs['V4']) / 2   # Step O
            v_steps_dict[self.get_step_label()] = v_pairs['V3'] + a_v                   # Step P
            v_steps_dict[self.get_step_label()] = v_pairs['V3'] - a_v                   # Step Q
            v_steps_dict[self.get_step_label()] = v_ref * self.v_nom                    # Step R
            if ul1547 is None:
                v_steps_dict[self.get_step_label()] = v_ref * self.v_nom
            else:
                v_steps_dict[self.get_step_label()] = self.v_nom

            # Inductive test
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] + a_v                   # Step S
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] - a_v                   # Step T
            v_steps_dict[self.get_step_label()] = (v_pairs['V1'] + v_pairs['V2']) / 2   # Step U
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] + a_v                   # Step V
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] - a_v                   # Step W
            v_steps_dict[self.get_step_label()] = self.v_low + a_v                      # Step X
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] - a_v                   # Step Y
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] + a_v                   # Step Z
            v_steps_dict[self.get_step_label()] = (v_pairs['V1'] + v_pairs['V2']) / 2   # Step AA
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] - a_v                   # Step BB
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] + a_v                   # Step CC
            v_steps_dict[self.get_step_label()] = v_ref * self.v_nom                    # Step DD
            if ul1547 is None:
                v_steps_dict[self.get_step_label()] = v_ref * self.v_nom
            else:
                v_steps_dict[self.get_step_label()] = self.v_nom

            for step, target in v_steps_dict.items():
                v_steps_dict.update({step: round(target, 2)})
                if target > self.v_high:
                    v_steps_dict.update({step: self.v_high})
                elif target < self.v_low:
                    v_steps_dict.update({step: self.v_low})

                # Skips steps when V4 is higher than Vmax of EUT
            if v_pairs['V4'] > self.v_high:
                #self.ts.log_debug('Since V4 is higher than Vmax, Skipping a few steps')
                del v_steps_dict['Step J']
                del v_steps_dict['Step K']
                del v_steps_dict['Step M']
                del v_steps_dict['Step N']

                # Skips steps when V1 is lower than Vmin of EUT
            if v_pairs['V1'] < self.v_low:
                self.ts.log_debug('Since V1 is lower than Vmin, Skipping a few steps')
                del v_steps_dict['Step V']
                del v_steps_dict['Step W']
                del v_steps_dict['Step Y']
                del v_steps_dict['Step Z']

            self.ts.log_debug(v_steps_dict)
            return v_steps_dict




class VoltWatt(EutParameters, UtilParameters):
    """
    This class implements the Volt-Watt functionality as described in IEEE 1547.1-2020 Section 5.14.9.

    The `create_vw_dict_steps()` method generates a dictionary of voltage steps to be used in the Volt-Watt test. 
    The method takes an optional `mode` parameter to specify whether the Volt-Watt is operating under normal or imbalanced grid conditions.
    The method returns an ordered dictionary of voltage steps, with the voltage values rounded to 2 decimal places and clamped to the EUT's 
    voltage limits. Values specified in Tables 31, 32, and 33 of IEEE 1547.1-2020.
    
    Parameters 
    ----------
    - EutParameters (object)  :  A class to represent Equipment Under Test (EUT) parameters.
    - UtilParameters (object) :  A class to represent utility parameters for test scripts.

    """
    meas_values = ['V', 'Q', 'P']
    x_criteria = ['V']
    y_criteria = {'P': VW}
    script_complete_name = 'Volt-Watt'

    """
    param curve: choose curve characterization [1-3] 1 is default
    """

    def __init__(self, ts):
        """
        Initialize the Interoperability object.

        Parameters
        ----------
        - ts : Test script object
        """
        self.ts = ts
        # self.criteria_mode = [True, True, True]
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)
        VoltWatt.set_params(self)

    def set_params(self):
        """
        Function to set VW curves points from Table 31, 32 and 33
        """
        
        self.param[VW] = {}
        """
        Table 31 - Characteristic 1: Default voltage-active power settings for normal operating performance 
        Category A and Category B DER
        +--------------------------------+-------------------------------------+-------------------------------------+
        |                                |                         Default values for DER                            |
        |    Voltage-active power        +-------------------------------------+-------------------------------------+
        |    parameters                  |            Category A               |            Category B               |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              V1                |             1.06 VN                 |             1.06 VN                 |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P1                |             Prated                  |             Prated                  |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              V2                |              1.1 VN                 |              1.1 VN                 |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P2                | The lesser of 0.2 Prated or Pmin    | The lesser of 0.2 Prated or Pmin    |
        | (applicable to DER that can    |                                     |                                     |
        | only generate active power)    |                                     |                                     |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P'2               |                                     |                                     |
        | (applicable to DER that can    |                0                    |                 0                   |
        | generate and absorb active     |                                     |                                     |
        | power)                         |                                     |                                     |
        +--------------------------------+-------------------------------------+-------------------------------------+
        | Open loop response time        |               10 s                  |               10 s                  |
        +--------------------------------+-------------------------------------+-------------------------------------+
        """

        self.param[VW][1] = {
            'V1': round(1.06 * self.v_nom, 2),
            'V2': round(1.10 * self.v_nom, 2),
            'P1': round(self.p_rated, 2),
            'TR': 10.0
        }
        """
        Table 32 - Characteristic 2: Default voltage-active power settings for normal operating performance 
        Category A and Category B DER
        +--------------------------------+-------------------------------------+-------------------------------------+
        |                                |                         Default values for DER                            |
        |    Voltage-active power        +-------------------------------------+-------------------------------------+
        |    parameters                  |            Category A               |            Category B               |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              V1                |             1.05 VN                 |             1.05 VN                 |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P1                |             Prated                  |             Prated                  |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              V2                |              1.1 VN                 |              1.1 VN                 |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P2                | The lesser of 0.2 Prated or Pmin    | The lesser of 0.2 Prated or Pmin    |
        | (applicable to DER that can    |                                     |                                     |
        | only generate active power)    |                                     |                                     |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P'2               |                                     |                                     |
        | (applicable to DER that can    |                0                    |                 0                   |
        | generate and absorb active     |                                     |                                     |
        | power)                         |                                     |                                     |
        +--------------------------------+-------------------------------------+-------------------------------------+
        | Open loop response time        |               90 s                  |               90 s                  |
        +--------------------------------+-------------------------------------+-------------------------------------+
        """
        self.param[VW][2] = {
            'V1': round(1.05 * self.v_nom, 2),
            'V2': round(1.10 * self.v_nom, 2),
            'P1': round(self.p_rated, 2),
            'TR': 90.0
        }
        """
        Table 33 - Characteristic 3: Default voltage-active power settings for normal operating performance 
        Category A and Category B DER
        +--------------------------------+-------------------------------------+-------------------------------------+
        |                                |                         Default values for DER                            |
        |    Voltage-active power        +-------------------------------------+-------------------------------------+
        |    parameters                  |            Category A               |            Category B               |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              V1                |             1.09 VN                 |             1.09 VN                 |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P1                |             Prated                  |             Prated                  |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              V2                |              1.1 VN                 |              1.1 VN                 |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P2                | The lesser of 0.2 Prated or Pmin    | The lesser of 0.2 Prated or Pmin    |
        | (applicable to DER that can    |                                     |                                     |
        | only generate active power)    |                                     |                                     |
        +--------------------------------+-------------------------------------+-------------------------------------+
        |              P'2               |                                     |                                     |
        | (applicable to DER that can    |                0                    |                 0                   |
        | generate and absorb active     |                                     |                                     |
        | power)                         |                                     |                                     |
        +--------------------------------+-------------------------------------+-------------------------------------+
        | Open loop response time        |               0.0 s                 |               0.0 s                 |
        +--------------------------------+-------------------------------------+-------------------------------------+
        """
        self.param[VW][3] = {
            'V1': round(1.09 * self.v_nom, 2),
            'V2': round(1.10 * self.v_nom, 2),
            'P1': round(self.p_rated, 2),
            'TR': 0.5
        }

        if self.p_min > (0.2 * self.p_rated):
            self.param[VW][1]['P2'] = int(0.2 * self.p_rated)
            self.param[VW][2]['P2'] = int(0.2 * self.p_rated)
            self.param[VW][3]['P2'] = int(0.2 * self.p_rated)
        else:
            self.param[VW][1]['P2'] = int(self.p_min)
            self.param[VW][2]['P2'] = int(self.p_min)
            self.param[VW][3]['P2'] = int(self.p_min)
        if self.absorb == 'Yes':
            # Overwrite P2 if mode inverter can absorb power
            self.param[VW][1]['P2'] = 0
            self.param[VW][2]['P2'] = self.p_rated_prime
            self.param[VW][3]['P2'] = self.p_rated_prime

        # self.ts.log_debug('VW settings: %s' % self.param[VW])

    def create_vw_dict_steps(self, mode='Normal'):
        """
        This function creates the dictionary steps for Volt-Watt
        :param mode (string): Verifies if VW is operating under normal or imbalanced grid mode
        :return: vw_dict_steps (dictionary)
        """
        if mode == 'Normal':
            # Setting starting letter for label
            self.set_step_label('G')
            v_steps_dict = collections.OrderedDict()
            v_pairs = self.get_params(curve=self.curve, function=VW)
            a_v = self.MRA['V'] * 1.5

            
            v_steps_dict[self.get_step_label()] = self.v_low + a_v                      # Step G
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] - a_v                   # Step H
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] + a_v                   # Step I
            v_steps_dict[self.get_step_label()] = (v_pairs['V2'] + v_pairs['V1']) / 2   # Step J
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] - a_v                   # Step K
            
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] + a_v                   # Step L
            v_steps_dict[self.get_step_label()] = self.v_high - a_v                     # Step M
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] + a_v                   # Step N
            v_steps_dict[self.get_step_label()] = v_pairs['V2'] - a_v                   # Step O
            
            v_steps_dict[self.get_step_label()] = (v_pairs['V1'] + v_pairs['V2']) / 2   # Step P
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] + a_v                   # Step Q
            v_steps_dict[self.get_step_label()] = v_pairs['V1'] - a_v                   # Step R
            v_steps_dict[self.get_step_label()] = self.v_low + a_v                      # Step S

            if v_pairs['V2'] > self.v_high:
                del v_steps_dict['Step K']
                del v_steps_dict['Step L']
                del v_steps_dict['Step M']
                del v_steps_dict['Step N']
                del v_steps_dict['Step O']

            # Ensure voltage step doesn't exceed the EUT boundaries and round V to 2 decimal places
            for step, voltage in v_steps_dict.items():
                v_steps_dict.update({step: np.around(voltage, 2)})
                if voltage > self.v_high:
                    self.ts.log("{0} voltage step (value : {1}) changed to VH (v_max)".format(step, voltage))
                    v_steps_dict.update({step: self.v_high})
                elif voltage < self.v_low:
                    self.ts.log("{0} voltage step (value : {1}) changed to VL (v_min)".format(step, voltage))
                    v_steps_dict.update({step: self.v_low})

            self.ts.log_debug('curve points:  %s' % v_pairs)

            return v_steps_dict
        return None


class ConstantPowerFactor(EutParameters, UtilParameters):
    """
    A class to represent the Constant Power Factor test based on IEEE 1547.1-2020 - Section 5.14.3.

    Parameters 
    ----------
    - EutParameters (object)  :  A class to represent Equipment Under Test (EUT) parameters.
    - UtilParameters (object) :  A class to represent utility parameters for test scripts.

    Attributes
    ----------
    meas_values : list
        List of measurement values used in the test, including voltage (V), active power (P), reactive power (Q), and power factor (PF).
    x_criteria : list
        List of criteria for the x-axis in the test, including voltage (V) and active power (P).
    y_criteria : dict
        Dictionary mapping y-axis criteria, with reactive power (Q) as the dependent variable.
    script_complete_name : str
        Full name of the script associated with this test.

    """
    meas_values = ['V', 'P', 'Q', 'PF']
    x_criteria = ['V', 'P']
    y_criteria = {'Q': CPF}
    script_complete_name = 'Constant Power Factor'

    def __init__(self, ts):
        """
        Initialize the ConstantPowerFactor object.

        Parameters
        ----------
        - ts : Test script object

        """
        # self.ts = ts
        # self.criteria_mode = [True, True, True]
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)


class ConstantReactivePower(EutParameters, UtilParameters):
    """
    A class to represent the Constant Reactive Power test based on IEEE 1547.1-2020 - Section 5.14.8.

    Attributes
    ----------
    meas_values : list
        List of measurement values used in the test, including voltage (V), reactive power (Q), and active power (P).
    x_criteria : list
        List of criteria for the x-axis in the test, including voltage (V).
    y_criteria : dict
        Dictionary mapping y-axis criteria, with reactive power (Q) as the dependent variable.
    script_complete_name : str
        Full name of the script associated with this test.
    """
    meas_values = ['V', 'Q', 'P']
    x_criteria = ['V']
    y_criteria = {'Q': CRP}
    script_complete_name = 'Constant Reactive Power'

    def __init__(self, ts):
        # self.ts = ts
        # self.criteria_mode = [True, True, True]
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)


class FrequencyWatt(EutParameters, UtilParameters):
    """
    A class to represent the FrequencyWatt based on IEEE 1547.1-2020 - Section 5.15.2.

    Attributes
    ----------
    - meas_values (list)          : List of measurement values used in the test (Frequency and active power)
    - x_criteria (list)           : List of criteria for the x-axis in the test (Frequency)
    - y_criteria (dict)           : Dictionary mapping y-axis criteria (active power as the dependent variable)
    - script_complete_name (str)  : Full name of the script associated with this test
    - param (dict)                : Dictionary to store parameters for different curves
    - f_nom (float)               : Nominal frequency (inherited from EutParameters)
    - f_max (float)               : Maximum frequency (inherited from EutParameters)
    - f_min (float)               : Minimum frequency (inherited from EutParameters)
    - MRA (dict)                  : Measurement Range Accuracy (inherited from EutParameters)

    Methods
    -------
    set_params():
        Set parameters for different Frequency-Watt curves
    create_fw_dict_steps(mode):
        Create a dictionary of frequency steps for the specified mode (Above or Below nominal)
    """
    meas_values = ['F', 'P']
    x_criteria = ['F']
    y_criteria = {'P': FW}
    script_complete_name = 'Frequency-Watt'

    def __init__(self, ts):
        """
        Initialize the FrequencyWatt object.

        Parameters
        ----------
        - ts : Test script object
        """

        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)
        FrequencyWatt.set_params(self)

    def set_params(self):
        """
        Set parameters for different Frequency-Watt curves.

        This method initializes parameters for three different curves based on IEEE 1547.1-2020 requirements.
        """

        p_small = self.ts.param_value('eut_fw.p_small')
        if p_small is None:
            p_small = 0.05

        self.param[FW] = {}
        """
        Table 34 - Characteristic 1: Default frequency-power power settings for abnormal operating performance
        Category I, II, and III DER [SAME AS TABLE 36]
        +------------------------------------------------------------------------------------------------------------+
        |        Parameters      |       Category I          |       Category II         |       Category III        |
        +------------------------+---------------------------+---------------------------+---------------------------+
        |        dbOF (Hz)       |          0.036            |          0.036            |          0.036            |
        +------------------------+---------------------------+---------------------------+---------------------------+
        |         kOF            |           0.05            |           0.05            |           0.05            |
        +------------------------+---------------------------+---------------------------+---------------------------+
        |       Tr (s)           |            5              |            5              |            5              |
        |    (small signal)      |                           |                           |                           |
        +------------------------+---------------------------+---------------------------+---------------------------+
        """
        if self.ts.param_value('fw.test_1_tr') is None:
            # Based on table 34 and category III
            tr_1 = 5.0
        else:
            tr_1 = self.ts.param_value('fw.test_1_tr')
        self.param[FW][1] = {
            'dbf': 0.036,
            'kof': 0.05,
            'TR': tr_1,
            'f_small': p_small * self.f_nom * 0.05
        }
        """
        Table 35 - Characteristic 2: Frequency-power power settings for abnormal operating performance
        Category I, II, and III DER [SAME AS TABLE 37]
        +-------------------------------------------------------------------------------------------- -------------+
        |        Parameters    |       Category I          |       Category II         |       Category III        |
        +----------------------+---------------------------+---------------------------+---------------------------+
        |        dbOF (Hz)     |          0.017            |          0.017            |          0.017            |
        +----------------------+---------------------------+---------------------------+---------------------------+
        |         kOF          |           0.03            |           0.03            |           0.02            |
        +----------------------+---------------------------+---------------------------+---------------------------+
        |       Tr (s)         |            1              |            1              |            0.2            |
        |    (small signal)    |                           |                           |                           |
        +----------------------+---------------------------+---------------------------+---------------------------+
        """
        if self.ts.param_value('fw.test_2_tr') is None:
            tr_2 = 0.2
        else:
            tr_2 = self.ts.param_value('fw.test_2_tr')
        self.param[FW][2] = {
            'dbf': 0.017,
            'kof': 0.03,
            'TR': tr_2,
            'f_small': p_small * self.f_nom * 0.02
        }
        if self.ts.param_value('fw.test_3_tr') is None:
            # Based on table 35 and category III
            tr_3 = 10.0
        else:
            tr_3 = self.ts.param_value('fw.test_3_tr')
        self.param[FW][3] = {
            'dbf': 1.0,
            'kof': 0.05,
            'TR': tr_3,
            'f_small': p_small * self.f_nom * 0.02
        }

    def create_fw_dict_steps(self, mode):
        """
        Create a dictionary of frequency steps for the specified mode.

        Parameters
        ----------
        - mode (str) : The mode for which to create steps ('Above' or 'Below' nominal frequency)

        Returns
        -------
        dict
            An ordered dictionary of frequency steps for the specified mode

        Notes
        -----
        This method creates frequency steps according to IEEE 1547.1-2020 Section 5.15.2.2 for 'Above' mode
        and Section 5.15.3.2 for 'Below' mode.
        """
        a_f = self.MRA['F'] * 1.5
        f_nom = self.f_nom
        f_steps_dict = collections.OrderedDict()
        fw_param = self.get_params(curve=self.curve, function=FW)

        self.set_step_label(starting_label='G')
        if mode == 'Above':    # Above Nominal Frequency 
            f_steps_dict[mode] = {}
            f_steps_dict[mode][self.get_step_label()] =  f_nom                                          # Step G          
            f_steps_dict[mode][self.get_step_label()] = (f_nom + fw_param['dbf']) - a_f                 # Step H                 
            f_steps_dict[mode][self.get_step_label()] = (f_nom + fw_param['dbf']) + a_f                 # Step I
            f_steps_dict[mode][self.get_step_label()] = fw_param['f_small'] + f_nom + fw_param['dbf']   # Step J    
            # STD_CHANGE : step k) should consider the accuracy
            f_steps_dict[mode][self.get_step_label()] = self.f_max - a_f                                # Step K                   
            f_steps_dict[mode][self.get_step_label()] = self.f_max - fw_param['f_small']                # Step L
            f_steps_dict[mode][self.get_step_label()] = (f_nom + fw_param['dbf']) + a_f                 # Step M
            f_steps_dict[mode][self.get_step_label()] = (f_nom + fw_param['dbf']) - a_f                 # Step N
            f_steps_dict[mode][self.get_step_label()] = f_nom

            for step, frequency in f_steps_dict[mode].items():
                f_steps_dict[mode].update({step: np.around(frequency, 3)})
                if frequency > self.f_max:
                    self.ts.log("{0} frequency step (value : {1}) changed to fH (f_max)".format(step, frequency))
                    f_steps_dict[mode].update({step: self.f_max})

        elif mode == 'Below':      # Below Nominal Frequency   
            f_steps_dict[mode] = {}
            f_steps_dict[mode][self.get_step_label()] = (f_nom - fw_param['dbf']) + a_f                 # Step G 
            f_steps_dict[mode][self.get_step_label()] = (f_nom - fw_param['dbf']) - a_f                 # Step H 
            f_steps_dict[mode][self.get_step_label()] = f_nom - fw_param['f_small'] - fw_param['dbf']   

            # STD_CHANGE : step j) should consider the accuracy 
            f_steps_dict[mode][self.get_step_label()] = self.f_min + a_f                                # Step I
            f_steps_dict[mode][self.get_step_label()] = self.f_min + fw_param['f_small']                # Step K
            f_steps_dict[mode][self.get_step_label()] = (f_nom - fw_param['dbf']) - a_f                 # Step L                    
            f_steps_dict[mode][self.get_step_label()] = (f_nom - fw_param['dbf']) + a_f                 # Step M
            f_steps_dict[mode][self.get_step_label()] = f_nom                                           # Step N 


            for step, frequency in f_steps_dict[mode].items():
                f_steps_dict[mode].update({step: np.around(frequency, 3)})
                if frequency < self.f_min:
                    self.ts.log("{0} frequency step (value : {1}) changed to fL (f_min)".format(step, frequency))
                    f_steps_dict[mode].update({step: self.f_min})

        return f_steps_dict[mode]


class Interoperability(EutParameters):
    """
    A class to represent Interoperability tests for EUT (Equipment Under Test).

    Attributes
    ----------
    - meas_values (list)          : List of measurement values to be recorded (Voltage, Power, Frequency)
    - x_criteria (list)           : List of values defined as target/step values to be controlled (Voltage)
    - y_criteria (dict)           : Dictionary of values to be controlled as steps (Power for Interoperability)
    - pairs (dict)                : Dictionary to store paired values
    - param (dict)                : Dictionary to store test parameters
    - target_dict (list)          : List to store target values
    - script_name (str)           : Name of the script (IOP)
    - script_complete_name (str)  : Complete name of the script ('Interoperability')
    - rslt_sum_col_name (str)     : Column names for the result summary
    - criteria_mode (list)        : List of boolean values for criteria modes

    Methods
    -------
    _config():
        Configure the Interoperability test parameters
    set_params():
        Set specific parameters for the Interoperability test
    """
    meas_values = ['V', 'P', 'F']  # Values to be recorded
    x_criteria = ['V']  # Values defined as target/step values which will be controlled as step
    y_criteria = {'P': IOP}  # Values defined as values which will be controlled as step

    def __init__(self, ts):
        """
        Initialize the Interoperability object.

        Parameters
        ----------
        - ts : Test script object
        """
        self.eut_params = EutParameters.__init__(self, ts)
        # self.datalogging = DataLogging.__init__(self)
        self.pairs = {}
        self.param = {}
        self.target_dict = []
        self.script_name = IOP
        self.script_complete_name = 'Interoperability'
        self.rslt_sum_col_name = 'P_TR_ACC_REQ, TR_REQ, P_FINAL_ACC_REQ, V_MEAS, P_MEAS, P_TARGET, P_TARGET_MIN,' \
                                 'P_TARGET_MAX, STEP, FILENAME\n'
        self.criteria_mode = [True, True, True]

        self._config()

    def _config(self):
        """
        Configure the Interoperability test parameters.

        This method sets up the necessary parameters and configurations for the Interoperability test.
        """
        self.set_params()
        # Create the pairs need
        # self.set_imbalance_config()

    def set_params(self):
        """
        Set specific parameters for the Interoperability test.

        This method retrieves and sets the settings and monitoring test parameters from the test script.
        """
        self.param['settings_test'] = self.ts.param_value('iop.settings_test')
        self.param['monitoring_test'] = self.ts.param_value('iop.monitoring_test')


class WattVar(EutParameters, UtilParameters):
    """
    A class to represent the Watt-Var function for power systems.

    Attributes
    ----------
    - meas_values (list)          : List of measurement values (Active Power, Reactive Power)
    - x_criteria (list)           : List of x-axis criteria (Active Power)
    - y_criteria (dict)           : Dictionary of y-axis criteria (Reactive Power for Watt-Var)
    - script_complete_name (str)  : Complete name of the script ('Watt-Var')
    - param (dict)                : Dictionary to store parameters for different curves
    - p_min (float)               : Minimum power (inherited from EutParameters)
    - p_rated (float)             : Rated power (inherited from EutParameters)
    - s_rated (float)             : Rated apparent power (inherited from EutParameters)
    - absorb (str)                : EUT absorption capability (inherited from EutParameters)
    - MRA (dict)                  : Measurement Range Accuracy (inherited from EutParameters)

    Methods
    -------
    set_params():
        Set parameters for different Watt-Var curves
    create_wv_dict_steps():
        Create a dictionary of power steps for the Watt-Var characteristic
    """
    meas_values = ['P', 'Q']
    x_criteria = ['P']
    y_criteria = {'Q': WV}
    script_complete_name = 'Watt-Var'

    def __init__(self, ts, curve=1):
        """
        Initialize the WattVar object.

        Parameters
        ----------
        - ts : Test script object
        - curve (int, optional) : Curve number (default is 1)
        """
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)
        WattVar.set_params(self)

    def set_params(self):
        """
        Set parameters for different Watt-Var curves.

        This method initializes parameters for three different curves based on the EUT's capabilities.
        It considers factors such as minimum power, rated power, and absorption capability.
        """
        self.param[WV] = {}

        if self.p_min > 0.2 * self.p_rated:
            p = self.p_min
            self.ts.log('P1 power is set using p_min')
        else:
            p = 0.2 * self.p_rated
            self.ts.log('P1 power is set using 20% p_rated')

        if self.absorb is "Yes":

            """    
            Table 28 -Characteristic 1: Default active power-reactive power settings for normal operating performance
            Category A and Category B DER
            +--------------------------------+-------------------------------------+-------------------------------------+
            |    Active power-reactive       |                          Default values for DER                           |
            |    power parameters            +-------------------------------------+-------------------------------------+
            |                                |            Category A               |            Category B               |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P3                |                                   Prated                                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P2                |                                 0.5 Prated                                |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P1                |                   The greater of 0.2 Prated and Pmin                      |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'1               |                   The lesser of 0.2 P'rated and P'min                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'2               |                               0.5 P'rated                                 |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'3               |                                  P'rated                                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q3                | 25% of nameplate apparent power     | 44% of nameplate apparent power     |
            |                                | rating, absorption                  | rating, absorption                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q2                |                                     0                                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q1                |                                     0                                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'1               |                                     0                                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'2               |                                     0                                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'3               |            44% of nameplate apparent power rating, injection              |
            +--------------------------------+-------------------------------------+-------------------------------------+
            NOTE:
                - Prated is the nameplate active power rating of the DER.
                - P'rated is the maximum active power that the DER can absorb.
                - Pmin is the minimum active power output of the DER.
                - P'min is the minimum, in amplitude, active power that the DER can absorb.
                - P' parameters are negative in value.
            """
            self.ts.log('Adding EUT Absorption Points (P1_prime-P3_prime, Q1_prime-Q3_prime)')
            self.param[WV][1] = {
                'P1': round(p, 2),
                'P2': round(0.5 * self.p_rated_prime, 2),
                'P3': round(1.0 * self.p_rated_prime, 2),
                'Q1': 0,
                'Q2': 0,
                'Q3': round(self.s_rated * 0.44, 2),
                'TR': 10.0
            }
            """
            Table 29 - Characteristic 2: Active power-reactive power settings for normal operating performance
            Category A and Category B DER
            +--------------------------------+-------------------------------------+-------------------------------------+
            |    Active power-reactive       |                                Values for DER                             |
            |    power parameters            +-------------------------------------+-------------------------------------+
            |                                |             Category A              |             Category B              |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P3                |                                   Prated                                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P2                |                                0.5 Prated                                 |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P1                |                    The greater of 0.2 Prated and Pmin                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'1               |                    The lesser of 0.2 P'rated and P'min                    |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'2               |                                0.5 P'rated                                |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'3               |                                  P'rated                                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q3                | 25% of nameplate apparent power     | 44% of nameplate apparent power     |
            |                                | rating, absorption                  | rating, absorption                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q2                | 13% of nameplate apparent power     | 22% of nameplate apparent power     |
            |                                | rating, absorption                  | rating, absorption                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q1                | 13% of nameplate apparent power     | 22% of nameplate apparent power     |
            |                                | rating, absorption                  | rating, absorption                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'1               |         22% of nameplate apparent power rating, injection                 |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'2               |         22% of nameplate apparent power rating, injection                 |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'3               |         44% of nameplate apparent power rating, injection                 |
            +--------------------------------+-------------------------------------+-------------------------------------+

            NOTE:
            - Prated is the nameplate active power rating of the DER.
            - P'rated is the maximum active power that the DER can absorb.
            - Pmin is the minimum active power output of the DER.
            - P'min is the minimum, in amplitude, active power that the DER can absorb.
            - P' parameters are negative in value.
            """
            self.param[WV][2] = {
                'P1': round(-p, 2),
                'P2': round(0.5 * self.p_rated_prime, 2),
                'P3': round(1.0 * self.p_rated_prime, 2),
                'Q1': round(self.s_rated * 0.22, 2),
                'Q2': round(self.s_rated * 0.22, 2),
                'Q3': round(self.s_rated * 0.44, 2),
                'TR': 10.0
            }
            """
            Table 30 - Characteristic 3: Active power-reactive power settings for normal operating performance
            Category A and Category B DER
            +--------------------------------+-------------------------------------+-------------------------------------+
            |         Active power -         |                                Values for DER                             |
            |        reactive power          +-------------------------------------+-------------------------------------+
            |          parameters            |             Category A              |             Category B              |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P3                |                                   Prated                                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P2                |                                0.5 Prated                                 |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P1                |                    The greater of 0.2 Prated and Pmin                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'1               |                    The lesser of 0.2 P'rated and P'min                    |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'2               |                                0.5 P'rated                                |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              P'3               |                                  P'rated                                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q3                | 25% of nameplate apparent power     | 44% of nameplate apparent power     |
            |                                | rating, absorption                  | rating, absorption                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q2                | 25% of nameplate apparent power     | 44% of nameplate apparent power     |
            |                                | rating, absorption                  | rating, absorption                  |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q1                |                                     0                                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'1               |                                     0                                     |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'2               |         44% of nameplate apparent power rating, injection                 |
            +--------------------------------+-------------------------------------+-------------------------------------+
            |              Q'3               |         44% of nameplate apparent power rating, injection                 |
            +--------------------------------+-------------------------------------+-------------------------------------+

            NOTE:
            - Prated is the nameplate active power rating of the DER.
            - P'rated is the maximum active power that the DER can absorb.
            - Pmin is the minimum active power output of the DER.
            - P'min is the minimum, in amplitude, active power that the DER can absorb.
            - P' parameters are negative in value.
            """
            self.param[WV][3] = {
                'P1': round(-p, 2),
                'P2': round(0.5 * self.p_rated_prime, 2),
                'P3': round(1.0 * self.p_rated_prime, 2),
                'Q1': round(0, 2),
                'Q2': round(self.s_rated * 0.44, 2),
                'Q3': round(self.s_rated * 0.44, 2),
                'TR': 10.0
            }
        else:
            self.param[WV][1] = {
                'P1': round(p, 2),
                'P2': round(0.5 * self.p_rated, 2),
                'P3': round(1.0 * self.p_rated, 2),
                'Q1': round(self.s_rated * 0.0, 2),
                'Q2': round(self.s_rated * 0.0, 2),
                'Q3': round(self.s_rated * -0.44, 2)
            }
            self.param[WV][2] = {
                'P1': round(p, 2),
                'P2': round(0.5 * self.p_rated, 2),
                'P3': round(1.0 * self.p_rated, 2),
                'Q1': round(self.s_rated * -0.22, 2),
                'Q2': round(self.s_rated * -0.22, 2),
                'Q3': round(self.s_rated * -0.44, 2)
            }
            self.param[WV][3] = {
                'P1': round(p, 2),
                'P2': round(0.5 * self.p_rated, 2),
                'P3': round(1.0 * self.p_rated, 2),
                'Q1': round(self.s_rated * 0.0, 2),
                'Q2': round(self.s_rated * -0.44, 2),
                'Q3': round(self.s_rated * -0.44, 2)
            }

        self.ts.log_debug('WV settings: %s' % self.param[WV])

    def create_wv_dict_steps(self):
        """
        Create a dictionary of power steps for the Watt-Var characteristic.

        This method generates a series of power steps to test the Watt-Var characteristic,
        including steps to increase power from minimum to maximum and then decrease back to minimum.

        Returns
        -------
        collections.OrderedDict
            An ordered dictionary of power steps for testing the Watt-Var characteristic
        """

        p_steps_dict = collections.OrderedDict()
        p_pairs = self.get_params(function=WV, curve=self.curve)
        self.set_step_label(starting_label='G')
        a_p = self.MRA['P'] * 1.5
        p_steps_dict[self.get_step_label()] = self.p_min                                        # STEP G
        if (p_pairs['P1'] - a_p) < self.p_min :
            lowest_p_value = self.p_min
        else:
            lowest_p_value = p_pairs['P1'] - a_p
        if (p_pairs['P3'] + a_p) > self.p_rated :
            highest_p_value = self.p_rated
        else:
            highest_p_value = p_pairs['P3'] + a_p


        p_steps_dict[self.get_step_label()] = lowest_p_value                                    # STEP H
        p_steps_dict[self.get_step_label()] = p_pairs['P1'] + a_p                               # STEP I
        p_steps_dict[self.get_step_label()] = (p_pairs['P1'] + p_pairs['P2']) / 2               # STEP J
        p_steps_dict[self.get_step_label()] = p_pairs['P2'] - a_p                               # STEP K
        p_steps_dict[self.get_step_label()] = p_pairs['P2'] + a_p                               # STEP L    
        p_steps_dict[self.get_step_label()] = (p_pairs['P2'] + p_pairs['P3']) / 2               # STEP M
        p_steps_dict[self.get_step_label()] = p_pairs['P3'] - a_p                               # STEP N
        p_steps_dict[self.get_step_label()] = highest_p_value                                   # STEP O
        p_steps_dict[self.get_step_label()] = self.p_rated                                      # STEP P   

        # Begin the return to Pmin
        p_steps_dict[self.get_step_label()] = highest_p_value                                   # STEP Q
        p_steps_dict[self.get_step_label()] = p_pairs['P3'] - a_p                               # STEP R
        p_steps_dict[self.get_step_label()] = (p_pairs['P2'] + p_pairs['P3']) / 2               # STEP S
        p_steps_dict[self.get_step_label()] = p_pairs['P2'] + a_p                               # STEP T
        p_steps_dict[self.get_step_label()] = p_pairs['P2'] - a_p                               # STEP U
        p_steps_dict[self.get_step_label()] = (p_pairs['P1'] + p_pairs['P2']) / 2               # STEP V
        p_steps_dict[self.get_step_label()] = p_pairs['P1'] + a_p                               # STEP W
        p_steps_dict[self.get_step_label()] = lowest_p_value                                    # STEP X
        p_steps_dict[self.get_step_label()] = self.p_min                                        # STEP Y

        return p_steps_dict


class LimitActivePower(EutParameters, UtilParameters):
    """
    A class to represent the Limit Active Power function for power systems.

    Attributes
    ----------
    - meas_values (list)          : List of measurement values (Frequency, Voltage, Active Power, Reactive Power)
    - x_criteria (list)           : List of x-axis criteria (Voltage, Frequency)
    - y_criteria (dict)           : Dictionary of y-axis criteria (Reactive Power for Limit Active Power)
    - script_complete_name (str)  : Complete name of the script ('Limit Active Power')

    """
    meas_values = ['F', 'V', 'P', 'Q']
    x_criteria = ['V', 'F']
    y_criteria = {'Q': LAP}
    script_complete_name = 'Limit Active Power'

    def __init__(self, ts):
        """
        Initialize the UnintentionalIslanding object.

        Parameters
        ----------
        - ts : Test script object
        """
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)
        # LimitActivePower.set_params(self)


class UnintentionalIslanding(EutParameters, UtilParameters):
    """
    A class to represent the Unintentional Islanding test for power systems.

    Attributes
    ----------
    - meas_values (list)          : List of measurement values (Frequency, Voltage, Active Power, Reactive Power)
    - x_criteria (list)           : List of x-axis criteria (Voltage)
    - y_criteria (dict)           : Dictionary of y-axis criteria (Active Power for Unintentional Islanding)
    - script_complete_name (str)  : Complete name of the script ('Unintentional Islanding')

    """
    meas_values = ['F', 'V', 'P', 'Q']
    x_criteria = ['V']
    y_criteria = {'P': UI}

    def __init__(self, ts):
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)
        self.script_complete_name = 'Unintentional Islanding'


class Prioritization(EutParameters, UtilParameters):
    """
    A class to represent the Prioritization function for power systems.

    This class handles the prioritization of different power system functions such as
    Volt-Var (VV), Constant Power Factor (CPF), Constant Reactive Power (CRP), and Watt-Var (WV).

    Attributes
    ----------
    - meas_values (list)          : List of measurement values (Frequency, Voltage, Active Power, Reactive Power)
    - x_criteria (list)           : List of x-axis criteria (Voltage, Frequency)
    - y_criteria (dict)           : Dictionary of y-axis criteria (Reactive Power and Active Power for Prioritization)
    - script_complete_name (str)  : Complete name of the script ('Prioritization')

    Inherited Attributes
    --------------------
    From EutParameters:
    - p_rated (float)             : Rated active power
    - var_rated (float)           : Rated reactive power
    - v_nom (float)               : Nominal voltage

    From UtilParameters:
    - Various utility parameters and methods

    Methods
    -------
    create_pri_dict_steps(function):
        Create a list of dictionaries representing steps for different prioritization functions
    """
    meas_values = ['F', 'V', 'P', 'Q']
    x_criteria = ['V', 'F']
    y_criteria = {'Q': PRI, 'P': PRI}
    script_complete_name = 'Prioritization'

    def __init__(self, ts):
        """
        Initialize the Prioritization object.

        Parameters
        ----------
        - ts : Test script object
        """
        EutParameters.__init__(self, ts)
        UtilParameters.__init__(self)

    def create_pri_dict_steps(self, function):
        """
        Create a list of dictionaries representing steps for different prioritization functions.

        This method generates a series of steps with varying voltage, frequency, and power levels.
        It then adds specific parameters based on the chosen function (VV, CPF, CRP, or WV).

        Parameters
        ----------
        function (str)         :  The function to create steps for. Can be one of VV, CPF, CRP, or WV.

        
        Returns
        -------
        list of dict
            A list of dictionaries, each representing a step in the prioritization test.
            Each dictionary contains keys for 'V' (voltage), 'F' (frequency), 'P' (active power),
            and depending on the function, 'Q' (reactive power) or 'PF' (power factor).
        """

        p_rated = self.p_rated
        q_rated = self.var_rated
        v_nom = self.v_nom
        i = 0

        """
        Table 39 - Category B : Voltage and frequency regulation priority test steps and expected results
        +------+------------+------------+-------------+-----------------------------------------------------+
        | Step | AC test    | AC test    | Expected    |   Expected reactive power for each enabled mode     |
        |      | source     | source     | active      +-------------+------------+------------+-------------+
        |      | voltage    | frequency  | power       | volt-var    | var        | Power      | watt-var    |
        |      | (p.u.)     | (Hz)       | (p.u. of    | (p.u. of    | (p.u. of   | factor     | (p.u. of    |
        |      |            |            | rated power)| rated power)| rated power| (unitless) | rated power)|
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  1   |     1      |    60      |     0.5     |     0       |  0.44 inj  |  0.9 inj   |     0       |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  2   |   1.09     |    60      |     0.4     |   0.44 abs  |  0.44 inj  |  0.9 inj   |     0       |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  3   |   1.09     |   60.33    |     0.3     |   0.44 abs  |  0.44 inj  |  0.9 inj   |     0       |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  4   |   1.09     |    60      |     0.4     |   0.44 abs  |  0.44 inj  |  0.9 inj   |     0       |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  5   |   1.09     |   59.36    |     0.4     |   0.44 abs  |  0.44 inj  |  0.9 inj   |     0       |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  6   |     1      |   59.36    |     0.6     |      0      |  0.44 inj  |  0.9 inj   |  0.09 abs   |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  7   |     1      |    60      |     0.5     |      0      |  0.44 inj  |  0.9 inj   |     0       |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+
        |  8   |     1      |   59.36    |     0.7     |      0      |  0.44 inj  |  0.9 inj   |  0.18 abs   |
        +------+------------+------------+-------------+-------------+------------+------------+-------------+

        Note: p.u. = per unit, inj = injection, abs = absorption
        """
        step_dicts = [{'V': 1.00 * v_nom, 'F': 60.00, 'P': 0.5 * p_rated},
                      {'V': 1.09 * v_nom, 'F': 60.00, 'P': 0.4 * p_rated},
                      {'V': 1.09 * v_nom, 'F': 60.33, 'P': 0.3 * p_rated},
                      {'V': 1.09 * v_nom, 'F': 60.00, 'P': 0.4 * p_rated},
                      {'V': 1.09 * v_nom, 'F': 59.36, 'P': 0.4 * p_rated},
                      {'V': 1.00 * v_nom, 'F': 59.36, 'P': 0.6 * p_rated},
                      {'V': 1.00 * v_nom, 'F': 60.00, 'P': 0.5 * p_rated},
                      {'V': 1.00 * v_nom, 'F': 59.36, 'P': 0.7 * p_rated}]

        if function == VV:
            self.ts.log_debug(f'adding VV in dict step')
            for step_dict in step_dicts:
                self.ts.log_debug(f'step_dict_before={step_dict}')

                if i > 0 or i < 5:
                    step_dict.update({'Q': -0.44 * q_rated})
                    self.ts.log_debug(f'i={i} and step_dict={step_dict}')

                else:
                    step_dict.update({'Q': 0})
                    self.ts.log_debug(f'i={i} and step_dict={step_dict}')

                i += 1
                self.ts.log_debug(f'step_dict={step_dict}')
        elif function == CPF:
            for step_dict in step_dicts:
                step_dict.update({'PF': 0.9})

        elif function == CRP:
            for step_dict in step_dicts:
                step_dict.update({'Q': q_rated})

        elif function == WV:
            for step_dict in step_dicts:
                if i == 5 or i < 7:
                    step_dict.update({'Q': 0.05 * q_rated})
                else:
                    step_dict.update({'Q': 0})
                i += 1

        return step_dicts


"""
This section is for the Active function
"""

class ActiveFunction(DataLogging, CriteriaValidation, ImbalanceComponent, VoltWatt, VoltVar, ConstantReactivePower,
                     ConstantPowerFactor, WattVar, FrequencyWatt, Interoperability, LimitActivePower, Prioritization,
                     UnintentionalIslanding):
    """
    This class acts as the main function for compliance testing.
    It inherits from multiple function classes to incorporate various test capabilities.

    Attributes:
    -----------
    ts  (object)                            : Test script object
    x_criteria  (list)                      : List of criteria for the x-axis in tests
    y_criteria  (dict)                      : Dictionary of criteria for the y-axis in tests
    param  (dict)                           : Dictionary to store parameters
    script_name  (str)                      : Name of the current test script
    running_test_script_parameters (dict)   : Dictionary to store parameters for the running test script
    meas_values (list)                      : List of measurement values used in the tests

    """

    def __init__(self, ts, script_name, functions, criteria_mode):
        """
        Initialize the ActiveFunction object.

        Parameters:
        -----------
        ts (object)            : Test script object
        script_name (str)      : Name of the current test script
        functions (list)       : List of functions to be activated in this test script
        criteria_mode (list)   : List of criteria modes for validation
        """
        self.ts = ts
        # Values defined as target/step values which will be controlled as step
        x_criterias = []
        self.x_criteria = []
        # Values defined as values which will be controlled as step
        y_criterias = []
        self.y_criteria = {}

        # Initiating criteria validation after data acquisition
        CriteriaValidation.__init__(self, criteria_mode=criteria_mode)

        self.param = {}
        # self.criterias = criterias

        self.script_name = script_name

        self.ts.log(f'Functions to be activated in this test script = {functions}')

        self.running_test_script_parameters = {}

        if VW in functions:
            VoltWatt.__init__(self, ts)
            x_criterias += VoltWatt.x_criteria
            self.y_criteria.update(VoltWatt.y_criteria)
        if VV in functions:
            VoltVar.__init__(self, ts)
            x_criterias += VoltVar.x_criteria
            self.y_criteria.update(VoltVar.y_criteria)
        if CPF in functions:
            ConstantPowerFactor.__init__(self, ts)
            x_criterias += ConstantPowerFactor.x_criteria
            self.y_criteria.update(ConstantPowerFactor.y_criteria)
        if CRP in functions:
            ConstantReactivePower.__init__(self, ts)
            x_criterias += ConstantReactivePower.x_criteria
            self.y_criteria.update(ConstantReactivePower.y_criteria)
        if WV in functions:
            WattVar.__init__(self, ts)
            x_criterias += WattVar.x_criteria
            self.y_criteria.update(WattVar.y_criteria)
        if FW in functions:
            FrequencyWatt.__init__(self, ts)
            x_criterias += FrequencyWatt.x_criteria
            self.y_criteria.update(FrequencyWatt.y_criteria)
        if LAP in functions:
            LimitActivePower.__init__(self, ts)
            x_criterias += FrequencyWatt.x_criteria
            self.y_criteria.update(FrequencyWatt.y_criteria)
        if PRI in functions:
            Prioritization.__init__(self, ts)
            x_criterias = Prioritization.x_criteria
            self.y_criteria.update(Prioritization.y_criteria)
        if IOP in functions:
            Interoperability.__init__(self, ts)
            x_criterias += Interoperability.x_criteria
            self.y_criteria.update(Interoperability.y_criteria)
        if UI in functions:
            UnintentionalIslanding.__init__(self, ts)
            x_criterias += UnintentionalIslanding.x_criteria
            self.y_criteria.update(UnintentionalIslanding.y_criteria)

        # Remove duplicates
        self.x_criteria = list(OrderedDict.fromkeys(x_criterias))
        # self.y_criteria=list(OrderedDict.fromkeys(y_criterias))
        self.meas_values = list(OrderedDict.fromkeys(x_criterias + list(self.y_criteria.keys())))

        DataLogging.__init__(self)
        ImbalanceComponent.__init__(self)


class NormalOperation(HilModel, EutParameters, DataLogging):
    """
    This class represents normal operation tests for the Equipment Under Test (EUT).
    It inherits from HilModel, EutParameters, and DataLogging classes.

    Attributes:
    -----------
    Inherited from parent classes
    """

    def __init__(self, ts, support_interfaces):
        """
        Initialize the NormalOperation object.

        Parameters:
        -----------
        ts (object)                         : Test script object
        support_interfaces (dict)           : Dictionary of support interfaces
        """
        EutParameters.__init__(self, ts)
        HilModel.__init__(self, ts, support_interfaces)
        self._config()

    def _config(self):
        """
        Configure the normal operation test.
        Sets normal parameters and VRT (Voltage Ride-Through) modes.
        """
        self.set_normal_params()
        self.set_vrt_modes()


"""
This section is for Ride-Through test
"""

class VoltageRideThrough(HilModel, EutParameters, DataLogging):
    """
    A class to perform Voltage Ride-Through (VRT) tests on inverters.

    This class inherits from HilModel, EutParameters, and DataLogging classes.
    It sets up and executes VRT tests according to specified parameters and modes.

    Attributes:
    -----------
    wfm_header (list)           : List of column headers for the waveform data file.
    phase_combination (str)     : The combination of phases to be tested.

    Methods:
    --------
    _config()
        Configures the VRT parameters, modes, and waveform file header.
    set_vrt_params()
        Sets the VRT test parameters from the test script.
    extend_list_end(_list, extend_value, final_length)
        Extends a list to a specified length with a given value.
    set_vrt_model_parameters(test_sequence)
        Sets the VRT model parameters for the HIL simulation.
    set_phase_combination(phase)
        Sets the phase combination for the VRT test.
    set_wfm_file_header()
        Sets the header for the waveform data file.
    set_test_conditions(current_mode)
        Sets the test conditions based on the current test mode.
    get_vrt_stop_time(test_sequences_df)
        Gets the VRT stop time based on the test sequences dataframe.
    get_test_sequence(current_mode, test_condition)
        Generates the test sequence for the specified VRT mode and test conditions
    set_vrt_modes()
        Sets the VRT modes based on the test parameters.
    get_wfm_file_header()
        Returns the waveform file header.
    get_modes()
        Returns the list of VRT modes to be tested.
    """

    def __init__(self, ts, support_interfaces):
        """
        Initializes the VoltageRideThrough object.

        Parameters:
        -----------
        ts (object)                 : Test script object.
        support_interfaces (dict)   : Dictionary of support interfaces for the test.
        """
        EutParameters.__init__(self, ts)
        HilModel.__init__(self, ts, support_interfaces)
        self.wfm_header = None
        self._config()
        self.phase_combination = None

    def _config(self):
        """
        Configures the VRT parameters, modes, and waveform file header.
        """
        self.set_vrt_params()
        self.set_vrt_modes()
        self.set_wfm_file_header()

    """
    Setter functions
    """

    def set_vrt_params(self):
        """
        Sets the VRT test parameters from the test script.

        Raises:
        -------
        Exception
            If there's an error in setting the parameter values.
        """
        try:
            # RT test parameters
            self.params["lv_mode"] = self.ts.param_value('vrt.lv_ena')
            self.params["hv_mode"] = self.ts.param_value('vrt.hv_ena')
            self.params["categories"] = self.ts.param_value('vrt.cat')
            self.params["range_steps"] = self.ts.param_value('vrt.range_steps')
            self.params["eut_startup_time"] = self.ts.param_value('eut.startup_time')
            self.params["model_name"] = self.hil.rt_lab_model
            self.params["range_steps"] = self.ts.param_value('vrt.range_steps')
            self.params["phase_comb"] = self.ts.param_value('vrt.phase_comb')
            self.params["dataset"] = self.ts.param_value('vrt.dataset_type')
            self.params["consecutive_ena"] = self.ts.param_value('vrt.consecutive_ena')

        except Exception as e:
            self.ts.log_error('Incorrect Parameter value : %s' % e)
            raise

    def extend_list_end(self, _list, extend_value, final_length):
        """
        Extends a list to a specified length with a given value.

        Parameters:
        -----------
        _list (list)            : The list to be extended.
        extend_value (any)      : The value to use for extending the list.
        final_length (int)      : The desired final length of the list.

        Returns:
        --------
        list
            The extended list.
        """
        list_length = len(_list)
        _list.extend([float(extend_value)] * (final_length - list_length))
        return _list

    def set_vrt_model_parameters(self, test_sequence):
        """
        Sets the VRT model parameters for the HIL simulation.

        Parameters:
        -----------
        test_sequence (list)       : The test sequence containing VRT conditions, timings, and values.
        """
        parameters = []
        # if "A" in phase_combination_label:
        #     parameters.append(("VRT_PHA_ENABLE", 1.0))
        # if "B" in phase_combination_label:
        #     parameters.append(("VRT_PHB_ENABLE", 1.0))
        # if "C" in phase_combination_label:
        #     parameters.append(("VRT_PHC_ENABLE", 1.0))

        # Enable VRT mode in the IEEE1547_fast_functions model
        parameters.append(("MODE", 3.0))

        
        CLEARING_STEPS = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

        clearing_steps_list = self.extend_list_end(CLEARING_STEPS, 0.0, 20)
        parameters.append(("CLEARING_STEPS", clearing_steps_list))

        vrt_condition_list = self.extend_list_end(test_sequence["VRT_CONDITION"].to_list(), 0.0, 20)
        parameters.append(("VRT_CONDITION", vrt_condition_list))

        vrt_start_timing_list = self.extend_list_end(test_sequence["VRT_START_TIMING"].to_list(), 0.0, 20)
        parameters.append(("VRT_START_TIMING", vrt_start_timing_list))

        vrt_end_timing_list = self.extend_list_end(test_sequence["VRT_END_TIMING"].to_list(), 0.0, 20)
        parameters.append(("VRT_END_TIMING", vrt_end_timing_list))

        vrt_values_list = self.extend_list_end(test_sequence["VRT_VALUES"].to_list(), 0.0, 20)
        parameters.append(("VRT_VALUES", vrt_values_list))
        self.hil.set_matlab_variables(parameters)

    def set_phase_combination(self, phase):
        """
        Sets the phase combination for the VRT test.

        Parameters:
        -----------
        phase (list)     : List of phases to be enabled for the test.
        """
        parameters = []
        self.ts.log_debug(f"set_phase_combination : {phase}")
        for ph in phase:
            parameters.append((f"VRT_PH{ph}_ENABLE", 1.0))
        self.hil.set_matlab_variables(parameters)

    def set_wfm_file_header(self):
        """
        Sets the header for the waveform data file.
        """
        self.wfm_header = ['TIME',
                           'AC_V_1', 'AC_V_2', 'AC_V_3',
                           'AC_I_1', 'AC_I_2', 'AC_I_3',
                           'AC_P_1', 'AC_P_2', 'AC_P_3',
                           'AC_Q_1', 'AC_Q_2', 'AC_Q_3',
                           'AC_V_CMD_1', 'AC_V_CMD_2', 'AC_V_CMD_3',
                           "TRIGGER"]

    def set_test_conditions(self, current_mode):
        """
        Sets the test conditions based on the current test mode.

        Parameters:
        -----------
        current_mode  (str)            :The current VRT test mode (e.g., 'LV_CAT2', 'HV_CAT3').

        Returns:
        --------
        pd.DataFrame
            A pd.DataFrame containing the test sequence for the current mode.
        """
        # Set useful variables
        mra_v_pu = self.MRA["V"] / self.v_nom
        RANGE_STEPS = self.params["range_steps"]
        index = ['VRT_CONDITION', 'MIN_DURATION', 'VRT_VALUES']
        TEST_CONDITION = {}
        # each condition are set with a pandas series as follow:
        # pd.Series([test condition, minimum duration(s), Residual Voltage (p.u.)], index=index)

        
        """
        Table 4 - Category II LVRT test conditions
        +-------------+-------------------+------------+------------+----------------------------+
        | Test        | Residual voltage  | Minimum    | From-To    | Required DER mode          |
        | condition   | (p.u.)            | duration *a| time       | of operation *b            |
        |             |                   | (s)        |            |                            |
        +-------------+-------------------+------------+------------+----------------------------+
        |      A      |     0.88-1.00     | 10         | t0-t1      | Continuous Operation       |
        +-------------+-------------------+------------+------------+----------------------------+
        |      B      |     0.00-0.30     | 0.160      | t1-t2      | Permissive Operation *e    |
        +-------------+-------------------+------------+------------+----------------------------+
        |      C      |     0.00-0.45     | 0.320      | t1-t3      | Permissive Operation       |
        +-------------+-------------------+------------+------------+----------------------------+
        |      D      |     0.45-0.65     | 3          | t1-t4      | Mandatory Operation *c     |
        +-------------+-------------------+------------+------------+----------------------------+
        |      D'     |     0.67-0.88     | 8          | t1-t4      | Mandatory Operation *d     |
        +-------------+-------------------+------------+------------+----------------------------+
        |      E      |     0.65-0.88     | 5          | t1-t5      | Mandatory Operation        |
        +-------------+-------------------+------------+------------+----------------------------+
        |      F      |     0.88-1.00     | 120        | t5-t6      | Continuous Operation       |
        +-------------+-------------------+------------+------------+----------------------------+

        Notes:
        a. Minimum duration
        b. Required DER mode of operation
        c. Mandatory Operation for condition D
        d. Mandatory Operation for condition D'
        e. Permissive Operation for condition B

        p.u. = per unit
        """
        if CAT_2 in current_mode and LV in current_mode:
            # The possible test conditions are ABCDD'EF
            if RANGE_STEPS == "Figure":
                # Using value of Figure 2 - CATEGORY II LVRT test signal
                TEST_CONDITION["A"] = pd.Series([1, 10, 0.94], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 0.160, 0.3 - 2 * mra_v_pu], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 0.160, 0.45 - 2 * mra_v_pu], index=index)
                TEST_CONDITION["D"] = pd.Series([4, 2.68, 0.65], index=index) # Time from t1 to t4 (3s-0.32s = 2.68s)
                TEST_CONDITION["D'"] = pd.Series([4 + 10, 7.68, 0.67 + 2 * mra_v_pu], index=index)
                TEST_CONDITION["E"] = pd.Series([5, 2.0, 0.88], index=index)
                TEST_CONDITION["F"] = pd.Series([6, 120.0, 0.94], index=index)
            elif RANGE_STEPS == "Random":
                TEST_CONDITION["A"] = pd.Series([1, 10, random.uniform(0.88 + 2 * mra_v_pu, 1.0)], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 0.160, random.uniform(0.0, 0.3 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 0.160, random.uniform(0.0, 0.45 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["D"] = pd.Series([4, 2.68, random.uniform(0.45 + 2 * mra_v_pu, 0.65 - 2 * mra_v_pu)],
                                                index=index)
                TEST_CONDITION["D'"] = pd.Series([4 + 10, 7.68, random.uniform(0.67, 0.88 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["E"] = pd.Series([5, 2.0, random.uniform(0.65 + 2 * mra_v_pu, 0.88 - 2 * mra_v_pu)],
                                                index=index)
                TEST_CONDITION["F"] = pd.Series([6, 120.0, random.uniform(0.88 + 2 * mra_v_pu, 1.0)], index=index)

        
            """
            Table 5 - Category III LVRT test conditions
            +-------------+-------------------+------------+------------+----------------------------+
            | Test        | Residual voltage  | Minimum    | From-To    | Required DER mode          |
            | condition   | (p.u.)            | duration   | time       | of operation               |
            |             |                   | (s)        |            |                            |
            +-------------+-------------------+------------+------------+----------------------------+
            |      A      |     0.88-1.00     | 5          | t0-t1      | Continuous Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      B      |     0.00-0.05     | 1          | t1-t2      | Permissive Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      C      |     0.00-0.50     | 10         | t1-t3      | Permissive Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      C'     |     0.52-0.70     | 10         | t1-t3      | Mandatory Operation        |
            +-------------+-------------------+------------+------------+----------------------------+
            |      D      |     0.50-0.70     | 20         | t1-t4      | Mandatory Operation        |
            +-------------+-------------------+------------+------------+----------------------------+
            |      E      |     0.88-1.00     | 120        | t4-t5      | Mandatory Operation        |
            +-------------+-------------------+------------+------------+----------------------------+
            """
        elif CAT_3 in current_mode and LV in current_mode:
            # The possible test conditions are ABCC'DE
            if RANGE_STEPS == "Figure":
                TEST_CONDITION["A"] = pd.Series([1, 5, 0.94], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 1, 0.05 - 2 * mra_v_pu], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 9, 0.5 - 2 * mra_v_pu], index=index)
                TEST_CONDITION["C'"] = pd.Series([3 + 10, 9, 0.52 + 2 * mra_v_pu], index=index)
                TEST_CONDITION["D"] = pd.Series([4, 10.0, 0.7], index=index)
                TEST_CONDITION["E"] = pd.Series([5, 120.0, 0.94], index=index)
            elif RANGE_STEPS == "Random":
                TEST_CONDITION["A"] = pd.Series([1, 5, random.uniform(0.88 + 2 * mra_v_pu, 1.0)], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 1, random.uniform(0.0, 0.05 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 9, random.uniform(0.0, 0.5 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["C'"] = pd.Series([3 + 10, 9, random.uniform(0.52, 0.7 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["D"] = pd.Series([4, 10.0, random.uniform(0.5 + 2 * mra_v_pu, 0.7 - 2 * mra_v_pu)],
                                                index=index)
                TEST_CONDITION["E"] = pd.Series([5, 120.0, random.uniform(0.88 + 2 * mra_v_pu, 1.0)], index=index)

            """
            Table 7 - Category I and II HVRT test conditions
            +-------------+-------------------+------------+------------+----------------------------+
            | Test        | Residual voltage  | Minimum    | Time       | Mode of operation          |
            | condition   | (p.u.)            | duration   | interval   |                            |
            |             |                   | (s)        |            |                            |
            +-------------+-------------------+------------+------------+----------------------------+
            |      A      |     1.00-1.10     | 10         | t0-t1      | Continuous Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      B      |     1.18-1.20     | 0.2        | t1-t2      | Permissive Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      C      |    1.155-1.175    | 0.5        | t1-t3      | Permissive Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      D      |     1.13-1.15     | 1.0        | t1-t4      | Permissive Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      E      |     1.00-1.10     | 120        | t4-t6      | Continous Operation        |
            +-------------+-------------------+------------+------------+----------------------------+
            """
        elif CAT_2 in current_mode and HV in current_mode:
            # ABCDE
            if RANGE_STEPS == "Figure":
                TEST_CONDITION["A"] = pd.Series([1, 10, 1.0], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 0.2, 1.2 - 2 * mra_v_pu], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 0.3, 1.175], index=index)
                TEST_CONDITION["D"] = pd.Series([4, 0.5, 1.15], index=index)
                TEST_CONDITION["E"] = pd.Series([5, 120.0, 1.0], index=index)
            elif RANGE_STEPS == "Random":
                TEST_CONDITION["A"] = pd.Series([1, 10, random.uniform(1.0, 1.1 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 0.2, random.uniform(1.18, 1.2)], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 0.3, random.uniform(1.155, 1.175)], index=index)
                TEST_CONDITION["D"] = pd.Series([4, 0.5, random.uniform(1.13, 1.15)], index=index)
                TEST_CONDITION["E"] = pd.Series([5, 120.0, random.uniform(1.0, 1.1 - 2 * mra_v_pu)], index=index)

            """
            Table 8 - Category III HVRT test conditions
            +-------------+-------------------+------------+------------+----------------------------+
            | Test        | Residual voltage  | Minimum    | From-To    |         Mode of            |
            | condition   | (p.u.)            | duration   | time       |        operation           |
            |             |                   | (s)        |            |                            |
            +-------------+-------------------+------------+------------+----------------------------+
            |      A      |     1.00-1.10     | 5          | t0-t1      | Continuous Operation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      B      |     1.18-1.20     | 12         | t1-t2      | Momentary Cessation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      B'     |     1.12-1.120    | 12         | t1-t2      | Momentary Cessation       |
            +-------------+-------------------+------------+------------+----------------------------+
            |      C      |     1.00-1.10     | 120        | t2-t3      | Continous Operation        |
            +-------------+-------------------+------------+------------+----------------------------+
            """
        elif CAT_3 in current_mode and HV in current_mode:
            # ABB'C
            if RANGE_STEPS == "Figure":
                TEST_CONDITION["A"] = pd.Series([1, 5, 1.05], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 12, 1.2 - 2 * mra_v_pu], index=index)
                TEST_CONDITION["B'"] = pd.Series([2 + 10, 12, 1.12], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 120, 1.05], index=index)
            elif RANGE_STEPS == "Random":
                TEST_CONDITION["A"] = pd.Series([1, 5, random.uniform(1.0, 1.1 - 2 * mra_v_pu)], index=index)
                TEST_CONDITION["B"] = pd.Series([2, 12, random.uniform(1.18, 1.2)], index=index)
                TEST_CONDITION["B'"] = pd.Series([2 + 10, 12, random.uniform(1.12, 1.2)], index=index)
                TEST_CONDITION["C"] = pd.Series([3, 120, random.uniform(1.0, 1.1 - 2 * mra_v_pu)], index=index)
        '''
        Get the full test sequence :
        Example for CAT_2 + LV + Not Consecutive
                ___________________________________________________
        VRT_CONDITION  MIN_DURATION  VRT_VALUES  VRT_START_TIMING  VRT_END_TIMING
        1.0         10.00        0.94              0.00           10.00
        2.0          0.16        0.28             10.00           10.16
        3.0          0.16        0.43             10.16           10.32
        4.0          2.68        0.65             10.32           13.00
        5.0          2.00        0.88             13.00           15.00
        6.0        120.00        0.94             15.00          135.00

                Example for CAT_3 + HV + Consecutive
                ___________________________________________________
        VRT_CONDITION  MIN_DURATION  VRT_VALUES  VRT_START_TIMING  VRT_END_TIMING
        1.0           5.0        1.05               0.0             5.0
        2.0          12.0        1.20               5.0            17.0
        1.0           5.0        1.05              17.0            22.0
        2.0          12.0        1.20              22.0            34.0
        1.0           5.0        1.05              34.0            39.0
        2.0          12.0        1.20              39.0            51.0
        3.0         120.0        1.05              51.0           171.0
        1.0           5.0        1.05             171.0           176.0
        12.0         12.0        1.14             176.0           188.0
        3.0         120.0        1.05             188.0           308.0

        Note: The Test condition value is directly connected to the alphabetical order.
        The value 1.0 is for A, 2.0 is for B and so on. When a prime is present, we
        just add the value 10.0. The value 12.0 is for B', 13 is for C' and so on.
        The idea is just to show this on the data.
        '''
        test_sequences_df = self.get_test_sequence(current_mode, TEST_CONDITION)

        return test_sequences_df

    def get_vrt_stop_time(self, test_sequences_df):
        """
        Gets the VRT stop time based on the test sequences dataframe.

        Parameters:
        -----------
        test_sequences_df (pd.DataFrame) : test sequence for the current mode
        """
        return test_sequences_df["VRT_END_TIMING"].iloc[-1]

    def get_test_sequence(self, current_mode, test_condition):
        """
        Generates the test sequence for the specified VRT mode and test conditions.

        This method creates a DataFrame containing the full test sequence, including
        VRT conditions, durations, values, and timing information for each step of the test.

        Parameters:
        -----------
        current_mode (str)         : The current VRT test mode (e.g., 'LV_CAT2', 'HV_CAT3').
        test_condition (dict)      : A dictionary containing the test conditions for each step of the sequence.

        Returns:
        --------
        pd.DataFrame
            A DataFrame with columns:
            - VRT_CONDITION: The condition identifier for each step
            - MIN_DURATION: The minimum duration for each step in seconds
            - VRT_VALUES: The voltage values (in p.u.) for each step
            - VRT_START_TIMING: The start time of each step
            - VRT_END_TIMING: The end time of each step

        Notes:
        ------
        - The method handles different test sequences based on the category (CAT_2 or CAT_3)
        and the type of test (LV or HV).
        - It takes into account whether consecutive tests are enabled or not.
        - The timing sequence is calculated based on the EUT startup time and the duration
        of each step.
        """
        index = ['VRT_CONDITION', 'MIN_DURATION', 'VRT_VALUES']
        T0 = self.params["eut_startup_time"]
        if self.params["consecutive_ena"] == "Enabled":
            CONSECUTIVE = True
        else:
            CONSECUTIVE = False
        test_sequences_df = pd.DataFrame(columns=index)
        if CAT_2 in current_mode and LV in current_mode:
            if CONSECUTIVE:
                # ABCDE
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
                # ABCDEF
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["F"], ignore_index=True)
                # ABCD'F
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D'"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["F"], ignore_index=True)

            else:
                # ABCDEF
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["F"], ignore_index=True)
        elif CAT_3 in current_mode and LV in current_mode:
            if CONSECUTIVE:
                # ABCD
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                # ABCD
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                # ABCDE
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
                # ABC'DE
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C'"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
            else:
                # ABCDE
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
        elif CAT_2 in current_mode and HV in current_mode:
            if CONSECUTIVE:
                # ABCD
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)

                # ABCDE
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
            else:
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
                pass
        elif CAT_3 in current_mode and HV in current_mode:
            if CONSECUTIVE:
                # AB
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)

                # AB
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)

                # ABC
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)

                # AB'C
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B'"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
            else:
                test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
                test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
                pass

        test_sequences_df.loc[0, 'VRT_START_TIMING'] = T0
        # Calculate the timing sequences
        test_sequences_df.loc[0, 'VRT_END_TIMING'] = T0 + test_sequences_df.loc[0, 'MIN_DURATION']
        for i in range(1, len(test_sequences_df)):
            test_sequences_df.loc[i, 'VRT_START_TIMING'] = test_sequences_df.loc[i - 1, 'VRT_END_TIMING']
            test_sequences_df.loc[i, 'VRT_END_TIMING'] = test_sequences_df.loc[i, 'VRT_START_TIMING'] + \
                                                         test_sequences_df.loc[i, 'MIN_DURATION']
        return test_sequences_df

    def set_vrt_modes(self):
        """
        Sets the VRT modes based on the test parameters.
        """
        modes = []
        if self.params["lv_mode"] == 'Enabled' and (
                self.params["categories"] == CAT_2 or self.params["categories"] == 'Both'):
            modes.append(f"{LV}_{CAT_2}")
        if self.params["lv_mode"] == 'Enabled' and (
                self.params["categories"] == CAT_3 or self.params["categories"] == 'Both'):
            modes.append(f"{LV}_{CAT_3}")
        if self.params["hv_mode"] == 'Enabled' and (
                self.params["categories"] == CAT_2 or self.params["categories"] == 'Both'):
            modes.append(f"{HV}_{CAT_2}")
        if self.params["hv_mode"] == 'Enabled' and (
                self.params["categories"] == CAT_3 or self.params["categories"] == 'Both'):
            modes.append(f"{HV}_{CAT_3}")
        self.params["modes"] = modes
        #self.ts.log_debug(self.params)

    """
    Getter functions
    """

    def get_wfm_file_header(self):
        """
        Returns the waveform file header.

        Returns:
        --------
        list
            The waveform file header.
        """
        return self.wfm_header

    def get_modes(self):
        """
        Returns the list of VRT modes to be tested.

        Returns:
        --------
        list
            The list of VRT modes.
        """
        return self.params["modes"]


class FrequencyRideThrough(HilModel, EutParameters, DataLogging):
    """
    A class to perform Frequency Ride-Through tests on inverters.

    This class inherits from HilModel, EutParameters, and DataLogging classes.
    It sets up and executes VRT tests according to specified parameters and modes.

    Attributes:
    -----------
    wfm_header (list)       : List of column headers for the waveform data file.
    params (dict)           : A dictionary to hold FRT test parameters such as low-frequency and
                              high-frequency modes, periods, parameters, and EUT startup time.

    Methods:
    --------
    _config()
        Configure FRT parameters, modes, and waveform file header.
    set_frt_params()
        Sets the FRT parameters from the test script.
    set_modes()
        Set the FRT modes based on the test parameters
    set_wfm_file_header()
        Sets the header for the waveform data file.
    set_test_conditions(current_mode)
        Sets the test conditions based on the current test mode.
    set_frt_model_parameters(test_sequence)
        Sets the FRT model parameters for the HIL simulation.
    get_rocof_dic()
        Get the Rate of Change of Frequency (ROCOF) values for the test.
    get_test_sequence(current_mode, test_condition)
        Generates the test sequence for the specified FRT mode and test conditions
    get_frt_stop_time(test_sequences_df)
        Returns the final end timing from the test sequence dataframe.
    get_modes()
        Retrieves the currently enabled FRT modes from the 'params' attribute.
    get_wfm_file_header()
        Returns the waveform file header list.
    extend_list_end(_list, extend_value, final_length)
        Extends the given list with a specified value to reach a certain length.
    """

    def __init__(self, ts, support_interfaces):
        """
        Initializes the FrequencyRideThrough class.

        Parameters:
        -----------
        ts (object)                : The test script environment used for parameter access.
        support_interfaces (list)  : List of hardware support interfaces required for HIL testing.
        """
        ts.log_debug(f"support_interfaces : {support_interfaces}")
        EutParameters.__init__(self, ts)
        self.params = {}
        HilModel.__init__(self, ts, support_interfaces)
        self.wfm_header = None
        self._config()

    def _config(self):
        """
        Configures the initial setup for Frequency Ride-Through tests.

        This method sets FRT parameters, modes, and the waveform file header.
        """
        self.set_frt_params()
        self.set_modes()
        self.set_wfm_file_header()

    """
    Setter functions
    """

    def set_frt_params(self):
        """
        Retrieves and sets the Frequency Ride-Through (FRT) parameters.

        Parameters are fetched from the test script environment and stored in
        the 'params' attribute.

        Raises:
        -------
        Exception
            If an incorrect parameter value is encountered during configuration.
        """
        try:
            # RT test parameters
            self.params["lf_mode"] = self.ts.param_value('frt.lf_ena')
            self.params["hf_mode"] = self.ts.param_value('frt.hf_ena')
            self.params["lf_parameter"] = self.ts.param_value('frt.lf_parameter')
            self.params["lf_period"] = self.ts.param_value('frt.lf_period')
            self.params["hf_parameter"] = self.ts.param_value('frt.hf_parameter')
            self.params["hf_period"] = self.ts.param_value('frt.hf_period')
            self.params["eut_startup_time"] = self.ts.param_value('eut.startup_time')
            # self.params["model_name"] = self.hil.rt_lab_model

        except Exception as e:
            self.ts.log_error('Incorrect Parameter value : %s' % e)
            raise

    def set_modes(self):
        """
        Determines and sets the enabled FRT modes.

        Based on the 'lf_mode' and 'hf_mode' parameters, the corresponding modes 
        are appended to the 'modes' list.
        """
        modes = []
        if self.params["lf_mode"] == "Enabled":
            modes.append(LFRT)
        if self.params["hf_mode"] == "Enabled":
            modes.append(HFRT)
        self.params["modes"] = modes

    def set_wfm_file_header(self):
        """
        Sets the waveform file headers for data logging during the test.

        The header includes time, voltage, current, frequency command, and a 
        trigger signal.
        """
        self.wfm_header = ['TIME',
                           'AC_V_1', 'AC_V_2', 'AC_V_3',
                           'AC_I_1', 'AC_I_2', 'AC_I_3',
                           'AC_FREQ_CMD_1', 'AC_FREQ_CMD_2', 'AC_FREQ_CMD_3', "TRIGGER"]

    def set_test_conditions(self, current_mode):
        """
        Defines and returns the test conditions for the current mode.

        Parameters:
        -----------
        current_mode : list
            A list indicating the active FRT modes (LFRT or HFRT).

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing the test conditions and timing sequences.
        """
        # Set useful variables
        mra_f = self.MRA["F"]
        index = ['FRT_CONDITION', 'MIN_DURATION', 'FRT_VALUES']
        TEST_CONDITION = {}
        # Test Procedure 5.5.3.4
        if LFRT in current_mode:
            TEST_CONDITION["Step E"] = pd.Series([1, 1, self.f_nom], index=index)
            TEST_CONDITION["Step G"] = pd.Series([2, self.params["lf_period"], self.params["lf_parameter"]],
                                                 index=index)
            # TEST_CONDITION["Step H"] = pd.Series([1, 1, self.f_nom], index=index)
            TEST_CONDITION["Step H"] = pd.Series([1, 11, self.f_nom], index=index)

        # Test Procedure 5.5.4.4
        elif HFRT in current_mode:
            
            TEST_CONDITION["Step E"] = pd.Series([1, 1, self.f_nom], index=index)
            TEST_CONDITION["Step G"] = pd.Series([2, self.params["hf_period"], self.params["hf_parameter"]],
                                                 index=index)
            # TEST_CONDITION["Step H"] = pd.Series([1, 1, self.f_nom], index=index)
            TEST_CONDITION["Step H"] = pd.Series([1, 11, self.f_nom], index=index)
        test_sequences_df = self.get_test_sequence(current_mode, TEST_CONDITION)

        return test_sequences_df

    def set_frt_model_parameters(self, test_sequence):
        """
        Sets the model parameters for the FRT test based on the test sequence.

        Parameters:
        -----------
        test_sequence : pd.DataFrame
            A DataFrame containing the test sequence parameters, such as start 
            and end timings and condition values.
        """
        parameters = []
        # Enable FRT mode in the IEEE1547_fast_functions model
        parameters.append(("MODE", 4.0))

        condition_list = self.extend_list_end(test_sequence["FRT_CONDITION"].to_list(), 0.0, 4)
        parameters.append(("FRT_CONDITION", condition_list))

        start_timing_list = self.extend_list_end(test_sequence["FRT_START_TIMING"].to_list(), 0.0, 4)
        parameters.append(("FRT_START_TIMING", start_timing_list))

        end_timing_list = self.extend_list_end(test_sequence["FRT_END_TIMING"].to_list(), 0.0, 4)
        parameters.append(("FRT_END_TIMING", end_timing_list))

        values_list = self.extend_list_end(test_sequence["FRT_VALUES"].to_list(), 0.0, 4)
        parameters.append(("FRT_VALUES", values_list))
        self.hil.set_matlab_variables(parameters)

    """
    Getter functions
    """
    def get_rocof_dic(self, ):
        """
        Returns a dictionary containing predefined Rate of Change of Frequency (ROCOF) values.

        Returns:
        --------
        dict
            A dictionary with keys 'ROCOF_ENABLE', 'ROCOF_VALUE', and 'ROCOF_INIT'.
        """
        params = {"ROCOF_ENABLE": 1.0,
                  "ROCOF_VALUE": 3.0,
                  "ROCOF_INIT": 60.0}
        return params

    def get_test_sequence(self, current_mode, test_condition):
        """
        Creates and returns a test sequence DataFrame.

        Parameters:
        -----------
        current_mode : list
            The active test mode (LFRT or HFRT).
        test_condition : dict
            A dictionary containing the test step conditions, including 
            condition type, minimum duration, and parameter values.

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing the sequence of test steps with start and 
            end timings.
        """
        index = ['FRT_CONDITION', 'MIN_DURATION', 'FRT_VALUES']
        T0 = self.params["eut_startup_time"]
        test_sequences_df = pd.DataFrame(columns=index)
        test_sequences_df = test_sequences_df.append(test_condition["Step E"], ignore_index=True)
        test_sequences_df = test_sequences_df.append(test_condition["Step G"], ignore_index=True)
        test_sequences_df = test_sequences_df.append(test_condition["Step H"], ignore_index=True)

        test_sequences_df.loc[0, 'FRT_START_TIMING'] = T0
        # Calculate the timing sequences
        test_sequences_df.loc[0, 'FRT_END_TIMING'] = T0 + test_sequences_df.loc[0, 'MIN_DURATION']
        for i in range(1, len(test_sequences_df)):
            test_sequences_df.loc[i, 'FRT_START_TIMING'] = test_sequences_df.loc[i - 1, 'FRT_END_TIMING']
            test_sequences_df.loc[i, 'FRT_END_TIMING'] = test_sequences_df.loc[i, 'FRT_START_TIMING'] + \
                                                         test_sequences_df.loc[i, 'MIN_DURATION']
        return test_sequences_df

    def get_frt_stop_time(self, test_sequences_df):
        """
        Retrieves the stop time of the FRT test from the test sequence DataFrame.

        Parameters:
        -----------
        test_sequences_df (pd.DataFrame)    : The DataFrame containing the FRT test sequences.

        Returns:
        --------
        float
            The final end timing of the FRT test sequence.
        """
        return test_sequences_df["FRT_END_TIMING"].iloc[-1]

    def get_modes(self):
        """
        Returns the currently enabled FRT modes.

        Returns:
        --------
        list
            A list of modes that are currently enabled (e.g., LFRT, HFRT).
        """
        return self.params["modes"]

    def get_wfm_file_header(self):
        """
        Returns the waveform file headers used for logging test data.

        Returns:
        --------
        list
            A list of waveform file headers, including time, voltage, current, 
            and frequency command.
        """
        return self.wfm_header

    def extend_list_end(self, _list, extend_value, final_length):
        """
        Extends a list to a specified length with a given value.

        Parameters:
        -----------
        _list (list)            : The list to be extended.
        extend_value (any)      : The value to use for extending the list.
        final_length (int)      : The desired final length of the list.

        Returns:
        --------
        list
            The extended list.
        """
        list_length = len(_list)
        _list.extend([float(extend_value)] * (final_length - list_length))
        return _list

class PhaseChangeRideThrough(HilModel, EutParameters, DataLogging):
    def __init__(self, ts, support_interfaces):
        """
        Initializes the PhaseChangeRideThrough class.

        Parameters:
        -----------
        ts : object
            The test script environment used for parameter access.
        support_interfaces : list
            List of hardware support interfaces required for HIL testing.
        """
        EutParameters.__init__(self, ts)
        HilModel.__init__(self, ts, support_interfaces)
        self.wfm_header = None
        self._config()

    def _config(self):
        """
        Configures the initial setup for Phase Change Ride-Through tests.

        This method sets the PCRT parameters and waveform file header.
        """
        self.set_pcrt_params()
        self.set_wfm_file_header()

    """
    Setter functions
    """

    def set_pcrt_params(self):
        """
        Retrieves and sets the Phase Change Ride-Through (PCRT) parameters.

        Parameters are fetched from the test script environment and stored in
        the 'params' attribute.

        Raises:
        -------
        Exception
            If an incorrect parameter value is encountered during configuration.
        """
        try:
            # RT test parameters
            self.params["eut_startup_time"] = self.ts.param_value('eut.startup_time')
            self.params["model_name"] = self.hil.rt_lab_model
        except Exception as e:
            self.ts.log_error('Incorrect Parameter value : %s' % e)
            raise

    def extend_list_end(self, _list, extend_value, final_length):
        """
        Extends a list to a specified length with a given value.

        Parameters:
        -----------
        _list (list)            : The list to be extended.
        extend_value (float)    : The value to use for extending the list.
        final_length (int)      : The desired final length of the list.

        Returns:
        --------
        list
            The extended list.
        """
        list_length = len(_list)
        _list.extend([float(extend_value)] * (final_length - list_length))
        return _list

    def set_pcrt_model_parameters(self, test_sequence):
        """
        Sets the model parameters for the PCRT test based on the test sequence.

        Parameters:
        -----------
        test_sequence : pd.DataFrame
            A DataFrame containing the test sequence parameters, such as start 
            and end timings and condition values.
        """
        parameters = []

        # Enable pcrt mode in the IEEE1547_fast_functions model
        parameters.append(("MODE", 2.0))

        pcrt_condition_list = self.extend_list_end(test_sequence["PCRT_CONDITION"].to_list(), 0.0, 11)
        parameters.append(("PCRT_CONDITION", pcrt_condition_list))

        pcrt_start_timing_list = self.extend_list_end(test_sequence["PCRT_START_TIMING"].to_list(), 0.0, 11)
        parameters.append(("PCRT_START_TIMING", pcrt_start_timing_list))

        pcrt_end_timing_list = self.extend_list_end(test_sequence["PCRT_END_TIMING"].to_list(), 0.0, 11)
        parameters.append(("PCRT_END_TIMING", pcrt_end_timing_list))

        pcrt_values_list = self.extend_list_end(test_sequence["PCRT_VALUES"].to_list(), 0.0, 11)
        parameters.append(("PCRT_VALUES", pcrt_values_list))
        self.hil.set_matlab_variables(parameters)

    def set_wfm_file_header(self):
        """
        Sets the waveform file headers for data logging during the test.

        The header includes time, voltage, current, and phase commands.
        """
        self.wfm_header = ['TIME',
                           'AC_V_1', 'AC_V_2', 'AC_V_3',
                           'AC_I_1', 'AC_I_2', 'AC_I_3',
                           'AC_PH_CMD_1', 'AC_PH_CMD_2', 'AC_PH_CMD_3',
                           "TRIGGER"]

    def set_test_conditions(self, test_num):
        """
        Defines and returns the test conditions for a given test number.

        Parameters:
        -----------
        test_num : float
            The test number for which conditions are being set.

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing the test conditions and timing sequences.
        """
        # Set useful variables
        index = ['PCRT_CONDITION', 'MIN_DURATION', 'PCRT_VALUES']
        TEST_CONDITION = {}
        """
        Table 9 - PCRT test conditions (variation 1)
        +-------------+-------------------+-------------------+-------------------+----------------+
        | Test        | Phase A           | Phase B           | Phase C           |    Duration    |        
        | condition   | voltage angle     | voltage angle     | voltage angle     |                |                          
        +-------------+-------------------+-------------------+-------------------+----------------+
        |      A      |         0         |        120        |       240         |      30-40     |
        +-------------+-------------------+-------------------+-------------------+----------------+
        |      B      |      60 or 300    |        120        |       240         |   0.320-0.500  |
        +-------------+-------------------+-------------------+-------------------+----------------+
        |      C      |         0         |     60 or 180     |       240         |   0.320-0.500  |
        +-------------+-------------------+-------------------+-------------------+----------------+
        |      D      |         0         |        120        |    180 or 300     |   0.320-0.500  |
        +-------------+-------------------+-------------------+-------------------+----------------+
        |      E      |         20        |        140        |        260        |      55-65     |
        +-------------+-------------------+-------------------+-------------------+----------------+
        |      F      |        340        |        100        |        220        |      55-65     |
        +-------------+-------------------+-------------------+-------------------+----------------+
        NOTE 1: All single-phase angle values are specified in the same direction, leading or lagging relative to the initial
                phase angle of an arbitrarily assigned phase A during test condition A.
        NOTE 2: In some test cases two phase angles are given to allow for either forward (leading) or reverse (lagging)
                phase shift, and either test condition may be used.
        NOTE 3: The test condition G is the same as the condition A, it is used as a computationnal trick
        """
        
        TEST_CONDITION["A"] = pd.Series([1.0, 30, 0.0], index=index)
        TEST_CONDITION["G"] = pd.Series([1.0, 30, 0.0], index=index)
        TEST_CONDITION["B"] = pd.Series([2.0, 0.5, 60.0], index=index)
        TEST_CONDITION["C"] = pd.Series([3.0, 0.5, 60.0], index=index)
        TEST_CONDITION["D"] = pd.Series([4.0, 0.5, 60.0], index=index)
        TEST_CONDITION["E"] = pd.Series([5.0, 60.0, 20.0], index=index)
        TEST_CONDITION["F"] = pd.Series([6.0, 60.0, 20.0], index=index)
        test_sequences_df = self.get_test_sequence(test_num, TEST_CONDITION)

        return test_sequences_df

    """
    Getter functions
    """

    def get_test_sequence(self, test_num, test_condition):
        """
        Creates and returns a test sequence DataFrame based on the test number and conditions.

        Parameters:
        -----------
        test_num (float)            : The test number for which to create the sequence.
        test_condition (dict)       : A dictionary containing the test step conditions, including 
                                    condition type, minimum duration, and parameter values.

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing the sequence of test steps with start and 
            end timings.
        """
        index = ['PCRT_CONDITION', 'MIN_DURATION', 'PCRT_VALUES']
        T0 = self.params["eut_startup_time"]
        test_sequences_df = pd.DataFrame(columns=index)
        if 1.0 == test_num:
            # ABA
            test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["B"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["G"], ignore_index=True)
        elif 2.0 == test_num:
            # ACA
            test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["C"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["G"], ignore_index=True)
        elif 3.0 == test_num:
            # ADA
            test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["D"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["G"], ignore_index=True)
        elif 4.0 == test_num:
            # AEA
            test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["E"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["G"], ignore_index=True)
        else:
            # AFA
            test_sequences_df = test_sequences_df.append(test_condition["A"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["F"], ignore_index=True)
            test_sequences_df = test_sequences_df.append(test_condition["G"], ignore_index=True)

        test_sequences_df.loc[0, 'PCRT_START_TIMING'] = T0
        # Calculate the timing sequences
        test_sequences_df.loc[0, 'PCRT_END_TIMING'] = T0 + test_sequences_df.loc[0, 'MIN_DURATION']
        for i in range(1, len(test_sequences_df)):
            test_sequences_df.loc[i, 'PCRT_START_TIMING'] = test_sequences_df.loc[i - 1, 'PCRT_END_TIMING']
            test_sequences_df.loc[i, 'PCRT_END_TIMING'] = test_sequences_df.loc[i, 'PCRT_START_TIMING'] + \
                                                         test_sequences_df.loc[i, 'MIN_DURATION']
        return test_sequences_df

    def get_pcrt_stop_time(self, test_sequences_df):
        """
        Retrieves the stop time of the PCRT test from the test sequence DataFrame.

        Parameters:
        -----------
        test_sequences_df (pd.DataFrame)     : The DataFrame containing the PCRT test sequences.

        Returns:
        --------
        float
            The final end timing of the PCRT test sequence.
        """
        return test_sequences_df["PCRT_END_TIMING"].iloc[-1]

    def get_wfm_file_header(self):
        """
        Returns the waveform file headers used for logging test data.

        Returns:
        --------
        list
            A list of waveform file headers, including time, voltage, current, 
            and phase commands.
        """
        return self.wfm_header

    def get_rms_file_header(self):
        """
        Returns the RMS file headers used for logging test data.

        Returns:
        --------
        list
            A list of RMS file headers, including time, voltage, current, 
            power, reactive power, and phase commands.
        """

        rms_header = ['TIME',
                           'AC_V_1', 'AC_V_2', 'AC_V_3',
                           'AC_I_1', 'AC_I_2', 'AC_I_3',
                           'AC_P_1', 'AC_P_2', 'AC_P_3',
                           'AC_Q_1', 'AC_Q_2', 'AC_Q_3',
                           'AC_PH_CMD_1', 'AC_PH_CMD_2', 'AC_PH_CMD_3',
                           "TRIGGER"]

        return rms_header

if __name__ == "__main__":
    pass
