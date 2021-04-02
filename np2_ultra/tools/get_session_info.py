import os
import glob2
import xml.etree.ElementTree as ET
import numpy as np

class GetFilesForFigs():
    """runs in conda env ecephys"""
    def __init__(self, session_date, mouse_id, recording, probe, root_dir=r"\\10.128.54.155\Data"):
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

        data_dir = os.path.join(self.root_dir, "np2_data", self.s_id, 'recording{}'.format(self.recording), 'continuous')
        try:
            self.data_dir = glob2.glob(os.path.join(data_dir, 'Neuropix-PXI*{}'.format(self.pxiDict['forward'][self.probe])))[0]
        except IndexError:
            print("{} recording{} probe{} folder doesn't exist.".format(self.s_id, self.recording, self.probe))
            return

        self.analysis_dir = os.path.join(self.root_dir, "analysis", self.s_id, 'probe{}'.format(self.probe))
        self.data_dict = os.path.join(self.analysis_dir, "extracted_data_recording{}_probe{}.pkl".format(self.recording, self.probe))
        if os.path.exists(self.data_dict)==False:
            print("No analysis pkl for {} recording{} probe{}".format(self.s_id, self.recording, self.probe))
            return


    def get_session_info(self):
        params_dir = os.path.join(self.root_dir, "np2_data", self.s_id)
        params_file = glob2.glob(os.path.join(params_dir, "*sess_params.json"))
        with open(params_file) as f:
            self.session_params = json.load(f)
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
        return self.gain_factor, self.session_params


    def get_data_files(self):
        raw_data_file = os.path.join(self.data_dir, "continuous.dat")
        rawData = np.memmap(raw_data_file,dtype='int16',mode='r')
        self.raw_data = np.reshape(rawData, (int(rawData.size/384), 384)).T

        channel_pos_file =  os.path.join(self.data_dir, "channel_positions.npy")
        self.channel_pos = np.load(channel_pos_file)

        return self.raw_data, self.channel_pos

    def get_probe_info(self):
        num_channels = 384

        if self.probe=='A':
            probeRows = 4
            probeCols = 96

            x_spacing = 16
            x_start = 11
            probeX = np.arange(x_start,x_spacing*probeCols, x_spacing)

            y_spacing = 20
            n_row = probeRows*2
            y_start = 20
            probeY = np.arange(y_start, y_spacing*n_row+1, y_spacing)

        elif (self.probe=='C') or (self.probe=='E'):
            probeRows = 8
            probeCols = 48
            channelSpacing = 6 # microns
            probeX = np.arange(probeCols)*channelSpacing
            probeY = np.arange(probeRows)*channelSpacing


        return probeRows, probeCols, probeX, probeY






if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('session_date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--recording_nums', nargs="+", type=str, default=["1", "2", "3"])
    parser.add_argument('--probes', nargs="+", type=list, default=["C", "E"])
    args = parser.parse_args()
    batch_run(args.session_date, args.mouse_id, args.recording_nums, args.probes)
