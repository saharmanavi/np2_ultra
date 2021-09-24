import os
import glob2
from datetime import datetime
import time
import shutil
import json

import np2_ultra.files as files

class TransferFiles():
    """
    Transfer ephys data from NP2 computers to backup and processing drives.

    Methods
    ----------
    xfer_ephys_data()
    xfer_sync_data()
    xfer_opto_data()
    xfer_behavior_videos()
    xfer_brain_imgs()
    xfer_params_file()
    get_date_modified(file_path, date_format=False)

    """

    def __init__(self, date, mouse_id, destination=('dest_root', 'np2_data'), openephys_folder='false', path_to_files=None):
        '''
        Parameters
        ----------
        date: str
            The date of the session in YYYY-MM-DD format
        mouse_id: str
            The 6 digit mouse number
        destination: tuple, optional, default = ('dest_root', 'np2_data')
            First value is key in np2_comp_names json, second value is optional, can be a sub-folder.
        openephys_folder: str, optional, default = 'false'
            Argument takes the exact name (not path) of the OpenEphys folder you wish to process.
            This is only needed when more than one session is run on the same day.
            default = 'false'
        path_to_files: path, optional, default = None
            Can be relative or exact path to where comp_names json and kilosort template files are located. Not typically used.
            If None, will use the relative path of folder 'files' located one directory up from current.
        '''
        if path_to_files==None:
            self.path_to_files = os.path.dirname(files.__file__)
        else:
            self.path_to_files = path_to_files

        try:
            with open(os.path.join(self.path_to_files, 'computer_names.json'), 'r') as f:
                comp_names = json.load(f)
            self.computer_names = comp_names
        except FileExistsError:
            print("computer_names.json is not found. Please enter a different path or check that the file is in the specified folder.")
            return

        self.mouse_id = mouse_id
        if date == 'today':
            self.date = datetime.strftime(datetime.today(), '%Y-%m-%d')
        else:
            self.date = date

        self.destination_folder = os.path.join(self.computer_names[destination[0]], destination[1])
        self.main_folder = os.path.join(self.destination_folder, self.date +'_' + self.mouse_id)
        if os.path.exists(self.main_folder)==False:
            os.mkdir(self.main_folder)
        self.bad_dats_txt = os.path.join(self.main_folder, "bad_dat_files.txt")

        #codeblock below pertains to running more than one experiment in a day -- can otherwise be ignored
        if openephys_folder != 'false':
            self.specify_folder = openephys_folder
        else:
            self.specify_folder = False
        self.multiple_experiments = False
        potential_folders = [f for f in os.listdir(self.computer_names['acq']) if self.date in f]
        if len(potential_folders) > 1:
            self.multiple_experiments=True
            if self.specify_folder==False:
                print("There are multiple folders with the same date. You must specify which folder to use using the openephys_folder argument.")
                return
            timestamp = self.specify_folder.split('_')[1]
            self.experiment_timestamp = datetime.strptime(timestamp, '%H-%M-%S').time()

    def run_it(self):
        """
        Runs data transfer to specified location for entire session.
        if __name__ == __main__ automatically calls this function.
        """
        print("date: {}, mouse: {}".format(self.date, self.mouse_id))
        print("looking in {}".format(self.computer_names['acq']))
        print("------TRANSFERRING ALL FILES--------")
        print("transferring to {}".format(self.destination_folder))
        self.xfer_ephys_data()
        self.xfer_sync_data()
        self.xfer_opto_data()
        self.xfer_behavior_videos()
        self.xfer_brain_imgs()
        self.xfer_params_file()
        print("------DONE TRANSFERRING FILES {}_{}--------".format(self.date, self.mouse_id))

    def get_date_modified(self, file_path, date_format=False):
        """
        Get the date a file was last modified. Currently used to ID the correct sync files.

        Parameters
        ----------
        date_format: str, optional, default = False
            Can optionally return the date as a string of the specified format, using standard datetime format codes.
            Default returns a datetime timestamp object.
        """
        timestamp = datetime.fromtimestamp(os.stat(file_path).st_mtime)
        if date_format != False:
            timestamp = datetime.strftime(timestamp, date_format)
        return timestamp

    def xfer_ephys_data(self):
        """
        Tranfer session output from Open Ephys, as well as make a copy of one timestamp.npy file per recording.
        Copying the timestamp.npy file is vital for downstream processing.
        """
        start = time.time()
        print("Transferring ephys data.")

        if len(glob2.glob(os.path.join(self.main_folder, 'recording*'))) == 0:
            transfer_ephys_data = True
        else:
            transfer_ephys_data = False

        if transfer_ephys_data==True:
            data_folders = glob2.glob(os.path.join(self.computer_names['acq'], "*{}*".format(self.date), '**', 'experiment1'))

            if (len(data_folders) > 1) & (self.specify_folder==False):
                print("There is more than one experiment for this day. Please specify which one you'd like to process using the openephys_folder argument:\n{}".format(data_folders))
                return
            elif (len(data_folders) > 1) & (self.specify_folder!=False):
                try:
                    data_loc = [f for f in data_folders if self.specify_folder in f][0]
                except IndexError:
                    print("The open ephys folder you specified does not exist. Check the name and try again.")
                    return
            else:
                data_loc = data_folders[0]

            transfer_loc = self.main_folder
            xml_file = os.path.join(os.path.dirname(data_loc), "settings.xml")
            shutil.copy(xml_file, os.path.join(transfer_loc, "settings.xml"))

            for file in os.listdir(data_loc):
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
                    #this step is very important because it fixes an issue where kilosort and openephys miscommunicate about timestamps
                    #it's necessary to save 1 timestamps.npy file per recording (from any probe is fine) outside of the folder where it usually is
                    #and this needs to happen before Kilosort is run because KS deletes that file.
                    #this timestamps.npy file is necessary to align the opto data properly. 
                    probeA_timestamps = glob2.glob(os.path.join(new, 'continuous', 'Neuropix-PXI-*.0', 'timestamps.npy'))[0]
                    shutil.copy(probeA_timestamps, new)
                except:
                    print("---------{} timestamps file couldn't be moved.---------".format(rename_dict[n]))

        end = time.time()
        print("That took {} seconds".format(end-start))

    def xfer_sync_data(self):
        """
        Tranfer session sync files. Files are matched by last modified timestamp to the correct recording folder.
        """
        start = time.time()
        print("Transferring sync data.")

        session_sync_files = []
        for file in os.listdir(self.computer_names['sync']):
            full_path = os.path.join(self.computer_names['sync'], file)
            if (self.get_date_modified(full_path, '%Y-%m-%d') == self.date) & ('.h5' in full_path):
                session_sync_files.append(full_path)

        if self.multiple_experiments==True:
            modified_sync_files_list = []
            for sync_file in session_sync_files:
                sync_timestamp = self.get_date_modified(sync_file)
                if sync_timestamp.time() > self.experiment_timestamp:
                    modified_sync_files_list.append(sync_file)
            # self.session_sync_files = sorted(modified_sync_files_list)
            self.session_sync_files = [(fullpath, datetime.fromtimestamp(os.stat(fullpath).st_ctime)) for fullpath in modified_sync_files_list]
        else:
            self.session_sync_files = [(fullpath, datetime.fromtimestamp(os.stat(fullpath).st_ctime)) for fullpath in session_sync_files]
            # self.session_sync_files = sorted(session_sync_files)
        self.session_sync_files.sort(key = lambda x: x[1])

        for n, name in enumerate(sorted(glob2.glob(os.path.join(self.main_folder, 'recording*')))):
            if len(glob2.glob(os.path.join(name, "*sync.h5"))) == 0:
                shutil.copy(self.session_sync_files[n][0], name)
                old = os.path.join(name, os.path.basename(self.session_sync_files[n][0]))
                new = os.path.join(name, os.path.basename(self.session_sync_files[n][0]).split('.')[0] + "_sync.h5")
                os.rename(old, new)
                print('sync file transferred to {}'.format(os.path.basename(name)))
            else:
                print('{} already had a sync file'.format(os.path.basename(name)))

        end = time.time()
        print("That took {} seconds".format(end-start))

    def xfer_opto_data(self):
        """
        Tranfer session opto pickles.
        """
        start = time.time()
        print("Transferring opto data.")

        mod_date = datetime.strftime(datetime.strptime(self.date, "%Y-%m-%d"), "%y%m%d")
        session_opto_files = []
        for file in os.listdir(self.computer_names['stim']):
            if mod_date in file:
                session_opto_files.append(os.path.join(self.computer_names['stim'], file))

        if self.multiple_experiments==True:
            modified_opto_files_list = []
            for opto_file in session_opto_files:
                opto_timestamp = self.get_date_modified(opto_file)
                if opto_timestamp.time() > self.experiment_timestamp:
                    modified_opto_files_list.append(opto_file)
            self.session_opto_files = sorted(modified_opto_files_list)
        else:
            self.session_opto_files = sorted(session_opto_files)

        for n, name in enumerate(sorted(glob2.glob(os.path.join(self.main_folder, 'recording*')))):
            if len(glob2.glob(os.path.join(name, "*opto.pkl"))) == 0:
                shutil.copy(self.session_opto_files[n], name)
                old = os.path.join(name, os.path.basename(self.session_opto_files[n]))
                new = os.path.join(name, os.path.basename(self.session_opto_files[n].split('_')[0] + "_{}.opto.pkl".format(self.mouse_id)))
                os.rename(old, new)
                print('opto file transferred to {}'.format(os.path.basename(name)))
            else:
                print('{} already had an opto file'.format(os.path.basename(name)))

        end = time.time()
        print("That took {} seconds".format(end-start))

    def xfer_behavior_videos(self):
        """
        Tranfer session behavior videos (eye tracking and body cam).
        """
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
        """
        Tranfer session photos showing brain surface and probe insertion locations.
        """
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
        """
        Tranfer session parameters JSON created at experiment time.
        """
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--destination', nargs="+", default=('dest_root', 'np2_data'))
    parser.add_argument('--openephys_folder',default='false')
    parser.add_argument('--path_to_files', default=None, type=str)
    args = parser.parse_args()

    TransferFiles(args.date, args.mouse_id, args.destination, args.openephys_folder, args.path_to_files).run_it()
