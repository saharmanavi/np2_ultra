import os
import glob2
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

class GetFiles():
    """runs in conda env ecephys"""
    def __init__(self, session_date, mouse_id, recording=None, probe=None, root_dir=r"\\10.128.54.155\Data"):
        """recording: list of ints corresponding to the recording numbers, or 'all' to process all recorsings in session
            probe: list of probes to process, or 'all' to process all probes (A, C, E)"""
        self.root_dir = root_dir

        self.session_date = session_date
        self.mouse_id = mouse_id
        self.s_id = "{}_{}".format(self.session_date, self.mouse_id)
        self.recording = recording
        self.probe = probe
        self.pxiDict = {'forward': {'A': '.0', 'C':'.2', 'E': '.4'},
                        'reverse': {'.0': 'A', '.2': 'C', '.4': 'E'}}

    def get_directories(self):
        """gets paths for:
                session_dir: top level directory for the session data files,
                recording_dir: directory containing all recording folders for the session,
                probe_dir: directory containing all probe folders for the recording,
                data_dir: directory containing raw data and kilosort files for the recording/probe
                analysis_dir: top level directory for the session analysis files"""

        self.session_dir =  os.path.join(self.root_dir, "np2_data", self.s_id)
        self.analysis_dir = os.path.join(self.root_dir, "analysis", self.s_id)
        if (self.recording is not None) and (self.probe is not None):
            self.recording_dir = os.path.join(self.session_dir, 'recording{}'.format(self.recording))
            self.probe_dir = os.path.join(self.recording_dir, 'continuous')
            try:
                self.data_dir = glob2.glob(os.path.join(self.probe_dir, 'Neuropix-PXI*{}'.format(self.pxiDict['forward'][self.probe])))[0]
            except IndexError:
                print("{} recording{} probe{} folder doesn't exist.".format(self.s_id, self.recording, self.probe))
                return

    def get_data_dict(self):
        """data_dict: the waveform and opto data as a dictionary"""
        try:
            data_pkl = os.path.join(self.analysis_dir,"probe{}".format(self.probe), "extracted_data_recording{}_probe{}.pkl".format(self.recording, self.probe))
        except NameError:
            self.get_directories()
            data_pkl = os.path.join(self.analysis_dir,"probe{}".format(self.probe), "extracted_data_recording{}_probe{}.pkl".format(self.recording, self.probe))

        if os.path.exists(data_pkl)==False:
            print("No analysis pkl for {} recording{} probe{}".format(self.s_id, self.recording, self.probe))
            return
        else:
            self.data_dict = pd.read_pickle(data_pkl)

    def get_session_parameters(self):
        """session_params: session metadata and probe depths dictionary"""
        params_file = glob2.glob(os.path.join(self.session_dir, "*sess_params.json"))[0]
        with open(params_file) as f:
            self.session_params = json.load(f)

    def get_gain_factor(self):
        """gain_factor: probe gain factor as float"""
        try:
            xml_file = os.path.join(params_dir, "settings.xml")
            tree = ET.parse(xml_file)
            root = tree.getroot()
            gains = []
            for n, c in enumerate(root[1][0][0]):
                g = root[1][0][0][n].get('gain')
                gains.append(float(g))
            self.gain_factor = np.mean(gains)
        except:
            self.gain_factor = 0.19499999284744262695

    def get_raw_data(self):
        """raw_data: raw data as a numpy memmap array"""
        raw_data_file = os.path.join(self.data_dir, "continuous.dat")
        rawData = np.memmap(raw_data_file,dtype='int16',mode='r')
        self.raw_data = np.reshape(rawData, (int(rawData.size/384), 384)).T

    def get_channel_positions(self):
        """channel_pos: numpy array of channel positions"""
        channel_pos_file =  os.path.join(self.data_dir, "channel_positions.npy")
        self.channel_pos = np.load(channel_pos_file)

    def get_probe_info(self):
        """gets values for:
            probeX/probeY: range of X and Y values of probe as numpy arrays
            probeRows/probeCols: values of number of probe rows and columns as ints"""
        if self.probe=='A':
            probeRows = 96
            probeCols = 4

            x_spacing = 16
            x_start = 11
            probeX = np.arange(x_start,x_spacing*probeCols, x_spacing)

            y_spacing = 20
            n_row = probeRows*2
            y_start = 20
            probeY = np.arange(y_start, y_spacing*n_row+1, y_spacing)

        elif (self.probe=='C') or (self.probe=='E'):
            probeRows = 48
            probeCols = 8
            channelSpacing = 6 # microns
            probeX = np.arange(probeCols)*channelSpacing
            probeY = np.arange(probeRows)*channelSpacing

        self.probeRows = probeRows
        self.probeCols = probeCols
        self.probeX = probeX
        self.probeY = probeY

        return self.probeRows, self.probeCols, self.probeX, self.probeY
