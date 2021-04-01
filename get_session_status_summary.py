import os
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime


class SessionSummary():
    def __init__(self, save=False):
        """ save: bool, whether to save the df as a csv
        run generate_session_df to generate new summary df.
        run get_most_recent to load the most recently created summary df."""
        self.save = save
        self.data_dir = r"\\10.128.54.155\Data\np2_data"
        self.analysis_dir = r"\\10.128.54.155\Data\analysis"
        self.file_dir = r"\\10.128.54.155\Data\session_processing_status"
        self.pxiDict = {'.0': 'A', '.2': 'C', '.4':'E'}
        self.columns=["session", "recording", "probe", "dat_file", "rez.mat", "analysis_pkl", "flags"]

    def get_latest_in_dir(self, directory):
        """gets the most recently modified item in the directory"""
        times = {}
        for d in os.listdir(directory):
            dirname = os.path.join(directory, d)
            t = datetime.strptime(time.ctime(os.path.getmtime(dirname)), '%c')
            times[t] = d
        latest = np.max(list(times.keys()))
        latest_path = os.path.join(directory, times[latest])

        return latest_path

    def get_most_recent(self):
        self.csv_path = self.get_latest_in_dir(self.file_dir)
        df = pd.read_csv(self.csv_path)
        return df

    def generate_session_df(self):
        sessions = os.listdir(self.data_dir)
        check_df = pd.DataFrame(columns=self.columns)
        n=0
        for session in sessions:
            session_path = os.path.join(self.data_dir, session)
            analysis_path = os.path.join(self.analysis_dir, session)

            recordings = [d for d in os.listdir(session_path) if "recording" in d]
            for recording in recordings:
                recording_dir = os.path.join(session_path, recording, 'continuous')

                objects = []
                for root, dirs, files in os.walk(recording_dir):
                    objects.append((root, dirs, files))

                npx_folders = os.listdir(recording_dir)
                if len(npx_folders) != 6:
                    print("something is missing in {} {}. Maybe it's still transferring?".format(session, recording))
                    break

                probeA = [r for r in npx_folders if '.0' in r][0]
                probeC = [r for r in npx_folders if '.2' in r][0]
                probeE = [r for r in npx_folders if '.4' in r][0]

                for probe in [probeA, probeC, probeE]:
                    probe_session_files = [t for t in objects if probe in t[0]][0][2]
                    dat_file = "continuous.dat" in probe_session_files
                    mat_file = "rez.mat" in probe_session_files
                    flags_file = "flags.json" in probe_session_files
                    try:
                        analysis_loc = os.listdir(os.path.join(analysis_path, "probe{}".format(self.pxiDict[probe[-2:]])))
                        analysis_file = [f for f in analysis_loc if "{}_probe".format(recording) in f]
                    except FileNotFoundError:
                        analysis_file = []

                    check_df.at[n, 'session'] = session
                    check_df.at[n, 'recording'] = recording
                    check_df.at[n, 'probe'] = self.pxiDict[probe[-2:]]
                    check_df.at[n, 'dat_file'] = int(dat_file)
                    check_df.at[n, 'rez.mat'] = int(mat_file)
                    check_df.at[n, 'analysis_pkl'] = len(analysis_file)

                    if flags_file==True:
                        flags_loc = os.path.join([t for t in objects if probe in t[0]][0][0], 'flags.json')
                        with open(flags_loc, 'r') as f:
                            flags = json.load(f)
                            check_df.at[n, 'flags'] = flags['other_notes']

                    else:
                        check_df.at[n, 'flags'] = ""

                    n += 1
        check_df = check_df.set_index(['session', 'recording', 'probe'])
        self.df = check_df

        if self.save==True:
            self.save_csv()

    def save_csv(self):
        fname = 'np2_session_status_{}.csv'.format(datetime.strftime(datetime.today(), '%Y-%m-%d_%H%M'))
        save_path = os.path.join(self.file_dir, fname)

        self.df.to_csv(save_path)
        print('saved at {}'.format(save_path))


if __name__ == "__main__":
    SessionSummary(save=True).generate_session_df()
