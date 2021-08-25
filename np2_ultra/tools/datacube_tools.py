import os
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime

from np2_ultra.tools import io, file_tools


class SessionSummary():
    def __init__(self, save=False):
        """ save: bool, whether to save the df as a csv
        run generate_session_df to generate new summary df.
        run get_most_recent to load the most recently created summary df."""
        self.save = save
        self.computer_names = io.read_computer_names()
        self.pxi_dict = io.read_pxi_dict()

        self.data_dir = os.path.join(self.computer_names["dest_root"], "np2_data")
        self.analysis_dir = os.path.join(self.computer_names["dest_root"], "analysis")
        self.file_dir = os.path.join(self.computer_names["dest_root"], "session_processing_status")

        self.columns=["session", "recording", "probe", "dat_file", "rez.mat", "analysis_pkl", "flags", "genotype"]

    def get_latest_in_dir(self, directory):
        """gets the most recently modified item in the directory"""
        times = {}
        for d in os.listdir(directory):
            dirname = os.path.join(directory, d)
            t = os.path.getmtime(dirname)
            times[t] = d
        latest = np.max(list(times.keys()))
        latest_path = os.path.join(directory, times[latest])

        return latest_path

    def get_most_recent(self, return_filename=False):
        csv_path = self.get_latest_in_dir(self.file_dir)
        df = pd.read_csv(csv_path, index_col=0)
        if return_filename==True:
            return df, csv_path
        else:
            return df

    def generate_session_df(self):
        sessions = os.listdir(self.data_dir)
        check_df = pd.DataFrame(columns=self.columns)

        n=0
        for session in sessions:
            session_path = os.path.join(self.data_dir, session)
            analysis_path = os.path.join(self.analysis_dir, session)

            try:
                params_file = os.path.join(session_path, "{}_sess_params.json".format(session))
                with open(params_file, 'r') as p:
                    params = json.load(p)
                    genotype = params['genotype'].lower()
            except:
                if "saline" in session:
                    genotype = "saline"
                else:
                    genotype = "none"

            recordings = [d for d in os.listdir(session_path) if "recording" in d]
            for recording in recordings:
                recording_dir = os.path.join(session_path, recording, 'continuous')

                objects = []
                for root, dirs, files in os.walk(recording_dir):
                    objects.append((root, dirs, files))

                npx_folders = os.listdir(recording_dir)
                if len(npx_folders) < 6:
                    print("something is missing in {} {}. Maybe it's still transferring?".format(session, recording))
                    break


                for key in self.pxi_dict['reverse'].keys():
                    for folder in npx_folders:
                        if key in folder:
                            probe_session_files = [t for t in objects if folder in t[0]][0][2]
                            dat_file = "continuous.dat" in probe_session_files
                            mat_file = "rez.mat" in probe_session_files
                            flags_file = "flags.json" in probe_session_files
                            probe_letter = self.pxi_dict['reverse'][key]
                            try:
                                analysis_loc = os.listdir(os.path.join(analysis_path, "probe{}".format(probe_letter)))
                                analysis_file = [f for f in analysis_loc if "{}_probe".format(recording) in f]
                                try:
                                    analysis_file_loc = os.path.join(analysis_path, "probe{}".format(probe_letter), analysis_file[0])
                                except IndexError:
                                    analysis_file_loc = ''
                            except FileNotFoundError:
                                analysis_file = []
                                analysis_file_loc = ''

                            check_df.at[n, 'session'] = session
                            check_df.at[n, 'recording'] = recording
                            check_df.at[n, 'probe'] = probe_letter
                            check_df.at[n, 'dat_file'] = int(dat_file)
                            check_df.at[n, 'rez.mat'] = int(mat_file)
                            check_df.at[n, 'analysis_pkl'] = len(analysis_file)
                            check_df.at[n, 'genotype'] = genotype
                            check_df.at[n, 'data_folder'] = [t for t in objects if folder in t[0]][0][0]
                            check_df.at[n, 'analysis_file'] = analysis_file_loc

                            if flags_file==True:
                                flags_loc = os.path.join([t for t in objects if folder in t[0]][0][0], 'flags.json')
                                with open(flags_loc, 'r') as f:
                                    flags = json.load(f)
                                    try:
                                        check_df.at[n, 'flags'] = flags['other_notes']
                                    except KeyError:
                                        check_df.at[n, 'flags'] = 'generic flag'

                            else:
                                check_df.at[n, 'flags'] = " "

                            n += 1

        self.df = check_df
        if self.save==True:
            self.save_csv()

    def save_csv(self):
        fname = 'np2_session_status_{}.csv'.format(datetime.strftime(datetime.today(), '%Y-%m-%d_%H%M'))
        save_path = os.path.join(self.file_dir, fname)

        self.df.to_csv(save_path)
        print('saved at {}'.format(save_path))

    def get_data_cube(self):
        if 'df' not in dir(self):
            self.df, fn = self.get_most_recent(return_filename=True)
            print("using most recently saved session summary found here:")
            print(fn)

        datacube = self.df.groupby(['genotype','session', ]).count().reset_index().groupby('genotype').count()[['session']].reset_index()
        datacube.drop(index=datacube[datacube.genotype=='saline'].index, inplace=True)
        datacube.rename(columns={'session':'n_sessions'}, inplace=True)
        datacube.set_index('genotype', inplace=True)
        self.datacube = datacube
        return datacube

    def get_unprocessed_sessions(self, kilosort=True, analysis_pkl=True):
        if 'df' not in dir(self):
            self.df, fn = self.get_most_recent(return_filename=True)
            print("using most recently saved session summary found here:")
            print(fn)

        rows = []
        if kilosort==True:
            rows.append(self.df[(self.df['rez.mat']==0)&(self.df.flags==' ')&(self.df.genotype!='saline')])
        if analysis_pkl==True:
            rows.append(self.df[(self.df['analysis_pkl']==0)&(self.df.flags==' ')&(self.df.genotype!='saline')])

        if (kilosort==True) & (analysis_pkl==True):
            unprocessed = pd.concat(rows)
            unprocessed.reset_index(inplace=True)
            unprocessed.drop(index=unprocessed[unprocessed.duplicated(keep='first')==True].index, inplace=True)
            unprocessed = unprocessed.set_index('index').sort_index()
        else:
            unprocessed = rows[0]

        self.unprocessed = unprocessed
        return unprocessed

if __name__ == "__main__":
    SessionSummary(save=True).generate_session_df()
