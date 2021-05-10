import os
import glob2
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import json

class GetFiles():
    """runs in conda env ecephys"""
    def __init__(self, session_date, mouse_id, recordings="all", probes="all", root_dir=r"\\10.128.54.155\Data"):
        """recording: list of ints corresponding to the recording numbers, or 'all' to process all recordings in session
            probe: list of probes to process, or 'all' to process all probes (A, C, E)"""
        self.root_dir = root_dir

        self.session_date = session_date
        self.mouse_id = mouse_id
        self.s_id = "{}_{}".format(self.session_date, self.mouse_id)
        self.pxiDict = {'forward': {'A': '.0', 'C':'.2', 'E': '.4'},
                        'reverse': {'.0': 'A', '.2': 'C', '.4': 'E'},
                        'lfp': {'A':'.1', 'C':'.3', 'E':'.5'}}

        self.get_directories(probes, recordings)
        # self.get_session_parameters()
        self.get_gain_factor()


    def get_directories(self, probes, recordings):
        """gets paths for:
                session_dir: top level directory for the session data files,
                recording_dir: directory containing all recording folders for the session,
                probe_dir: directory containing all probe folders for the recording,
                data_dir: directory containing raw data and kilosort files for the recording/probe
                analysis_dir: top level directory for the session analysis files"""

        self.session_dir =  os.path.join(self.root_dir, "np2_data", self.s_id)
        self.analysis_dir = os.path.join(self.root_dir, "analysis", self.s_id)
        if probes == "all":
            self.probes = ['A', 'C', 'E']
        else:
            self.probes = probes

        if recordings == "all":
            self.recordings = [os.path.join(self.session_dir, d) for d in os.listdir(self.session_dir) if "recording" in d]
        else:
            self.recordings = [os.path.join(self.session_dir, "recording{}".format(r)) for r in recordings]

        data_dirs = {}
        for recording in self.recordings:
            temp = {}
            for probe in self.probes:
                try:
                    p = glob2.glob(os.path.join(recording, 'continuous', 'Neuropix-PXI*{}'.format(self.pxiDict['forward'][probe])))
                    temp[probe] = p[0]
                except IndexError:
                    print("{} recording{} probe{} folder doesn't exist.".format(self.s_id, self.recording, self.probe))
                    pass
            r_name = os.path.basename(recording)
            data_dirs[r_name] = temp
        self.data_dirs = data_dirs

    def get_session_parameters(self):
        """SESSION-WIDE
        session_params: session metadata and probe depths dictionary"""
        params_file = glob2.glob(os.path.join(self.session_dir, "*sess_params.json"))[0]
        with open(params_file) as f:
            self.session_params = json.load(f)

    def get_gain_factor(self):
        """SESSION-WIDE
        gain_factor: probe gain factor as float"""
        try:
            xml_file = os.path.join(self.session_dir, "settings.xml")
            tree = ET.parse(xml_file)
            root = tree.getroot()
            gains = []
            for n, c in enumerate(root[1][0][0]):
                g = root[1][0][0][n].get('gain')
                gains.append(float(g))
            self.gain_factor = np.mean(gains)
        except:
            self.gain_factor = 0.19499999284744262695


    def get_data_dict(self, probe, recording):
        """data_dict: the waveform and opto data as a dictionary"""
        # try:
        data_pkl = os.path.join(self.analysis_dir,"probe{}".format(probe), "extracted_data_{}_probe{}.pkl".format(recording, probe))
        # except NameError:
        #     self.get_directories()
        #     data_pkl = os.path.join(self.analysis_dir,"probe{}".format(self.probe), "extracted_data_recording{}_probe{}.pkl".format(self.recording, self.probe))

        if os.path.exists(data_pkl)==False:
            print("No analysis pkl for {} {} probe{}".format(self.s_id, recording, probe))
            return
        else:
            data_dict = pd.read_pickle(data_pkl)
            return data_dict

    def get_raw_data(self, data_dir):
        """raw_data: raw data as a numpy memmap array"""
        raw_data_file = os.path.join(data_dir, "continuous.dat")
        rawData = np.memmap(raw_data_file,dtype='int16',mode='r')
        raw_data = np.reshape(rawData, (int(rawData.size/384), 384)).T
        return raw_data

    def get_channel_positions(self, data_dir):
        """channel_pos: numpy array of channel positions"""
        channel_pos_file =  os.path.join(data_dir, "channel_positions.npy")
        channel_pos = np.load(channel_pos_file)
        return channel_pos

    def get_probe_info(self, probe):
        """gets values for:
            probeX/probeY: range of X and Y values of probe as numpy arrays
            probeRows/probeCols: values of number of probe rows and columns as ints"""
        if probe=='A':
            probeRows = 96
            probeCols = 4

            x_spacing = 16
            x_start = 11
            probeX = np.arange(x_start,x_spacing*probeCols, x_spacing)

            y_spacing = 20
            n_row = probeRows*2
            y_start = 20
            probeY = np.arange(y_start, y_spacing*n_row+1, y_spacing)

        elif (probe=='C') or (probe=='E'):
            probeRows = 48
            probeCols = 8
            channelSpacing = 6 # microns
            probeX = np.arange(probeCols)*channelSpacing
            probeY = np.arange(probeRows)*channelSpacing

        return probeRows, probeCols, probeX, probeY

    def get_events_dir(self, lfp=False):
        '''Gets the directory with the events files for the probe/recording'''
        if lfp==True:
            pxi_dict = self.pxiDict['lfp']
        else:
            pxi_dict = self.pxiDict['forward']
        events_dirs = {}
        for recording in self.recordings:
            temp = {}
            for probe in self.probes:
                events_dir = glob2.glob(os.path.join(recording, 'events', 'Neuropix-PXI*{}'.format(pxi_dict[probe]), 'TTL*'))[0]
                temp[probe] = events_dir
            r_name = os.path.basename(recording)
            events_dirs[r_name] = temp

        self.events_dirs = events_dirs
        return self.events_dirs
