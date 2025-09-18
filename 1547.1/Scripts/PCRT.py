"""
The phase-angle change ride-through (PCRT) test verifies the ability of the EUT to ride through sudden voltage
phase-angle changes without tripping in accordance with the requirements in 6.5.2.6 of IEEE Std 1547-2018.

Initial Script: 2-4-20, jjohns2@sandia.gov

"""

import sys
import os
import traceback
from svpelab import gridsim
from svpelab import loadsim
from svpelab import pvsim
from svpelab import das
from svpelab import der
from svpelab import hil as hil_lib
from svpelab import p1547
import script
from svpelab import result as rslt
import time

TEST_NAME = {
    1: 'ABA',
    2: 'ACA',
    3: 'ADA',
    4: 'AEA',
    5: 'AFA'
}

def test_run():
    """
    The `test_run()` function is the main entry point for the phase-angle change ride-through (PCRT) test. 
    It verifies the ability of the EUT to ride through sudden voltage phase-angle changes without tripping 
    in accordance with the requirements in 6.5.2.6 of IEEE Std 1547-2018.

    This function initializes the necessary test equipment and components, configures the test parameters, 
    runs the PCRT test sequence, and captures the test data. It supports both hardware-in-the-loop (HIL) and 
    software-in-the-loop (SIL) testing environments.

    The function returns the overall test result, which can be either `script.RESULT_COMPLETE` or `script.RESULT_FAIL`.
    """


    """
    Table 9 - PCRT test conditions (variation 1)
    +---------------+------------------------+------------------------+------------------------+--------------+
    | Test condition| Phase A voltage angle  | Phase B voltage angle  | Phase C voltage angle  | Duration     |
    |               | (degrees, relative to  | (degrees, relative to  | (degrees, relative to  | (s)          |
    |               | initial phase A angle) | initial phase A angle) | initial phase A angle) |              |
    |               |      (See NOTE 1)      |                        |                        |              |
    +---------------+------------------------+------------------------+------------------------+--------------+
    |      A        |           0            |          120           |          240           | 30-40        |
    +---------------+------------------------+------------------------+------------------------+--------------+
    |      B        |       60 or 300        |          120           |          240           | 0.320-0.500  |
    +---------------+------------------------+------------------------+------------------------+--------------+
    |      C        |           0            |       60 or 180        |          240           | 0.320-0.500  |
    +---------------+------------------------+------------------------+------------------------+--------------+
    |      D        |           0            |          120           |       180 or 300       | 0.320-0.500  |
    +---------------+------------------------+------------------------+------------------------+--------------+
    |      E        |          20            |          140           |          260           | 55-65        |
    +---------------+------------------------+------------------------+------------------------+--------------+
    |      F        |          340           |          100           |          220           | 55-65        |
    +---------------+------------------------+------------------------+------------------------+--------------+
    NOTE 1 - All single-phase angle values are specified in the same direction, leading or lagging relative to the initial
             phase angle of an arbitrarily assigned phase A during test condition A.
    NOTE 2 - In some test cases two phase angles are given to allow for either forward (leading) or reverse (lagging)
             phase shift, and either test condition may be used.
    """



    result = script.RESULT_FAIL
    grid = None
    pv = p_rated = None
    daq = None
    eut = None
    rs = None
    hil = None
    result_summary = None
    step = None
    q_initial = None
    dataset_filename = None

    try:

        sink_power = ts.param_value('eut.sink_power')
        p_rated = ts.param_value('eut.p_rated')
        p_rated_prime = ts.param_value('eut.p_rated_prime')
        s_rated = ts.param_value('eut.s_rated')
        var_rated = ts.param_value('eut.var_rated')

        # DC voltages
        v_nom_in_enabled = ts.param_value('cpf.v_in_nom')
        v_min_in_enabled = ts.param_value('cpf.v_in_min')
        v_max_in_enabled = ts.param_value('cpf.v_in_max')

        v_nom_in = ts.param_value('eut.v_in_nom')
        v_min_in = ts.param_value('eut_cpf.v_in_min')
        v_max_in = ts.param_value('eut_cpf.v_in_max')

        # AC voltages
        v_nom = ts.param_value('eut.v_nom')
        v_min = ts.param_value('eut.v_low')
        v_max = ts.param_value('eut.v_high')
        f_nom = ts.param_value('eut.f_nom')
        p_min = ts.param_value('eut.p_min')
        p_min_prime = ts.param_value('eut.p_min_prime')
        phases = ts.param_value('eut.phases')

        test_num = ts.param_value('pcrt.test_num')
        n_iter = ts.param_value('pcrt.n_iter')
        eut_startup_time = ts.param_value('eut.startup_time')

        # initialize HIL environment, if necessary
        ts.log_debug(15 * "*" + "HIL initialization" + 15 * "*")

        hil = hil_lib.hil_init(ts)
        hil_setup = ts.params['hil.setup']

        if hil is not None and hil_setup == 'SIL':
            ts.log('Start simulation of hil')
            hil.start_simulation()

        """
         Configure settings in 1547.1 Standard module for the Voltage Ride Through Tests
        """
        PhaseRideThrough = p1547.PhaseChangeRideThrough(ts, support_interfaces={"hil": hil})
        # result params
        # result_params = lib_1547.get_rslt_param_plot()
        # ts.log(result_params
        # initialize the das

        if hil is not None and hil_setup == 'PHIL':
            ts.log('Start simulation of hil')
            hil.start_simulation()

        # grid simulator is initialized with test parameters and enabled
        ts.log_debug(15 * "*" + "Gridsim initialization" + 15 * "*")
        grid = gridsim.gridsim_init(ts, support_interfaces={"hil": hil})  # Turn on AC so the EUT can be initialized
        if grid is not None:
            grid.voltage(v_nom)

        # pv simulator is initialized with test parameters and enabled
        ts.log_debug(15 * "*" + "PVsim initialization" + 15 * "*")
        pv = pvsim.pvsim_init(ts, support_interfaces={'hil': hil})
        if pv is not None:
            pv.power_set(p_rated)
            pv.power_on()  # Turn on DC so the EUT can be initialized

        # initialize data acquisition
        ts.log_debug(15 * "*" + "DAS initialization" + 15 * "*")
        daq = das.das_init(ts, support_interfaces={"hil": hil})
        daq.waveform_config({"mat_file_name": "WAV.mat",
                             "wfm_channels": PhaseRideThrough.get_wfm_file_header()})
        if daq is not None:
            daq.sc['V_MEAS'] = 100
            """
            daq.sc['P_MEAS'] = 100
            daq.sc['Q_MEAS'] = 100
            daq.sc['Q_TARGET_MIN'] = 100
            daq.sc['Q_TARGET_MAX'] = 100
            daq.sc['PF_TARGET'] = 1
            daq.sc['event'] = 'None'
            ts.log('DAS device: %s' % daq.info())
            """

        if ts.param_value('pcrt.wav_ena') == "Yes":
            wav_ena = True
            if hil is not None:
                daq.waveform_capture(wav_ena)
        else:
            wav_ena = False
        if ts.param_value('pcrt.data_ena') == "Yes" :
            data_ena = True

        else:
            data_ena = False

        if ts.param_value('pcrt.rms_ena') == 'Yes':
            rms_ena = True
            if hil is not None:
                daq.data_capture(rms_ena)
        else:
            rms_ena = False

        PhaseRideThrough.set_daq(daq)
        """
        This test doesn't have specific procedure steps.
        """

        # open result summary file
        result_summary_filename = 'result_summary.csv'
        result_summary = open(ts.result_file_path(result_summary_filename), 'a+')
        ts.result_file(result_summary_filename)
        result_summary.write('Test Name, Waveform File, RMS File\n')

        # Wait to establish communications with the EUT after AC and DC power are provided
        eut = der.der_init(ts, support_interfaces={'hil': hil})

        if eut is not None:
            eut.config()

        for repetition in range(1, n_iter + 1):
            if hil.model_state() != 'Model Running':
                ts.log('Start simulation of hil')
                hil.config()
                hil.start_simulation()
            dataset_filename = f'PCRT_{TEST_NAME[test_num]}_{repetition}'
            ts.log_debug(15 * "*" + f"Starting {dataset_filename}" + 15 * "*")

            """
            Setting up available power to appropriate power level
            """
            if pv is not None:
                pv.iv_curve_config(pmp=p_rated, vmp=v_nom_in)
                pv.irradiance_set(1100.)

            """
            Initiating voltage sequence for pcrt
            """
            pcrt_test_sequences = PhaseRideThrough.set_test_conditions(test_num)
            ts.log_debug(pcrt_test_sequences)
            pcrt_stop_time = PhaseRideThrough.get_pcrt_stop_time(pcrt_test_sequences)
            if hil is not None:
                # This adds 5 seconds of nominal behavior for EUT normal shutdown. This 5 sec is not recorded.
                pcrt_stop_time = pcrt_stop_time + 5
                ts.log('Stop time set to %s' % hil.set_stop_time(pcrt_stop_time))
                # The driver should take care of this by selecting "Yes" to "Load the model to target?"
                hil.load_model_on_hil()
                # You need to first load the model, then configure the parameters
                # Now that we have all the test_sequences its time to sent them to the model.
                PhaseRideThrough.set_pcrt_model_parameters(pcrt_test_sequences)
                # The driver parameter "Execute the model on target?" should be set to "No"
                if pv is not None:
                    pv.power_set(p_rated)
                # ts.sleep(0.5)
                sim_time = hil.get_time()
                while (pcrt_stop_time - sim_time) > 1.0:  # final sleep will get to stop_time.
                    sim_time = hil.get_time()
                    ts.log('Sim Time: %0.3f.  Waiting another %0.3f sec before saving data.' % (
                        sim_time, pcrt_stop_time - sim_time))
                    time.sleep(5)
                hil.stop_simulation()
                time.sleep(10)
                rms_dataset_filename = "No File"
                wave_start_filename = "No File"
                if data_ena:
                    rms_dataset_filename = dataset_filename + "_RMS.csv"

                    # complete data capture
                    ts.log('Waiting for Opal to save the waveform data: {}'.format(dataset_filename))
                    ts.sleep(10)
                if wav_ena:
                    # Convert and save the .mat file
                    ts.log('Processing waveform dataset(s)')
                    wave_start_filename = dataset_filename + "_WAV.csv"

                    ds = daq.waveform_capture_dataset()  # returns list of databases of waveforms (overloaded)
                    ts.log(f'Number of waveforms to save {len(ds)}')
                    if len(ds) > 0:
                        ds[0].to_csv(ts.result_file_path(wave_start_filename))
                        ts.result_file(wave_start_filename)

                if rms_ena:
                    # Convert and save the .mat file
                    ts.log('Processing rms dataset(s)')
                    rms_start_filename = dataset_filename + "_RMS.csv"

                    ds = daq.waveform_capture_dataset()  # returns list of databases of waveforms (overloaded)
                    ts.log(f'Number of waveforms to save {len(ds)}')
                    if len(ds) > 0:
                        ds[0].to_csv(ts.result_file_path(rms_start_filename))
                        ts.result_file(rms_start_filename)

                if data_ena:
                    daq.waveform_config({"mat_file_name": "Data.mat",
                                         "wfm_channels": PhaseRideThrough.get_rms_file_header()})
                    ds = daq.waveform_capture_dataset()
                    ts.log('Saving file: %s' % rms_dataset_filename)
                    if len(ds) > 0:
                        ds[0].to_csv(ts.result_file_path(rms_dataset_filename))
                        # ds.remove_none_row(ts.result_file_path(rms_dataset_filename), "TIME")
                        result_params = {
                            'plot.title': rms_dataset_filename.split('.csv')[0],
                            'plot.x.title': 'Time (sec)',
                            'plot.x.points': 'TIME',
                            'plot.y.points': 'AC_VRMS_1, AC_VRMS_2, AC_VRMS_3',
                            'plot.y.title': 'Voltage (V)',
                            'plot.y2.points': 'AC_IRMS_1, AC_IRMS_2, AC_IRMS_3',
                            'plot.y2.title': 'Current (A)',
                        }
                        ts.result_file(rms_dataset_filename, params=result_params)
                result_summary.write('%s, %s, %s,\n' % (dataset_filename, wave_start_filename,
                                                        rms_dataset_filename))


        result = script.RESULT_COMPLETE

    except script.ScriptFail as e:

        reason = str(e)

        if reason:
            ts.log_error(reason)


    except Exception as e:

        ts.log_error((e, traceback.format_exc()))

        ts.log_error('Test script exception: %s' % traceback.format_exc())


    finally:

        if grid is not None:
            grid.close()

        if pv is not None:

            # if p_rated is not None:
            #     pv.power_set(p_rated)

            pv.close()

        if daq is not None:
            daq.close()

        if eut is not None:
            # eut.fixed_pf(params={'Ena': False, 'PF': 1.0})

            eut.close()

        if rs is not None:
            rs.close()

        if hil is not None:

            if hil.model_state() == 'Model Running':
                hil.stop_simulation()

            hil.close()

        if result_summary is not None:
            result_summary.close()

        # create result workbook

        excelfile = ts.config_name() + '.xlsx'

        rslt.result_workbook(excelfile, ts.results_dir(), ts.result_dir())

        ts.result_file(excelfile)

    return result


