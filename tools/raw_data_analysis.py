import os
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime

from allensdk.brain_observatory.ecephys.align_timestamps import barcode
from allensdk.brain_observatory.ecephys.align_timestamps import channel_states as cs
from allensdk.brain_observatory.sync_dataset import Dataset
from ..processing.ultra_tools import get_sync_line_data


def get_sync_data(sync_file):
    sync_data = Dataset(sync_file)
    barcode_channel = sync_data._line_to_bit('barcode_ephys')
    sample_freq_digital = float(100000)
    on_events = sync_data.get_rising_edges(barcode_channel)
    off_events = sync_data.get_falling_edges(barcode_channel)

    on_times = on_events / sample_freq_digital
    off_times = off_events / sample_freq_digital

    sync_barcode_times, sync_barcodes = barcode.extract_barcodes_from_times(on_times, off_times)
    return sync_data, sync_barcode_times

def get_ephys_data(dat_file, num_channels=384):
    raw_data = np.memmap(os.path.join(dat_file),dtype='int16',mode='r')
    data = np.reshape(raw_data, (int(raw_data.size/num_channels), num_channels))
    return data

def get_ephys_probeshift(events_dir, sync_barcode_times, probe_sample_rate=30000):
    channel_states = np.load(os.path.join(events_dir,'channel_states.npy'))
    event_times = np.load(os.path.join(events_dir,'timestamps.npy'))
    probe_barcode_times, probe_barcodes = cs.extract_barcodes_from_states(channel_states,
                                                                            event_times, probe_sample_rate)
    # compute time shift between ephys and sync
    probe_shift = sync_barcode_times[0] - probe_barcode_times[0]
    return probe_shift

def get_probe_time(probe_data, probe_shift, timestamp_0, probe_sample_rate=30000):
    probe_index = range(probe_data.shape[0]) + timestamp_0
    probe_times = np.divide(probe_index, probe_sample_rate)
    probe_times = np.add(probe_times, probe_shift)
    return probe_times

def get_opto_data(opto_file, sync_data):
    opto_data = pd.read_pickle(opto_file)
    # opto_sample_rate = 5000.
    opto_channel = sync_data._line_to_bit('stim_trial_opto')

    opto_on_times,opto_off_times = get_sync_line_data(sync_data,channel=opto_channel)
    return opto_data, opto_on_times

def get_opto_times_by_type(opto_dict, level=None, condition=None):
    if level==None:
        indxs = np.where(opto_dict['trial_conditions']==condition)[0]
    elif condition==None:
        indxs = np.where(opto_dict['trial_levels']==level)[0]
    else:
        indxs = np.where((opto_dict['trial_levels']==level)&(opto_dict['trial_conditions']==condition))[0]
    times = opto_dict['trial_start_times'][indxs]
    return times, indxs


def get_file_from_date(directory, date):
    """gets all files in directory with same create date as date listed.
    Date should be a string in YYYYMMDD format"""

    times = {}
    for d in os.listdir(directory):
        dirname = os.path.join(directory, d)
        t = datetime.strptime(time.ctime(os.path.getmtime(dirname)), '%c')
        times[t] = d

    files = []
    for k in times.keys():
        if date==datetime.strftime(k, "%Y%m%d"):
            files.append(times[k])

    return files


def get_opto_stim_table(sync_data, opto_pkl, opto_sample_rate=10000):
    """Code from Corbett"""
    trial_levels = opto_pkl['opto_levels']
    trial_conds = opto_pkl['opto_conditions']
    trial_start_times = sync_data.get_rising_edges('stim_trial_opto', units='seconds')

    waveforms = opto_pkl['opto_waveforms']
    trial_waveform_durations = [waveforms[cond].size/opto_sample_rate for cond in trial_conds]

    trial_end_times = trial_start_times + trial_waveform_durations

    trial_dict = {
            'trial_levels': trial_levels,
            'trial_conditions': trial_conds,
            'trial_start_times': trial_start_times,
            'trial_end_times': trial_end_times}

    return trial_dict

def get_lfp_suffixes(probe):
    if probe=='A':
        return '.1'
    elif probe=='C':
        return '.3'
    elif probe=='E':
        return '.5'
    else:
        return "No such probe in this experiment."

def get_data_slices(data, probe_times, opto_times, window_dur, pre_time, sampling_rate=30000):
    """data in shape (n_samples, n_channels)
        probe_times in seconds
        opto_times in seconds
        window_dur in seconds
        pre_time in seconds
        sampling rate is 30000 for AP band, 1000 for LFP backends

        returns: array of shape (n_opto_times, n_samples_in_window_dur, n_channels)"""

    values = np.empty((len(opto_times), int(window_dur*sampling_rate), 384))
    for n,time in enumerate(opto_times):
        on = np.where(probe_times>=time)[0][0]
        start = int(on - pre_time*sampling_rate)
        end = int(start + window_dur*sampling_rate)
        values[n] = data[start:end,:]

    return values
