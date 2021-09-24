import os
import glob2
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import json

import np2_ultra.tools.io as io


class GetFiles():
    def __init__(self, session_date, mouse_id, probes="all", recordings="all",
                        pxi_dict='default', opto_params='default', verbose=False):
        '''
        date: str
            The date of the session in YYYY-MM-DD format
        mouse_id: str
            The 6 digit mouse number
        probes: list, optional, default = 'all'
            Optionally only process a subset of probes in the session.
            Probes are ID'd by their letter and passed as a list of strings, eg ['A', 'E']
        recordings: list, optional, default = 'all'
            Optionally only process a subset of recordings in the session.
            Recordings are ID'd by the name of the recording folder and passed as a list of strings, eg ['recording2']
        pxi_dict: path, optional, default = 'default'
            Pass a path to a JSON containing a customized dictionary of mappings of probe letter to OpenEphys folder suffix.
            Default option runs the file located at ../files/pxi_dict.json
        opto_params: path, optional, default = 'default'
            Pass a path to a JSON containing a dictionary of opto PSTH parameters.
            Default option runs the file located at ../files/opto_params.json
        verbose: bool, optional, default=False
            If set to true, print statements will tell you names of variables set by the class.
        '''
        self.verbose = verbose
        self.computer_names = io.read_computer_names()

        self.pxi_dict = io.read_pxi_dict(path_to_json=pxi_dict)
        self.opto_params = io.read_opto_params(path_to_json=opto_params)

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
            self.recording_dirs = {d:os.path.join(self.session_dir, d) for d in os.listdir(self.session_dir) if "recording" in d}
        else:
            self.recording_dirs = {r:os.path.join(self.session_dir, r) for r in recordings}
        if self.verbose==True:
            print("The session recording directories are available as recording_dirs.")

    def get_probe_dirs(self, probes):
        '''
        Generate a dictionary of the probe directories to be processed for the session.
        '''
        if 'recording_dirs' not in dir(self):
            self.determine_recordings("all")
        probe_data_dirs = {}
        for recording in self.recording_dirs.keys():
            temp = {}
            pxi_dirs = os.listdir(os.path.join(self.recording_dirs[recording], 'continuous'))
            probe_dirs = [d for d in pxi_dirs if int(d[-1]) % 2 == 0]
            for probe in probe_dirs:
                key= probe[-2:]
                probe_letter = self.pxi_dict['reverse'][key]
                temp[probe_letter] = os.path.join(self.recording_dirs[recording], 'continuous', probe)
            recording_name = os.path.basename(recording)
            probe_data_dirs[recording_name] = temp

        to_drop = []
        if probes != "all":
            for recording in probe_data_dirs.keys():
                for key in probe_data_dirs[recording].keys():
                    if key not in probes:
                        to_drop.append((recording, key))
                        # probe_data_dirs[recording].pop(key)
        for drop in to_drop:
            probe_data_dirs[drop[0]].pop(drop[1])

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
        pkl_dir = os.path.join(self.analysis_dir, "probe{}".format(probe))
        try:
            pkl_file = [f for f in os.listdir(pkl_dir) if recording in f][0]
            self.data_dict = pd.read_pickle(os.path.join(pkl_dir, pkl_file))
            if self.verbose==True:
                print("Data dictionary returned as data_dict.")
        except IndexError:
            print("There is no analysis file for this recording/probe combo.")
            return

    def get_raw_data(self, recording, probe, band='spike'):
        """
        recording: str in format "recordingN" where N is the recording number
        probe: str in format of a capital letter indicating the probe cartridge position
        raw_data: raw data as a numpy memmap array
        """
        if self.probe_data_dirs==False:
            self.get_probe_dirs("all")
        if band=='spike':
            data_dir = self.probe_data_dirs[recording][probe]
        elif band=='lfp':
            data_dir = os.path.join()
        raw_data_file = os.path.join(data_dir, "continuous.dat")
        rawData = np.memmap(raw_data_file,dtype='int16',mode='r')
        raw_data = np.reshape(rawData, (int(rawData.size/384), 384)).T
        return raw_data

    def get_events_dir(self, probes, lfp=False):
        '''
        lfp: bool
            Currently does nothing.
        Gets the directory with the events files for the probe/recording
        '''
        if 'recording_dirs' not in dir(self):
            self.determine_recordings("all")
        event_data_dirs = {}
        for recording in self.recording_dirs.keys():
            temp = {}
            pxi_dirs = os.listdir(os.path.join(self.recording_dirs[recording], 'events'))
            event_dirs = [d for d in pxi_dirs if (int(d[-1]) % 2 == 0) & ("Neuropix" in d)]
            for event in event_dirs:
                key = event[-2:]
                probe_letter = self.pxi_dict['reverse'][key]
                temp[probe_letter] = glob2.glob(os.path.join(self.recording_dirs[recording], 'events', event, 'TTL*'))[0]
            recording_name = os.path.basename(recording)
            event_data_dirs[recording_name] = temp

        to_drop = []
        if probes != "all":
            for recording in event_data_dirs.keys():
                for key in event_data_dirs[recording].keys():
                    if key not in probes:
                        # event_data_dirs[recording].pop(key)
                        to_drop.append((recording, key))

        for drop in to_drop:
            event_data_dirs[drop[0]].pop(drop[1])

        self.event_dirs = event_data_dirs
        if self.verbose==True:
            print("The session event data directories are available as event_dirs.")

    def make_flags_json(self, recording, probe, text, skip_kilosort):
        """
        Create a flags JSON for the probe/recording combo.

        Parameters
        ----------
        recording: str
            Recording to check.
        probe: str
            Probe to check.
        text: str
            Descriptive text that will appear in the flags column of the session summary dataframe.
        skip_kilosort: bool
            whether Kilosort should be skipped for this recording/probe combo.
        """
        if 'probe_data_dirs' not in dir(self):
            self.get_probe_dirs("all")
        try:
            write_dir = self.probe_data_dirs[recording][probe]
        except KeyError:
            print("That probe/recording combo does not exist in this class instance. Rerun with optional probes, recordings args set to 'all'.")
        flag_text = {'skip_kilosort': skip_kilosort,
                    'other notes': text}
        flag_file = os.path.join(write_dir, 'flags.json')
        with open(flag_file, 'w') as t:
            json.dump(flag_text, t)

        print('file saved at: {}'.format(flag_file))
        print(flag_text)

    def get_flags_json(self, recording, probe):
        """
        Find the flags JSON for the recording/probe combo.

        Parameters
        ----------
        recording: str
            Recording to check.
        probe: str
            Probe to check.

        Returns
        ----------
        flags: dictionary
            The dictionary contained in the flags JSON file.
        """
        try:
            flags_file = os.path.join(self.probe_data_dirs[recording][probe], "flags.json")
            with open(flags_file, 'r') as f:
                flags = json.load(f)
            return flags
        except FileNotFoundError as e:
            print("Issue finding the flags json: {}".format(e))

    def get_kilosort_flag(self, recording, probe):
        """
        Read the kilosort flag (if any) for the recording/probe combo and determine whether to skip Kilosort.

        Parameters
        ----------
        recording: str
            Recording to check.
        probe: str
            Probe to check.

        Returns
        ----------
        skip_ks: bool
            Whether or not to skip Kilosort.
        """
        if 'saline' in self.mouse_id:
            skip_ks = True
        else:
            try:
                flags_file = os.path.join(self.probe_data_dirs[recording][probe], "flags.json")
                with open(flags_file, 'r') as f:
                    flags = json.load(f)
                    skip_ks = flags['skip_kilosort']
            except:
                skip_ks = False
        return skip_ks