def run(test_script):
    """
    Runs the test script.

    This function is the entry point for the test script. It sets up the necessary global variables, logs debug information, and calls the `test_run()` 
    function to execute the test. If any exceptions occur during the test, it logs the error and sets the return code to 1. 
    

    Parameters:
        test_script (script.ScriptInfo): The test script object.

    Returns:
        int: The return code, 0 for success, 1 for failure.
    """

    try:
        global ts
        ts = test_script
        rc = 0
        result = script.RESULT_COMPLETE

        ts.log_debug('')
        ts.log_debug('**************  Starting %s  **************' % (ts.config_name()))
        ts.log_debug('Script: %s %s' % (ts.name, ts.info.version))
        ts.log_active_params()

        result = test_run()

        ts.result(result)
        if result == script.RESULT_FAIL:
            rc = 1

    except Exception as e:
        ts.log_error('Test script exception: %s' % traceback.format_exc())
        rc = 1

    sys.exit(rc)


info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.0')
# Data acquisition
info.param_group('pcrt', label='test parameters')
info.param('pcrt.test_num', label='Test Number (1-5)', default=1)
info.param('pcrt.n_iter', label='Number of Iterations', default=5)
info.param('pcrt.wav_ena', label='Waveform acquisition needed (.mat->.csv) ?', default='Yes', values=['Yes', 'No'])
info.param('pcrt.rms_ena', label='Fast RMS acquisition needed (.mat->.csv) ?', default='No', values=['Yes', 'No'])
info.param('pcrt.data_ena', label='RMS acquisition needed (SVP creates .csv from block queries)?', default='No', values=['Yes', 'No'])

