import os
import glob2
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import json

import io

class GetFiles():
    """runs in conda env ecephys"""
    def __init__(self, session_date, mouse_id, recordings="all", probes="all", verbose=False):
        """recording: list of ints corresponding to the recording numbers, or 'all' to process all recordings in session
            probe: list of probes to process, or 'all' to process all probes in session"""
        self.verbose = verbose
        self.computer_names = io.read_computer_names()
        self.pxiDict = io.read_pxi_dict()

        self.session_date = session_date
        self.mouse_id = mouse_id
        self.s_id = "{}_{}".format(self.session_date, self.mouse_id)
        self.root_dir = self.computer_names["dest_root"]

        self.get_base_dirs()


    def get_base_dirs(self):
        """gets paths for:
                root_dir: synology drive directory
                session_dir: top level directory for the session data files,
                analysis_dir: top level directory for the session analysis files"""
        self.root_dir = self.computer_names["dest_root"]
        self.session_dir =  os.path.join(self.root_dir, "np2_data", self.s_id)
        self.analysis_dir = os.path.join(self.root_dir, "analysis", self.s_id)
        if self.verbose==True:
            print("The session data directory is available as session_dir.")
            print("The analysis data directory is available as analysis_dir.")

    def determine_recordings(self, recordings):
        if recordings == "all":
            self.recording_dirs = [os.path.join(self.session_dir, d) for d in os.listdir(self.session_dir) if "recording" in d]
        else:
            self.recording_dirs = [os.path.join(self.session_dir, "recording{}".format(r)) for r in recordings]
        if self.verbose==True:
            print("The session recording directories are available as recording_dirs.")

    def get_probe_dirs(self, probes):
        probe_data_dirs = {}
        for recording in self.recording_dirs:
            temp = {}
            pxi_dirs = os.listdir(os.path.join(recording, 'continuous'))
            probe_dirs = [d for d in pxi_dirs if int(d[-1]) % 2 == 0]
            for probe in probe_dirs:
                key= probe[-2:]
                probe_letter = self.pxi_dict['reverse'][key]
                temp[probe_letter] = os.path.join(recording, 'continuous', probe)
            recording_name = os.path.basename(recording)
            probe_data_dirs[recording_name] = temp

        if probes != "all":
            for recording in probe_data_dirs.keys():
                for key in probe_data_dirs[recording].keys():
                    if key not in probes:
                        probe_data_dirs[recording].pop(key)

        self.probe_data_dirs = probe_data_dirs
        if self.verbose==True:
            print("The session probe data directories are available as probe_data_dirs.")


    def get_session_parameters(self):
        """SESSION-WIDE
        session_params: session metadata and probe depths dictionary"""
        try:
            params_file = glob2.glob(os.path.join(self.session_dir, "*sess_params.json"))[0]
            with open(params_file) as f:
                self.session_params = json.load(f)
            if self.verbose==True:
                print("Session parameters are available as session_params.")
        except IndexError:
            print("This session doesn't appear to have a params file.")

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
        if self.verbose==True:
            print("Gain factor returned as gain_factor.")


    def get_data_dict(self, recording, probe):
        """
        recording: str in format "recordingN" where N is the recording number
        probe: str in format of a capital letter indicating the probe cartridge position
        data_dict: the waveform and opto data as a dictionary
        """
        pkl_dir = os.path.join(self.analysis_dir, self.s_id, "probe{}".format(probe))
        try:
            pkl_file = [f for f in pkl_dir if recording[0] in f][0]
            self.data_dict = pd.read_pickle(pkl_file)
            if self.verbose==True:
                print("Data dictionary returned as data_dict.")
        except IndexError:
            print("There is no analysis file for this recording/probe combo.")
            return

    def get_raw_data(self, recording, probe):
        """
        recording: str in format "recordingN" where N is the recording number
        probe: str in format of a capital letter indicating the probe cartridge position
        raw_data: raw data as a numpy memmap array
        """
        data_dir = 
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
