import os
import shutil
import glob2
import time

class TransferToBackup():
    def __init__(self):
        """very specific class written to transfer files from NP2 synology drive to new backup drives"""
        self.frm = r"\\10.128.54.155\Data\np2_data"
        self.to = r"\\W10dt05517\e"

        potential_xfers = os.listdir(self.frm)
        already_exists = os.listdir(self.to)

        self.to_xfer = [d for d in potential_xfers if d not in already_exists]
        self.filenames = ['continuous.dat', 'synchronized_timestamps.npy', 'timestamps.npy',
                            'channels.npy', 'channel_states.npy', 'full_words.npy']


    def run_it(self):

        for x in self.to_xfer:
            print("starting to copy session {}".format(x))
            start = time.time()
            session_path = os.path.join(self.frm, x)
            self.make_directories(session_path)
            src_dst = self.build_file_list(session_path)
            self.copy_files(src_dst)
            end = time.time()
            dur = end - start
            print("finished {}, that took {} seconds".format(x, dur))

    def make_directories(self, session_path):
        paths = []
        for root,dirs,files in os.walk(session_path):
            for d in dirs:
                fullp = os.path.join(root, d)
                paths.append(fullp.split('np2_data\\')[1])

        for p in paths:
            pathname = os.path.join(self.to, p)
            if os.path.exists(pathname)==False:
                os.makedirs(pathname)

    def build_file_list(self, session_path):
        paths = []
        for fn in self.filenames:
            paths.append(glob2.glob(os.path.join(session_path, '**', fn)))

        source_paths = [p for subp in paths for p in subp]
        dest_paths = []
        for sp in source_paths:
            split = sp.split('np2_data\\')[1]
            dest_paths.append(os.path.join(self.to, split))

        src_dst = list(zip(source_paths, dest_paths))
        return src_dst

    def copy_files(self, src_dst_list):
        for pair in src_dst_list:
            shutil.copy2(pair[0], pair[1])



if __name__ == "__main__":
    TransferToBackup().run_it()
