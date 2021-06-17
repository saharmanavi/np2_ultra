import os
import glob2
from datetime import datetime
import time
import shutil
import json
import matlab.engine

from np2_ultra.tools import io, file_tools
import np2_ultra.files as files

class RunKilosort():
    def __init__(self, date, mouse_id, probes_to_run='all', recordings_to_run='all'):
        '''
        date: string, 'YYYY-MM-DD' or 'today' to run with today's date
        mouse_id: string,
        probes_to_run: if not 'all' then must be a list of capital letters eg ['A']
        recordings_to_run: if not 'all' then must be a list of strings in format 'recordingN' eg ['recording1']
        '''
        self.date = date
        self.mouse_id = mouse_id
        self.probes = probes_to_run
        self.recordings = recordings_to_run
        self.computer_names = io.read_computer_names()
        self.pxi_dict = io.read_pxi_dict()

        self.get_all_file_locations()
        self.run_kilosort()

    def get_all_file_locations(self):
        self.get_files = file_tools.GetFiles(self.date, self.mouse_id)
        self.main_folder = self.get_files.session_dir
        self.bad_dats_txt = os.path.join(self.main_folder, "bad_dat_files.txt")
        self.get_files.get_probe_dirs(probes='all')
        self.probe_dict = self.get_files.probe_data_dirs
        self.path_to_ks_one_oh, self.path_to_ks_ultra = io.get_paths_to_kilosort_templates()

    def skip_ks_flag(self, probe_dir):
        if 'saline' in self.mouse_id:
            skip_ks = True
        else:
            try:
                flags_file = glob2.glob(os.path.join(probe_dir, "flags.json"))[0]
                with open(flags_file, 'r') as f:
                    flags = json.load(f)
                    skip_ks = flags['skip_kilosort']
            except Exception as e:
                skip_ks = False
        return skip_ks

    def write_ks_file(self, probe_dir):
        if '.0' in probe_dir:
            session_file = os.path.join(self.main_folder, "kilosort_one_oh_session.m")
            if os.path.exists(session_file)==False:
                shutil.copy(self.path_to_ks_one_oh, session_file)
        else:
            session_file = os.path.join(self.main_folder, "kilosort_ultra_session.m")
            if os.path.exists(session_file)==False:
                shutil.copy(self.path_to_ks_ultra, session_file)

        with open(session_file, "r") as f:
            lines = f.readlines()

        zline = [n for n,l in enumerate(lines) if "rootZ =" in l]
        while len(zline) > 0:
            for z in zline:
                del lines[z]
            zline = [n for n,l in enumerate(lines) if "rootZ =" in l]

        text_insert = "rootZ = '{}';".format(probe_dir)
        lines.insert(0, text_insert)

        with open(session_file, "w") as dest:
            dest.writelines(lines)

    def run_kilosort(self):

        eng = matlab.engine.start_matlab()
        eng.addpath(self.main_folder, nargout=0)

        if self.recordings != 'all':
            [self.probe_dict.drop(key, None) for key in self.probe_dict if key not in self.recordings]
        if self.probes != 'all':
            for recording_key in self.recordings.keys():
                [self.probe_dict[recording_key].drop(key, None) for key in self.probe_dict[recording_key] if key not in self.probes]

        bad_dats = []
        for recording_key in self.probe_dict:
            for probe_key in self.probe_dict[recording_key]:
                d = self.probe_dict[recording_key][probe_key]
                skip_ks = self.skip_ks_flag(probe_dir=d)

                if (("rez.mat" in os.listdir(d))==False) and (skip_ks == False):
                    self.write_ks_file(probe_dir=d)

                    try:
                        start = time.time()
                        print('starting kilosort on {} {}'.format(d.split("\\")[6], d.split('\\')[-1]))
                        eng.cd(self.main_folder)
                        if ".0" in d:
                            eng.kilosort_one_oh_session(nargout=0)
                        else:
                            eng.kilosort_ultra_session(nargout=0)
                        end = time.time()
                        print("done with kilosort. that took {}s".format(end-start))
                    except Exception as e:
                        now = datetime.strftime(datetime.now(), '%Y%m%d-%H%M')
                        bad_dats.append("{} {} {}".format(now, d, e))
                        pass

                elif ("rez.mat" in os.listdir(d))==True:
                    print("{} {} has already been processed. Delete rez.mat to reprocess.".format(d.split("\\")[6], d.split('\\')[-1]))
                elif skip_ks == True:
                    print("Skipping {} {} because of flags file: {}".format(d.split("\\")[6], d.split('\\')[-1], flags['other_notes']))

            with open(self.bad_dats_txt, 'a') as f:
                for line in bad_dats:
                    f.write(line + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--probes_to_run', nargs="+", default='all')
    parser.add_argument('--recordings_to_run', nargs="+", default='all')
    args = parser.parse_args()

    RunKilosort(args.date, args.mouse_id, args.probes_to_run, args.recordings_to_run)
