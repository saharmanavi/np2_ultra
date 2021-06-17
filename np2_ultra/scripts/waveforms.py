import os
import glob2
import numpy as np
import pandas as pd
import time
import sys
import shutil
import json

from np2_ultra.tools import io, file_tools
import np2_ultra.tools.analysis_tools as ant

from allensdk.brain_observatory.ecephys.align_timestamps import barcode
from allensdk.brain_observatory.ecephys.align_timestamps import channel_states as cs
from allensdk.brain_observatory.sync_dataset import Dataset

class GetWaveforms():
    """runs in conda env ecephys"""
    def __init__(self, date, mouse_id, probes_to_run='all', recordings_to_run='all', use_json_params=None):
        self.date = date
        self.mouse_id = mouse_id
        self.computer_names = io.read_computer_names()
        self.pxi_dict = io.read_pxi_dict()


        self.get_directories(recordings = recordings_to_run, probes = probes_to_run)
        self.waveform_extraction_params(use_json_params=use_json_params)

    def run_it(self):
        for recording in self.recording_dirs.keys():
            self.get_recording_sync_opto(recording)

            for probe in self.probe_data_dirs[recording].keys():
                print("--------Starting probe {} for {}--------".format(probe, recording))
                self.get_recording_and_probe(recording, probe)
                self.get_all_ks_files(recording, probe)
                self.get_probe_sync_data(recording, probe)
                self.get_waveforms(recording, probe)
                self.get_opto_data()
                self.save_data_dicts(recording, probe)


    def get_directories(self, recordings, probes):
        self.get_files = file_tools.GetFiles(self.date, self.mouse_id)
        self.get_files.determine_recordings(recordings=recordings)
        self.recording_dirs = self.get_files.recording_dirs
        self.get_files.get_probe_dirs(probes=probes)
        self.probe_data_dirs = self.get_files.probe_data_dirs
        self.get_files.get_events_dir(probes=probes)
        self.events_dirs = self.get_files.event_dirs
        self.analysis_dir = self.get_files.analysis_dir
        if os.path.exists(self.analysis_dir)==False:
            os.makedirs(self.analysis_dir)
        self.session_name = self.get_files.s_id


    #parameters for waveform extraction
    def waveform_extraction_params(self, use_json_params=None):
        if use_json_params is not None:
            with open(use_json_params, 'r') as params:
                extraction_params = json.load(params)
        else:
            extraction_params = {
                                'n_channels': 384,
                                'tot_waveforms': 200, #total waveforms
                                'samples_per_spike': 90,
                                'pre_samples': 30,
                                'n_boots': 100
                                }
        self.extraction_params = extraction_params

    def get_recording_sync_opto(self, recording):
        recording_folder = self.recording_dirs[recording]

        sync_file = glob2.glob(os.path.join(recording_folder, '*sync.h5'))[0]
        self.sync_dataset = Dataset(sync_file)
        self.probe_sample_rate = 30000.

        barcode_channel = self.sync_dataset._line_to_bit('barcode_ephys')
        sample_freq_digital = self.sync_dataset.sample_freq

        on_events = self.sync_dataset.get_rising_edges(barcode_channel)
        off_events = self.sync_dataset.get_falling_edges(barcode_channel)
        on_times = on_events / sample_freq_digital
        off_times = off_events / sample_freq_digital

        self.sync_barcode_times, self.sync_barcodes = barcode.extract_barcodes_from_times(on_times, off_times)

        opto_pkl = glob2.glob(os.path.join(recording_folder, '*opto.pkl'))[0]
        self.opto_data = pd.read_pickle(opto_pkl)
        self.opto_on_times,opto_off_times = ant.get_sync_line_data(self.sync_dataset,'stim_trial_opto')

    def get_recording_and_probe(self, recording, probe):
        self.session_info = {'session_name': self.session_name,
                           'probe_label': probe,
                           'recording_number': recording}


    def get_all_ks_files(self, recording, probe):
        '''
        This is done 1 recording/probe at a time.
        '''
        data_dir = self.probe_data_dirs[recording][probe]
        ks_file_dict = {'spike_clusters': 'spike_clusters.npy',
                        'spike_times': 'spike_times.npy',
                        'channel_map': 'channel_map.npy',}

        timestamps_file = os.path.join(self.recording_dirs[recording], 'timestamps.npy')
        self.recording_timestamp_zero  = np.load(timestamps_file)[0]
        self.spike_times_opto, self.spike_times_wf= ant.fix_spike_times(os.path.join(data_dir, ks_file_dict['spike_times']),
                                                                        timestamps_file,
                                                                        data_dir)
        self.clusters = np.load(os.path.join(data_dir, ks_file_dict['spike_clusters']))
        self.channel_map = np.squeeze(np.load(os.path.join(data_dir, ks_file_dict['channel_map'])))

        if self.clusters.size > self.spike_times_wf.size:
            print('Cluster assignments outnumber spike times. Taking subset.')
            self.clusters = self.clusters[:self.spike_times_wf.size]

        cluster_IDs = pd.read_csv(os.path.join(data_dir,'cluster_KSLabel.tsv'),sep='\t', index_col='cluster_id')
        cluster_assignments = {}
        for row in cluster_IDs.index:
            cluster_assignments[str(row)] = cluster_IDs.loc[row, 'KSLabel']

        self.good_clusters = [int(c) for c in cluster_assignments.keys() if cluster_assignments[c]=='good']


    def get_waveforms(self, recording, probe):
        '''
        This is done 1 recording/probe at a time.
        '''

        data = self.get_files.get_raw_data(recording, probe).T
        waveforms_dict = {}
        for cluster_idx, cluster_num in enumerate(self.good_clusters):
            print('Analyzing cluster {}, number {} of {}'.format(cluster_num, cluster_idx+1, len(self.good_clusters)))

            in_cluster = np.where(self.clusters == cluster_num)[0]
            times_for_cluster = self.spike_times_wf[in_cluster]
            waveform_boots = np.zeros((self.extraction_params['n_boots'],
                                        self.extraction_params['samples_per_spike'],
                                        self.extraction_params['n_channels']))

            SNR_boots=np.zeros(waveform_boots.shape)

            for i in range(self.extraction_params['n_boots']):
                times_boot = ant.bootstrap_resample(times_for_cluster, n=self.extraction_params['tot_waveforms'])
                waveforms = np.zeros((self.extraction_params['samples_per_spike'],
                                    self.extraction_params['n_channels'],
                                    self.extraction_params['tot_waveforms']))

                bad_spikes = []
                for wv_idx in range(0, self.extraction_params['tot_waveforms']):
                    peak_time = times_boot[wv_idx][0]
                    raw_waveform = data[int(peak_time-self.extraction_params['pre_samples']):int(peak_time+self.extraction_params['samples_per_spike']-self.extraction_params['pre_samples']),:]
                    if raw_waveform.shape[0] < self.extraction_params['samples_per_spike']:
                        bad_spikes.append(wv_idx)
                        continue
                    else:
                        norm_waveform = raw_waveform - np.tile(raw_waveform[0,:],(self.extraction_params['samples_per_spike'],1))
                        waveforms[:, :, wv_idx] = norm_waveform
                if len(bad_spikes) > 0:
                    waveforms = waveforms[:, :, np.setdiff1d(np.arange(self.extraction_params['tot_waveforms']), bad_spikes)]
                SNR_boots[i,:,:]=ant.signaltonoise(waveforms, axis=2)
                waveform_boots[i,:,:]=np.mean(waveforms,2)

            waveforms_dict[str(cluster_num)] = {'waveform': np.squeeze(np.mean(waveform_boots,0))[:, self.channel_map],
                                                'SNR': np.squeeze(np.mean(SNR_boots,0))[:, self.channel_map] }

        for n, key in enumerate(waveforms_dict.keys()):
            k  = int(key)
            in_cluster = np.where(self.clusters == k)[0]
            waveforms_dict[str(key)]['spike_times'] = np.squeeze(self.spike_times_opto[in_cluster]) / self.probe_sample_rate - self.probeShift

        self.waveforms_dict = waveforms_dict


    def get_probe_sync_data(self, recording, probe):
        # get barcodes from ephys data
        events_folder = self.events_dirs[recording][probe]
        channel_states = np.load(os.path.join(events_folder,'channel_states.npy'))
        event_times = np.load(os.path.join(events_folder,'timestamps.npy'))
        event_times = event_times - self.recording_timestamp_zero
        probe_barcode_times, probe_barcodes = cs.extract_barcodes_from_states(channel_states,
                                                                                event_times, self.probe_sample_rate)
        # compute time shift between ephys and sync
        self.probeShift, __, ___ = barcode.get_probe_time_offset(master_times = self.sync_barcode_times,
                                                        master_barcodes = self.sync_barcodes,
                                                        probe_times = probe_barcode_times,
                                                        probe_barcodes = probe_barcodes,
                                                        acq_start_index = 0,
                                                        local_probe_rate = self.probe_sample_rate,
                                                        )


    def get_opto_data(self):
        # optotagging
        pre_time = 0.5
        window_dur = 2
        opto_response_dict = {}
        for cond in np.unique(self.opto_data['opto_conditions']):
            cond_dict = {}
            for level in np.unique(self.opto_data['opto_levels']):
                level_dict = {}
                for cluster in self.good_clusters:
                    opto_trials = (self.opto_data['opto_conditions']==cond) & (self.opto_data['opto_levels']==level)
                    psth,tp = ant.getPSTH(self.waveforms_dict[str(cluster)]['spike_times'],
                                        self.opto_on_times[opto_trials]-pre_time,
                                        window_dur,
                                        binSize=0.01)
                    level_dict[cluster] = {'psth': psth, 'times':tp}
                cond_dict[level] = level_dict
            cond_key = "stim_{}".format(cond)
            opto_response_dict[cond_key] = cond_dict
            opto_response_dict[cond_key]['stim_waveform'] = self.opto_data['opto_waveforms'][cond]
        opto_response_dict['window_dur'] = window_dur
        opto_response_dict['pre_time'] = pre_time
        self.opto_response_dict = opto_response_dict

    def save_data_dicts(self, recording, probe):
        save_dict = {'extraction_params': self.extraction_params,
                    'cluster_data': self.waveforms_dict,
                    'session_info': self.session_info,
                    'good_clusters': self.good_clusters,
                    'opto_data': self.opto_response_dict}

        self.data_dict = save_dict
        save_folder = os.path.join(self.analysis_dir, "probe{}".format(probe))
        if os.path.exists(save_folder)==False:
            os.makedirs(save_folder)
        pd.to_pickle(save_dict, os.path.join(save_folder, 'extracted_data_{}_probe{}.pkl'.format(recording, probe)))
        print('data dictionary saved in {}'.format(save_folder))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--probes_to_run', nargs="+", default='all')
    parser.add_argument('--recordings_to_run', nargs="+", default='all')
    parser.add_argument('--use_json_params', nargs="+", type=str, default=None)
    args = parser.parse_args()

    runner = GetWaveforms(args.date, args.mouse_id, args.probes_to_run, args.recordings_to_run, args.use_json_params)
    runner.run_it()
