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
    """
    Run Kilosort spike sorting via the Python Matlab engine.

    Methods
    ----------
    get_all_file_locations(pxi_dict)
    write_ks_file(probe_dir)
    run_kilosort()
    """

    def __init__(self, date, mouse_id, probes_to_run='all', recordings_to_run='all', pxi_dict='default', override_ks_flag=False):
        '''
        Parameters
        ----------
        date: str
            The date of the session in YYYY-MM-DD format
        mouse_id: str
            The 6 digit mouse number
        probes_to_run: list, optional, default = 'all'
            Optionally only process a subset of probes in the session.
            Probes are ID'd by their letter and passed as a list of strings, eg ['A', 'E']
        recordings_to_run: list, optional, default = 'all'
            Optionally only process a subset of recordings in the session.
            Recordings are ID'd by the name of the recording folder and passed as a list of strings, eg ['recording2']
        pxi_dict: path, optional, default = 'default'
            Pass a path to a JSON containing a customized dictionary of mappings of probe letter to OpenEphys folder suffix.
            Default option runs the file located at ../files/pxi_dict.json
        override_ks_flag: bool, optional, default = False
            Optionally override any flags preventing Kilosort from running.
            Note: this will not override the stop caused by the rez.mat file existing, and you will still need to manually delete that to rerun (if it exists).
        '''
        self.date = date
        self.mouse_id = mouse_id
        self.probes = probes_to_run
        self.recordings = recordings_to_run
        self.flag_override = override_ks_flag

        self.computer_names = io.read_computer_names()
        self.get_all_file_locations(pxi_dict=pxi_dict)
        self.run_kilosort()

    def get_all_file_locations(self, pxi_dict):
        """
        Get paths to all relevant files and folders.
        Is initialized in __init__.

        Parameters
        ----------
        pxi_dict: see documentation of this arg under __init__
        """
        self.get_files = file_tools.GetFiles(self.date, self.mouse_id, pxi_dict=pxi_dict)
        self.pxi_dict = self.get_files.pxi_dict
        self.main_folder = self.get_files.session_dir
        self.bad_dats_txt = os.path.join(self.main_folder, "bad_dat_files.txt")
        self.get_files.get_probe_dirs(probes='all')
        self.probe_dict = self.get_files.probe_data_dirs
        self.path_to_ks_one_oh, self.path_to_ks_ultra = io.get_paths_to_kilosort_templates()

    def write_ks_file(self, probe_dir):
        """
        Retrieves templates for Kilosort's Matlab scripts, transfers to data folder and writes the path to the DAT file as rootZ.
        This function is called in run_kilosort() for each DAT file processed.

        Parameters
        ----------
        probe_dir: path
            The path to the directory where raw data for the probe being processed is stored.

        Returns
        ----------
        one_oh: bool
            A boolean specifying whether the probe being processed is a 1.0 probe or not.
            Determined by the "one_oh_probes" key in the pxi_dict json passed to the class.
        """
        one_oh_probes=self.pxi_dict['one_oh_probes']
        probe_dir_key = probe_dir[-2:]
        probe = self.pxi_dict['reverse'][probe_dir_key]

        if probe in one_oh_probes:
            session_file = os.path.join(self.main_folder, "kilosort_one_oh_session.m")
            if os.path.exists(session_file)==False:
                shutil.copy(self.path_to_ks_one_oh, session_file)
            one_oh = True
        else:
            session_file = os.path.join(self.main_folder, "kilosort_ultra_session.m")
            if os.path.exists(session_file)==False:
                shutil.copy(self.path_to_ks_ultra, session_file)
            one_oh = False

        with open(session_file, "r") as f:
            lines = f.readlines()

        zline = [n for n,l in enumerate(lines) if "rootZ =" in l]
        while len(zline) > 0:
            for z in zline:
                del lines[z]
            zline = [n for n,l in enumerate(lines) if "rootZ =" in l]

        text_insert = "rootZ = '{}';\n".format(probe_dir)
        lines.insert(0, text_insert)

        with open(session_file, "w") as dest:
            dest.writelines(lines)

        return one_oh

    def run_kilosort(self):
        """
        Calls and runs the Python Matlab engine with Kilosort per recording/probe combo.
        Is initialized under __init__.
        """
        eng = matlab.engine.start_matlab()
        eng.addpath(self.main_folder, nargout=0)

        if self.recordings != 'all':
            remove_list = [key for key in self.probe_dict if key not in self.recordings]
            [self.probe_dict.pop(key, None) for key in self.probe_dict.copy().keys() if key not in self.recordings]
        if self.probes != 'all':
            remove_list = []
            for recording_key in self.probe_dict.copy().keys():
                remove_probes = [key for key in self.probe_dict[recording_key] if key not in self.probes]
                remove_list.append((recording_key, [p for p in remove_probes]))
            for pair in remove_list:
                recording = pair[0]
                probes = pair[1]
                tups = [(recording, p) for p in probes]
                [self.probe_dict[t[0]].pop(t[1], None) for t in tups]

        bad_dats = []
        for recording_key in self.probe_dict:
            for probe_key in self.probe_dict[recording_key]:
                d = self.probe_dict[recording_key][probe_key]
                if self.flag_override == True:
                    skip_ks = False
                else:
                    skip_ks = self.get_files.get_kilosort_flag(recording_key, probe_key)

                if (("rez.mat" in os.listdir(d))==False) and (skip_ks == False):
                    one_oh = self.write_ks_file(probe_dir=d)

                    try:
                        start = time.time()
                        print('starting Kilosort on {} {}'.format(d.split("\\")[6], d.split('\\')[-1]))
                        eng.cd(self.main_folder)
                        if one_oh == True:
                            eng.kilosort_one_oh_session(nargout=0)
                        elif one_oh == False:
                            eng.kilosort_ultra_session(nargout=0)
                        end = time.time()
                        print("done with Kilosort. that took {}s".format(end-start))
                    except Exception as e:
                        now = datetime.strftime(datetime.now(), '%Y%m%d-%H%M')
                        bad_dats.append("{} {} {}".format(now, d, e))
                        self.get_files.make_flags_json(recording_key,
                                                    probe_key,
                                                    text = "failed kilosort",
                                                    skip_kilosort = True,)
                        pass

                elif ("rez.mat" in os.listdir(d))==True:
                    print("{} {} has already been processed. Delete rez.mat to reprocess.".format(d.split("\\")[6], d.split('\\')[-1]))
                elif skip_ks == True:
                    flags = self.get_files.get_flags_json(recording_key, probe_key)
                    print("Skipping {} {} because of flags file: {}".format(d.split("\\")[6], d.split('\\')[-1], flags['other notes']))

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
    parser.add_argument('--pxi_dict', default='default')
    parser.add_argument('--override_ks_flag', type=bool, default=False)

    args = parser.parse_args()

    RunKilosort(args.date, args.mouse_id, args.probes_to_run, args.recordings_to_run, args.pxi_dict, args.override_ks_flag)
