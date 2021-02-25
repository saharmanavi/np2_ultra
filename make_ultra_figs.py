import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import glob2
import cv2
import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
matplotlib.rcParams['pdf.fonttype'] = 42

class make_ultra_figs():
    """runs in conda env ecephys"""
    def __init__(self, session_date, mouse_id, recording="all", probe="all", root_dir=r"\\10.128.54.155\Data"):
        self.root_dir = root_dir
        self.analysis_dir = os.path.join(self.root_dir, "analysis")
        self.data_dir = os.path.join(self.roo_dir, "np2_data")

        self.session_date = session_date
        self.mouse_id = mouse_id
        self.s_id = "{}_{}".format(self.mouse_id, self.session_date)
        self.pxiDict = {'A': '.0', 'C':'.2', 'E': '.4'}

        params_file = glob2.glob(os.path.join(self.data_dir, self.s_id, "*params.json"))[0]
        with open(params_file) as f:
            self.session_params = json.load(f)


    def get_files(self, mouse_id, session_date, probe, recording):

        p_id = "probe{}".format(probe)
        r_id = "recording{}".format(recording)

        dict_file = glob2.glob(os.path.join(root_analysis_dir, s_id, p_id, "*{}*".format(r_id)))[0]
        raw_data_file = glob2.glob(os.path.join(root_data_dir, s_id, r_id, "continuous", "*{}".format(pxiDict[probe]), "continuous.dat"))[0]

        data_dict = pd.read_pickle(dict_file)

        rawData = np.memmap(raw_data_file,dtype='int16',mode='r')
        if (probe=='C') or (probe=='E'):
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
