import os
import glob2
import numpy as np
import pandas as pd
import time
import sys
import shutil
import json

sys.path.append(r"C:\Users\saharm\Documents\CODE\local_code")
from ultra_analysis_sahar import get_sync_line_data, getPSTH
from allensdk.brain_observatory.ecephys.align_timestamps import barcode
from allensdk.brain_observatory.ecephys.align_timestamps import channel_states as cs
from allensdk.brain_observatory.sync_dataset import Dataset

class GetUltraWaveforms():
    """runs in conda env ecephys"""
    def __init__(self, probe_label, session_date, mouse_id, recording_num, root_dir=r"\\10.128.54.155\Data"):
        self.pxiDict = {'A': {'ap': '.0', 'lfp': '.1'},
                        'C': {'ap': '.2', 'lfp': '.3'},
                        'E': {'ap': '.4', 'lfp': '.5'},}
        self.probe_label = probe_label
        self.recording_num = recording_num
        self.session_name = '{}_{}'.format(session_date, mouse_id)

        #all the paths
        self.recording_dir = os.path.join(root_dir, 'np2_data', self.session_name, "recording{}".format(recording_num))
        data_dirs = glob2.glob(os.path.join(self.recording_dir, 'continuous', "Neuropix-PXI-*{}".format(self.pxiDict[self.probe_label]['ap'])))
        try:
            self.data_dir = data_dirs[0]
        except IndexError:
            print("skipping recording {} for {}, looks like this folder doesn't exist".format(recording_num, self.session_name))
            return

        self.analysis_dir = os.path.join(root_dir, 'analysis', self.session_name, 'probe{}'.format(self.probe_label))
        events_dir = os.path.join(self.recording_dir, 'events', "Neuropix-PXI-*{}".format(self.pxiDict[self.probe_label]['ap']))
        self.events_dir = glob2.glob(os.path.join(events_dir, 'TTL*'))[0]
        if os.path.exists(self.analysis_dir)==False:
            os.makedirs(self.analysis_dir)
        self.syncFile = glob2.glob(os.path.join(self.recording_dir, '*sync.h5'))[0]
        self.optoPklFile = glob2.glob(os.path.join(self.recording_dir, '*opto.pkl'))[0]

        #parameters for waveform extraction
        self.numChannels = 384
        self.TW = 200 #total waveforms
        self.samplesPerSpike = 90
        self.preSamples = 30
        self.boots = 100

        #gather parameters
        self.params_dict = {'total_waveforms': self.TW,
                            'samplesPerSpike' : self.samplesPerSpike,
                            'preSamples' : self.preSamples,
                            'boots' : self.boots,}

        self.data_info = {'session_name': self.session_name,
                           'probe_label': self.probe_label,
                           'recording_number': self.recording_num}

    def run_it(self):
        start = time.time()
        self.skip_wvs = self.check_flags_file('skip_kilosort', self.data_dir, default_cond=False)
        if self.skip_wvs == True:
            print("Skipping {} {} {}, looks like there's a problem with this recording.".format(self.session_name, self.recording_num, self.probe_label))
            return
        else:
            print("Getting waveforms for {} {} {}.".format(self.session_name, self.recording_num, self.probe_label))
            try:
                self.get_all_ks_files()
            except FileNotFoundError:
                flag_text = {'skip_kilosort': True, 'other_notes': "a kilosort file was not found"}
                self.create_flags_txt(self.data_dir, flag_text)
                print("Skipping {} {} {} because {}".format(self.session_name, self.recording_num, self.probe_label, flag_text['other_notes']))
                return
            self.get_sync_data()
            self.get_waveforms()
            self.get_opto_data()
            self.save_data_dicts()
        end = time.time()
        print("Finished. That took {} seconds.".format(end-start))

    def create_flags_txt(self, folder_loc, flag_text):
        """folder_loc is the path to the folder where the continuous.dat file is for the probe/recording
        flag_text is a dictionary with common keys 'skip_kilosort' and 'other_notes'"""

        flag_file = os.path.join(folder_loc, "flags.json")
        with open(flag_file, 'w') as t:
            json.dump(flag_text, t)

    def fix_spike_times(self, spike_times_file, timestamps_file):
        spike_times = np.load(spike_times_file)
        if 'spike_times_old.npy' not in os.listdir(self.data_dir):
            shutil.copy(spike_times_file, os.path.join(os.path.dirname(spike_times_file), 'spike_times_old.npy'))
            t0 = np.load(timestamps_file)[0]
            spike_times = spike_times + t0
            np.save(spike_times_file, spike_times)
        spike_times_old = np.load(os.path.join(self.data_dir, 'spike_times_old.npy'))
        return spike_times, spike_times_old

    def check_flags_file(self, key, path_to_folder, default_cond=False):
        condition = default_cond
        flags_file = os.path.join(path_to_folder,'flags.json')
        if os.path.exists(flags_file):
            with open(flags_file, 'r') as f:
                flags = json.load(f)
                condition = flags[key]
        return condition

    def get_all_ks_files(self):
        clustersFile = os.path.join(self.data_dir,'spike_clusters.npy')
        spikeTimesFile = os.path.join(self.data_dir,'spike_times.npy')
        clusterAssignmentFile = os.path.join(self.data_dir, 'cluster_groups.csv')
        waveformsFile = os.path.join(self.data_dir, 'mean_waveforms.npy')
        channelMapFile = os.path.join(self.data_dir, 'channel_map.npy')

        channel_map = np.load(os.path.join(self.data_dir,  'channel_map.npy'))
        channel_positions = np.load(os.path.join(self.data_dir,  'channel_positions.npy'))

        rawData = np.memmap(os.path.join(self.data_dir,'continuous.dat'),dtype='int16',mode='r')
        self.data = np.reshape(rawData, (int(rawData.size/self.numChannels), self.numChannels))

        self.spike_times_opto, self.spike_times_wf = self.fix_spike_times(spikeTimesFile, os.path.join(self.recording_dir, 'timestamps.npy'))
        self.clusters = np.load(clustersFile)
        self.channelMap = np.squeeze(np.load(channelMapFile))
        self.cluster_nums = np.unique(self.clusters)

        if self.clusters.size > self.spike_times_wf.size:
            print('Cluster assignments outnumber spike times. Taking subset.')
            self.clusters = self.clusters[:spike_times.size]

        #make dictionary with cluster nums as keys and assigments (eg 'good' or 'mua') as values
        #changed by sahar to use kilosorts tsv file
        clusterIDs = pd.read_csv(os.path.join(self.data_dir,'cluster_KSLabel.tsv'),sep='\t', index_col='cluster_id')
        clusterAssignments = {}
        for row in clusterIDs.index:
            clusterAssignments[str(row)] = clusterIDs.loc[row, 'KSLabel']

        self.goodClusters = [int(c) for c in clusterAssignments.keys() if clusterAssignments[c]=='good']

    def signaltonoise(self, a, axis=0, ddof=0):
        a = np.asanyarray(a)
        m = a.mean(axis)
        sd = a.std(axis=axis, ddof=ddof)
        return np.where(sd == 0, 0, m/sd)

    def bootstrap_resample(self, X, n=None):
        """ Bootstrap resample an array.
        Sample with replacement.
        From analysis/sampling.py.
        Parameters
        ----------
        X : array_like
          data to resample
        n : int, optional
          length of resampled array, equal to len(X) if n==None
        Results
        -------
        returns X_resamples
        """
        if n == None:
            n = len(X)

        resample_i = np.floor(np.random.rand(n)*len(X)).astype(int)
        X_resample = X[resample_i]
        return X_resample

    def get_waveforms(self):
        #get waveforms
        waveforms_dict = {}
        for cluster_idx, cluster_num in enumerate(self.goodClusters):
            print('Analyzing cluster {}, number {} of {}'.format(cluster_num, cluster_idx+1, len(self.goodClusters)))

            in_cluster = np.where(self.clusters == cluster_num)[0]
            times_for_cluster = self.spike_times_wf[in_cluster]
            waveform_boots = np.zeros((self.boots,self.samplesPerSpike, self.numChannels))
            SNR_boots=np.zeros((self.boots,self.samplesPerSpike, self.numChannels))
            for i in range(self.boots):
                times_boot = self.bootstrap_resample(times_for_cluster,n=self.TW)
                waveforms = np.zeros((self.samplesPerSpike, self.numChannels, self.TW))

                badSpikes = []
                for wv_idx in range(0, self.TW):
                    peak_time = times_boot[wv_idx][0]
                    rawWaveform = self.data[int(peak_time-self.preSamples):int(peak_time+self.samplesPerSpike-self.preSamples),:]
                    if rawWaveform.shape[0] < self.samplesPerSpike:
                        badSpikes.append(wv_idx)
                        continue
                    else:
                        normWaveform = rawWaveform - np.tile(rawWaveform[0,:],(self.samplesPerSpike,1))
                        waveforms[:, :, wv_idx] = normWaveform
                if len(badSpikes) > 0:
                    waveforms = waveforms[:, :, np.setdiff1d(np.arange(self.TW), badSpikes)]
                SNR_boots[i,:,:]=self.signaltonoise(waveforms, axis=2)
                waveform_boots[i,:,:]=np.mean(waveforms,2)

            waveforms_dict[str(cluster_num)] = {'waveform': np.squeeze(np.mean(waveform_boots,0))[:, self.channelMap],
                                                'SNR': np.squeeze(np.mean(SNR_boots,0))[:, self.channelMap] }

            # print("{}: {}".format(cluster_num, np.sum(waveforms_dict[str(cluster_num)]['waveform'])))


        #add cluster spike times
        for n, key in enumerate(waveforms_dict.keys()):
            k  = int(key)
            in_cluster = np.where(self.clusters == k)[0]
            waveforms_dict[str(key)]['spike_times'] = np.squeeze(self.spike_times_opto[in_cluster]) / self.probeSampleRate + self.probeShift

        self.waveforms_dict = waveforms_dict


    def get_sync_data(self):
        self.syncDataset = Dataset(self.syncFile)
        self.probeSampleRate = 30000.
        # get barcodes from sync file
        barcode_channel = self.syncDataset._line_to_bit('barcode_ephys')
        sample_freq_digital = float(100000)
        on_events = self.syncDataset.get_rising_edges(barcode_channel)
        off_events = self.syncDataset.get_falling_edges(barcode_channel)

        on_times = on_events / sample_freq_digital
        off_times = off_events / sample_freq_digital

        self.sync_barcode_times, sync_barcodes = barcode.extract_barcodes_from_times(on_times, off_times)


        # get barcodes from ephys data
        channel_states = np.load(os.path.join(self.events_dir,'channel_states.npy'))
        event_times = np.load(os.path.join(self.events_dir,'timestamps.npy'))
        self.probe_barcode_times, probe_barcodes = cs.extract_barcodes_from_states(channel_states,
                                                                                event_times, self.probeSampleRate)

        # compute time shift between ephys and sync
        self.probeShift = self.sync_barcode_times[0] - self.probe_barcode_times[0]

    def get_opto_data(self):
        # optotagging
        self.optoPklData = pd.read_pickle(self.optoPklFile)

        optoSampleRate = 5000.
        opto_channel = self.syncDataset._line_to_bit('stim_trial_opto')
        # self.optoOnTimes = self.syncDataset.get_rising_edges(opto_channel)
        # optoOffTimes = self.syncDataset.get_falling_edges(opto_channel)
        self.optoOnTimes,optoOffTimes = get_sync_line_data(self.syncDataset,'stim_trial_opto')

        optoConditions = np.unique(self.optoPklData['opto_conditions'])
        optoLevels = np.unique(self.optoPklData['opto_levels'])
        cmap = np.ones((len(optoLevels),3))
        cmap[:,:2] = np.arange(0,1.01-1/len(optoLevels),1/len(optoLevels))[::-1,None]
        self.preTime = 0.5
        self.windowDur = 2

        opto_response_dict = {}
        for cond in np.unique(self.optoPklData['opto_conditions']):
            cond_dict = {}
            for level in np.unique(self.optoPklData['opto_levels']):
                level_dict = {}
                for cluster in self.goodClusters:
                    optoTrials = (self.optoPklData['opto_conditions']==cond) & (self.optoPklData['opto_levels']==level)
                    psth,tp = getPSTH(self.waveforms_dict[str(cluster)]['spike_times'],self.optoOnTimes[optoTrials]-self.preTime,
                                            self.windowDur,binSize=0.01)
                    level_dict[cluster] = {'psth': psth, 'times':tp}
                cond_dict[level] = level_dict
            cond_key = "stim_{}".format(cond)
            opto_response_dict[cond_key] = cond_dict
            opto_response_dict[cond_key]['stim_waveform'] = self.optoPklData['opto_waveforms'][cond]
        opto_response_dict['window_dur'] = self.windowDur
        opto_response_dict['pre_time'] = self.preTime
        self.opto_response_dict = opto_response_dict

    def save_data_dicts(self):
        save_dict = {'extraction_params': self.params_dict,
                    'cluster_data': self.waveforms_dict,
                    'data_info': self.data_info,
                    'good_clusters': self.goodClusters,
                    'opto_data': self.opto_response_dict}

        self.data_dict = save_dict
        pd.to_pickle(save_dict, os.path.join(self.analysis_dir, 'extracted_data_recording{}_probe{}.pkl'.format(self.recording_num,self.probe_label)))
        print('data dictionary saved in {}'.format(self.analysis_dir))


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('json_params', type=str)
    args, _ = parser.parse_known_args()

    with open(args.json_params, 'r') as f:
        json_params = json.load(f)

    runner = GetUltraWaveforms(**json_params)
    runner.run_it()
