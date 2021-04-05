import os
import glob2
from datetime import datetime
import time
import shutil
import matlab.engine
import json

class XferFilesRunKS():
    """runs in conda env kilosort"""
    def __init__(self, date, mouse_id, sort_A = True, computer_names_file = r"\\10.128.54.155\Data\np2_comp_names.txt"):
        self.sort_A = sort_A
        self.mouse_id = mouse_id
        computer_names = {}
        with open(computer_names_file) as file:
            for f in file:
                f = f.strip()
                computer_names[f.split(':')[0]] = f.split(':')[1]
        self.computer_names = computer_names
        if date == 'today':
            self.date = datetime.strftime(datetime.today(), '%Y-%m-%d')
        else:
            self.date = date
        self.destination_folder = os.path.join(computer_names['dest_root'], "np2_data")
        self.main_folder = os.path.join(self.destination_folder, self.date +'_' + self.mouse_id)
        if os.path.exists(self.main_folder)==False:
            os.mkdir(self.main_folder)
        self.bad_dats_txt = os.path.join(self.main_folder, "bad_dat_files.txt")

    def run_it(self):
        print("date: {}, mouse: {}".format(self.date, self.mouse_id))
        print(self.computer_names['acq'])
        print("------TRANSFERRING ALL FILES--------")
        self.xfer_ephys_data()
        self.xfer_sync_data()
        self.xfer_opto_data()
        self.xfer_behavior_videos()
        self.xfer_brain_imgs()
        self.xfer_params_file()
        print("------DONE TRANSFERRING FILES--------")
        print("------STARTING KILOSORT--------")
        if self.mouse_id != "saline":
            self.run_kilosort()
            print("------DONE WITH KILOSORT {}_{}--------".format(self.date, self.mouse_id))
        else:
            print("------DONE TRANSFERRING FILES {}_{}--------".format(self.date, self.mouse_id))

    def get_date_modified(self, file_path, date_format):
        date = datetime.strftime(datetime.fromtimestamp(os.stat(file_path).st_ctime), date_format)
        return date

    def xfer_ephys_data(self):
        start = time.time()
        print("Transferring ephys data.")

        if len(glob2.glob(os.path.join(self.main_folder, 'recording*'))) == 0:
            transfer_ephys_data=True
            # print("transfer_ephys_data = true")
        else:
            transfer_ephys_data = False
            # print("transfer_ephys_data = false")

        if transfer_ephys_data==True:
            data_loc = glob2.glob(os.path.join(self.computer_names['acq'], "*{}*".format(self.date), '**', 'experiment1'))[0]
            # print(data_loc)
            transfer_loc = self.main_folder
            xml_file = os.path.join(os.path.dirname(data_loc), "settings.xml")
            shutil.copy(xml_file, os.path.join(transfer_loc, "settings.xml"))
            # print(transfer_loc)

            for file in os.listdir(data_loc):
                # print(file)
                if "recording" in file:
                    fol = os.path.join(data_loc, file)
                    shutil.copytree(fol, os.path.join(transfer_loc, file))
                    print("{} transfered".format(file))
        else:
            print("Ephys data already transferred.")

        rename_dict = {0: 'recording1', 1: 'recording2', 2:'recording3', 3: 'recording4', 4: 'recording5'}
        for n, name in enumerate(glob2.glob(os.path.join(self.main_folder, 'recording*'))):
            if "recording" in name:
                old = name
                new = os.path.join(os.path.dirname(name), rename_dict[n])
                try:
                    os.rename(old, new)
                except FileExistsError:
                    pass
                try:
                    probeA_timestamps = glob2.glob(os.path.join(new, 'continuous', 'Neuropix-PXI-*.0', 'timestamps.npy'))[0]
                    shutil.copy(probeA_timestamps, new)
                except:
                    print("---------{} timestamps file couldn't be moved.---------".format(rename_dict[n]))

        end = time.time()



        print("That took {} seconds".format(end-start))

    def xfer_sync_data(self):
        #transfer sync data
        start = time.time()
        print("Transferring sync data.")

        session_sync_files = []
        for file in os.listdir(self.computer_names['sync']):
            full_path = os.path.join(self.computer_names['sync'], file)
            if self.get_date_modified(full_path, '%Y-%m-%d') == self.date:
                session_sync_files.append(full_path)
        session_sync_files = sorted(session_sync_files)

        for n, name in enumerate(sorted(glob2.glob(os.path.join(self.main_folder, 'recording*')))):
            if len(glob2.glob(os.path.join(name, "*sync.h5"))) == 0:
                shutil.copy(session_sync_files[n], name)
                old = os.path.join(name, os.path.basename(session_sync_files[n]))
                new = os.path.join(name, os.path.basename(session_sync_files[n]).split('.')[0] + "_sync.h5")
                os.rename(old, new)
                print('sync file transferred to {}'.format(os.path.basename(name)))
            else:
                print('{} already had a sync file'.format(os.path.basename(name)))

        end = time.time()
        print("That took {} seconds".format(end-start))

    def xfer_opto_data(self):
        #transfer opto data
        start = time.time()
        print("Transferring opto data.")
        mod_date = datetime.strftime(datetime.strptime(self.date, "%Y-%m-%d"), "%y%m%d")
        session_opto_files = []
        for file in os.listdir(self.computer_names['stim']):
            if mod_date in file:
                session_opto_files.append(os.path.join(self.computer_names['stim'], file))
        session_opto_files = sorted(session_opto_files)

        for n, name in enumerate(sorted(glob2.glob(os.path.join(self.main_folder, 'recording*')))):
            if len(glob2.glob(os.path.join(name, "*opto.pkl"))) == 0:
                shutil.copy(session_opto_files[n], name)
                old = os.path.join(name, os.path.basename(session_opto_files[n]))
                new = os.path.join(name, os.path.basename(session_opto_files[n].split('_')[0] + "_{}.opto.pkl".format(self.mouse_id)))
                os.rename(old, new)
                print('opto file transferred to {}'.format(os.path.basename(name)))
            else:
                print('{} already had an opto file'.format(os.path.basename(name)))

        end = time.time()
        print("That took {} seconds".format(end-start))

    def xfer_behavior_videos(self):
        #transfer behavior videos
        start = time.time()
        print("Transferring videos.")
        mod_date = str(self.date).replace('-', '')

        session_video_files = []
        for file in os.listdir(self.computer_names['video_eye_beh']):
            if mod_date in file:
                session_video_files.append(os.path.join(self.computer_names['video_eye_beh'], file))

        beh_video_files = sorted([f for f in session_video_files if 'Behavior' in f])
        eye_video_files = sorted([f for f in session_video_files if 'Eye' in f])

        for n, name in enumerate(sorted(glob2.glob(os.path.join(self.main_folder, 'recording*')))):
            if (len(glob2.glob(os.path.join(name, "*Behavior*"))) == 0) | (len(glob2.glob(os.path.join(name, "*Eye*"))) == 0):
                idx1 = n*2
                idx2 = idx1+1
                try:
                    shutil.copy(beh_video_files[idx1], name)
                    shutil.copy(beh_video_files[idx2], name)
                    shutil.copy(eye_video_files[idx1], name)
                    shutil.copy(eye_video_files[idx2], name)
                    print("video files transferred to {}.".format(os.path.basename(name)))
                except:
                    print("no videos for {}".format(os.path.basename(name)))
                    pass
            else:
                print('{} already had video files'.format(os.path.basename(name)))

        end = time.time()
        print("That took {} seconds".format(end-start))

    def xfer_brain_imgs(self):
        start = time.time()
        print("Transferring brain images.")
        mod_date = str(self.date).replace('-', '_')

        session_img_files = []
        for file in os.listdir(self.computer_names['video_brain_img']):
            if mod_date in file:
                session_img_files.append(os.path.join(self.computer_names['video_brain_img'], file))

        for file in session_img_files:
            shutil.copy(file, self.main_folder)
        end = time.time()
        print("That took {} seconds".format(end-start))

    def xfer_params_file(self):
        start = time.time()
        print("Transferring params file.")
        try:
            param_file = glob2.glob(os.path.join(self.computer_names['video_sess_params'], '*{}*'.format(self.date)))[0]
            shutil.copy(param_file, self.main_folder)
            end = time.time()
            print("That took {} seconds".format(end-start))
        except:
            print("No params file for {}".format(self.date))
            pass

    def run_kilosort(self):
        kilosort_main_ultra = r"\\10.128.54.155\Data\kilosort_files\kilosort_main_ultra.m"
        kilosort_main_one_oh = r"\\10.128.54.155\Data\kilosort_files\kilosort_main_one_oh.m"
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
    args = parser.parse_args()
    runner = XferFilesRunKS(args.date, args.mouse_id, args.sort_A)
    runner.run_it()
