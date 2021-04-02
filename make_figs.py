import os
import xml.etree.ElementTree as ET
import glob2
import json
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns
import itertools
import cv2
import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
matplotlib.rcParams['pdf.fonttype'] = 42



class MakeFigs():
    """runs in conda env ecephys"""
    def __init__(self, session_date, mouse_id, recording="all", probe="all", root_dir=r"\\10.128.54.155\Data"):
        """recording: list of ints corresponding to the recording numbers, or 'all' to process all recorsings in session
            probe: list of probes to process, or 'all' to process all probes (A, C, E)"""
        self.root_dir = root_dir

        self.session_date = session_date
        self.mouse_id = mouse_id
        self.s_id = "{}_{}".format(self.session_date, self.mouse_id)
        self.data_dir = os.path.join(self.root_dir, "np2_data", self.s_id)
        self.analysis_dir = os.path.join(self.root_dir, "analysis", self.s_id)

        if recording == 'all':
            self.recordings = [d for d in os.listdir(self.data_dir) if 'recording' in d]
        else:
            self.recordings = ["recording{}".format(r) for r in recording]

        if probe == 'all':
            self.probes = ['A', 'C', 'E']
        else:
            self.probes = probe

        self.pxiDict = {'forward': {'A': '.0', 'C':'.2', 'E': '.4'},
                        'reverse': {'.0': 'A', '.2': 'C', '.4': 'E'}}

        # self.data_dir = os.path.join(self.root_dir, "np2_data", self.s_id, 'recording{}'.format(recording), 'continuous')

    def run_it(self):
        for rec in self.recordings:
            fol = os.path.join(self.data_dr, rec, 'continuous')
            for p in self.probes:
                try:
                    data_loc = os.path.join(fol, [f for f in os.listdir(fol) if self.pxiDict['forward'][p] in f][0])
                except IndexError:
                    print("data folder for {} probe{} doesn't seem to exist".format(recording, probe))
                    break
                analysis_loc = os.path.join(self.analysis_dir, "probe{}".format(p))

                gain_factor, session params = self.get_session_info(data_loc)
                data_dict, raw_data = self.get_recording_probe_files(rec, p, data_loc, analysis_loc)


    def get_session_info(self, data_loc):
        params_file = os.path.join(data_loc, "*params.json")
        with open(params_file) as f:
            session_params = json.load(f)
        try:
            xml_file = os.path.join(data_loc, "*params.json")
            tree = ET.parse(xml_file)
            root = tree.getroot()
            gains = []
            for n, c in enumerate(root[1][0][0]):
                g = root[1][0][0][n].get('gain')
                gains.append(float(g))
            gain_factor = np.mean(gains)

        except:
            gain_factor = 0.19499999284744262695
        return gain_factor, session_params


    def get_recording_probe_files(self, recording, probe, data_loc, analysis_loc):
        try:
            dict_file_loc = os.path.join(analysis_loc, "probe{}".format(probe))
            dict_file = [f for f in os.listdir(dict_file_loc) if recording in f][0]
            dict_file = os.path.join(dict_file_loc, dict_file)
        except IndexError:
            print("The analysis pickle for {} probe{} doesn't exist.".format(recording, probe))
            break

        raw_data_file = os.path.join(data_loc, "continuous.dat")
        data_dict = pd.read_pickle(dict_file)

        rawData = np.memmap(raw_data_file,dtype='int16',mode='r')
        raw_data = np.reshape(rawData, (int(rawData.size/384), 384)).T

        return data_dict, raw_data





if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('session_date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--recording_nums', nargs="+", type=str, default=["1", "2", "3"])
    parser.add_argument('--probes', nargs="+", type=list, default=["C", "E"])
    args = parser.parse_args()
    batch_run(args.session_date, args.mouse_id, args.recording_nums, args.probes)