# EUT general parameters
info.param_group('eut', label='EUT Parameters', glob=True)
info.param('eut.phases', label='Phases', default='Single Phase', values=['Single phase', 'Split phase', 'Three phase'])
info.param('eut.s_rated', label='Apparent power rating (VA)', default=10000.0)
info.param('eut.p_rated', label='Output power rating (W)', default=8000.0)
info.param('eut.p_min', label='Minimum Power Rating(W)', default=1000.)
info.param('eut.var_rated', label='Output var rating (vars)', default=2000.0)
info.param('eut.v_nom', label='Nominal AC voltage (V)', default=120.0, desc='Nominal voltage for the AC simulator.')
info.param('eut.v_low', label='Minimum AC voltage (V)', default=116.0)
info.param('eut.v_high', label='Maximum AC voltage (V)', default=132.0)
info.param('eut.v_in_nom', label='V_in_nom: Nominal input voltage (Vdc)', default=400)
info.param('eut.f_nom', label='Nominal AC frequency (Hz)', default=60.0)
info.param('eut.startup_time', label='EUT Startup time', default=10)
info.param('eut.scale_current', label='EUT Current scale input string (e.g. 30.0,30.0,30.0)', default="33.3400,33.3133,33.2567")
info.param('eut.offset_current', label='EUT Current offset input string (e.g. 0,0,0)', default="0,0,0")
info.param('eut.scale_voltage', label='EUT Voltage scale input string (e.g. 30.0,30.0,30.0)', default="20.0,20.0,20.0")
info.param('eut.offset_voltage', label='EUT Voltage offset input string (e.g. 0,0,0)', default="0,0,0")

# Add the SIRFN logo
info.logo('sirfn.png')

# Other equipment parameters
der.params(info)
gridsim.params(info)
pvsim.params(info)
das.params(info)
hil_lib.params(info)


def script_info():
    
    return info


if __name__ == "__main__":

    # stand alone invocation
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    params = None

    test_script = script.Script(info=script_info(), config_file=config_file, params=params)
    test_script.log('log it')

    run(test_script)


