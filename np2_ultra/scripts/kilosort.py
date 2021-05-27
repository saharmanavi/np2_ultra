import os
import glob2
from datetime import datetime
import time
import shutil
import json

from np2_ultra.tools import io, get_session_file_info

class RunKilosort():
    def __init__(self, date, mouse_id):
        '''
        date: string, 'YYYY-MM-DD' or 'today' to run with today's date
        mouse_id: string,

        '''
    self.date = date
    self.mouse_id = mouse_id

    self.get_files = get_session_file_info.GetFiles(self.date, self.mouse_id)


    self.probe_config = probe_config
    self.computer_names = io.read_computer_names()
    self.pxi_dict = io.read_pxi_dict(probe_config=self.probe_config)



    def id_probe_dirs(self):


    def run_kilosort(self):
        import matlab.engine

        kilosort_main_one_oh = os.path.join(self.path_to_files, 'kilosort_main_one_oh.m')
        kilosort_main_ultra = os.path.join(self.path_to_files, 'kilosort_main_ultra.m')
        eng = matlab.engine.start_matlab()
        eng.addpath(self.main_folder, nargout=0)

        data_A = glob2.glob(os.path.join(self.main_folder, 'recording*', 'continuous', '*.0'))
        data_C = glob2.glob(os.path.join(self.main_folder, 'recording*', 'continuous', '*.2'))
        data_E = glob2.glob(os.path.join(self.main_folder, 'recording*', 'continuous', '*.4'))

        if self.sort_A == False:
            dir_list = [data_C, data_E]
        else:
            dir_list = [data_A, data_C, data_E]

        bad_dats = []

        shutil.copy(kilosort_main_one_oh, os.path.join(self.main_folder, "kilosort_one_oh_session.m"))
        shutil.copy(kilosort_main_ultra, os.path.join(self.main_folder, "kilosort_ultra_session.m"))
        for dirs in dir_list:
            if dirs==data_A:
                session_file = os.path.join(self.main_folder, "kilosort_one_oh_session.m")
                if os.path.exists(session_file)==False:
                    shutil.copy(kilosort_main_one_oh, os.path.join(self.main_folder, "kilosort_one_oh_session.m"))
            else:
                session_file = os.path.join(self.main_folder, "kilosort_ultra_session.m")
                if os.path.exists(session_file)==False:
                    shutil.copy(kilosort_main_ultra, os.path.join(self.main_folder, "kilosort_ultra_session.m"))

            for d in dirs:
                try:
                    flags_file = glob2.glob(os.path.join(d, "flags.json"))[0]
                    with open(flags_file, 'r') as f:
                        flags = json.load(f)
                        skip_ks = flags['skip_kilosort']
                except Exception as e:
                    skip_ks = False
                    # print("exception: {}".format(e))

                if (("rez.mat" in os.listdir(d))==False) and (skip_ks == False):
                    with open(session_file, "r") as f:
                        lines = f.readlines()

                    zline = [n for n,l in enumerate(lines) if "rootZ =" in l]
                    while len(zline) > 0:
                        for z in zline:
                            del lines[z]
                        zline = [n for n,l in enumerate(lines) if "rootZ =" in l]

                    text_insert = "rootZ = '{}';".format(d)
                    lines.insert(0, text_insert)

                    with open(session_file, "w") as dest:
                        dest.writelines(lines)

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
    parser.add_argument('--sort_A', nargs="+", type=bool, default=True)
    parser.add_argument('--destination', nargs="+", type=tuple, default=('dest_root', 'np2_data'))
    parser.add_argument('--openephys_folder', nargs="+", type=str, default= 'false')
    args = parser.parse_args()
    runner = XferFilesRunKS(args.date, args.mouse_id, args.sort_A, args.destination, args.openephys_folder)
    runner.run_it()
