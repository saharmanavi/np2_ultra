import os
import json
import glob2
import itertools
import matplotlib.gridspec as gs
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42

from .tools.get_session_files_info import GetFiles


class MakeQCFigs():
    def __init__(self, session_date, mouse_id):
        self.session_name = "{}_{}".format(session_date, mouse_id)
        gf = GetFiles(session_date, mouse_id)


        r_paths = glob2.glob(os.path.join(self.root_data_dir, self.session_name, "recording*"))
        self.recordings = [os.path.basename(r) for r in r_paths]
        params_file = glob2.glob(os.path.join(self.root_data_dir, self.session_name, "*params.json"))[0]
        with open(params_file) as f:
            self.session_params = json.load(f)

        self.get_files()
        self.get_metadata_dict()
        self.make_pdf()

    def get_files(self):
        data_dicts = dict.fromkeys(self.recordings)
        for k in data_dicts.keys():
            data_dicts[k] = dict.fromkeys(self.probes)

        bad_ones = []
        for s in itertools.product(self.recordings, self.probes):
            p_id = "probe{}".format(s[1])
            r_id = s[0]
            try:
                dict_file = glob2.glob(os.path.join(self.root_analysis_dir, self.session_name, p_id, "*{}*".format(r_id)))[0]
                data_dict = pd.read_pickle(dict_file)
                data_dicts[r_id][s[1]] = data_dict
            except:
                bad_ones.append(s)
                pass
        self.bad_ones = bad_ones
        self.data_dicts = data_dicts

    def get_metadata_dict(self):
        temp_rec = {}
        for rec in self.recordings:
            try:
                good_A = len(self.data_dicts[rec]['A']['good_clusters'])
            except:
                good_A = 0
            try:
                good_C = len(self.data_dicts[rec]['C']['good_clusters'])
            except:
                good_C = 0
            try:
                good_E = len(self.data_dicts[rec]['E']['good_clusters'])
            except:
                good_E = 0
            r_dict = {'probeA': {'depth': self.session_params['probe_depths'][rec]['probeA'],
                    'num_good_units': good_A},
                        'probeC': {'depth': self.session_params['probe_depths'][rec]['probeC'],
                                'num_good_units': good_C},
                      'probeE': {'depth': self.session_params['probe_depths'][rec]['probeE'],
                                'num_good_units': good_E},
                                }

            temp_rec[rec] = r_dict

        metadata_dict = {'session_date' : self.session_params['date'],
                        'mouse_id' : self.session_params['mouse_id'],
                        'genotype' : self.session_params['genotype'],
                        'num_recordings': len(self.recordings),
                        'recordings_info': temp_rec}
        self.metadata_dict = metadata_dict



    def plot_probe_qc(self, probe, recording, axs):
        probeMean = np.zeros((probeRows,probeCols))
        probeStd = np.zeros((probeRows,probeCols))
        j = 0
        for ch,d in enumerate(raw_data[:,:300000]):
            i = ch//probeCols
            probeMean[i,j] = d.mean()
            probeStd[i,j] = d.std()
            if j==jmax:
                j = 0
            else:
                j += 1
        # fig = plt.figure(figsize=(5,7))
        # axs[0] = fig.add_subplot(1,2,1)
        im = axs[0].imshow(probeMean,cmap='gray')
        cb = plt.colorbar(im,ax=axs[0],fraction=0.05,pad=0.04,shrink=0.5)
        cb.ax.tick_params(labelsize=5)
        axs[0].set_title('raw mean')
        # axs[1] = fig.add_subplot(1,2,2)
        im = axs[1].imshow(probeStd,cmap='gray')
        cb = plt.colorbar(im,ax=axs[1],fraction=0.05,pad=0.04,shrink=0.5)
        cb.ax.tick_params(labelsize=5)
        axs[1].set_title('raw std')

    def make_pdf(self):
        save_dir = os.path.join(self.root_analysis_dir, self.session_name)
        pdf_file = PdfPages(os.path.join(save_dir, '{}_session_summary.pdf'.format(self.session_name)))
        for recording in self.recordings:
            fig = plt.figure(figsize=(11.69,8.27), dpi=100)

            gd = gs.GridSpec(20,16)
            axtitle = plt.subplot(gd[0,:])
            axnames_1 = plt.subplot(gd[1:3, :5])
            axmean_1 = plt.subplot(gd[4:,:2])
            axstd_1 = plt.subplot(gd[4:,2:4])

            axnames_2 = plt.subplot(gd[1:3, 5:11])
            axmean_2 = plt.subplot(gd[4:,5:7])
            axstd_2 = plt.subplot(gd[4:,8:10])

            axnames_3 = plt.subplot(gd[1:3, 11:])
            axmean_3 = plt.subplot(gd[4:,11:13])
            axstd_3 = plt.subplot(gd[4:,14:])

            axtitle.text(.5,.5,"{} {} {} {}".format(self.metadata_dict['session_date'],
                                                    self.metadata_dict['mouse_id'],
                                                    self.metadata_dict['genotype'],
                                                    recording),
                         size=18, horizontalalignment='center', verticalalignment='center')
            axtitle.axis('off')

            ##probe A stuff
            if (recording, 'A') in self.bad_ones:
                axnames_1.text(.5,.5, "no Probe A data",
                               size=14, horizontalalignment='center', verticalalignment='center')
                axnames_1.axis('off')
                axmean_1.axis('off')
                axstd_1.axis('off')

            else:
                axnames_1.text(.5,.5, "Probe A depth={} \nn_units={}".format(self.metadata_dict['recordings_info'][recording]['probeA']['depth'],
                                                                           self.metadata_dict['recordings_info'][recording]['probeA']['num_good_units']),
                               size=14, horizontalalignment='center', verticalalignment='center')
                axnames_1.axis('off')
                self.plot_probe_qc(probe='A', recording=recording, axs=[axmean_1, axstd_1])


            ##probe C stuff
            if (recording, 'C') in self.bad_ones:
                axnames_2.text(.5,.5, "no Probe C data",
                               size=14, horizontalalignment='center', verticalalignment='center')
                axnames_2.axis('off')
                axmean_2.axis('off')
                axstd_2.axis('off')

            else:
                axnames_2.text(.5,.5, "Probe C depth={} \nn_units={}".format(self.metadata_dict['recordings_info'][recording]['probeC']['depth'],
                                                                           self.metadata_dict['recordings_info'][recording]['probeC']['num_good_units']),
                               size=14, horizontalalignment='center', verticalalignment='center')
                axnames_2.axis('off')
                self.plot_probe_qc(probe='C', recording=recording, axs=[axmean_2, axstd_2])

            ##probe E stuff
            if (recording, 'E') in self.bad_ones:
                axnames_3.text(.5,.5, "no Probe E data",
                               size=14, horizontalalignment='center', verticalalignment='center')
                axnames_3.axis('off')
                axmean_3.axis('off')
                axstd_3.axis('off')
            else:
                axnames_3.text(.5,.5, "Probe E depth={} \nn_units={}".format(self.metadata_dict['recordings_info'][recording]['probeE']['depth'],
                                                                           self.metadata_dict['recordings_info'][recording]['probeE']['num_good_units']),
                               size=14, horizontalalignment='center', verticalalignment='center')
                axnames_3.axis('off')
                self.plot_probe_qc(probe='E', recording=recording, axs=[axmean_3, axstd_3])


            pdf_file.savefig(fig)

        pdf_file.close()
        print("summary saved at {}".format(save_dir))









#
# if __name__ == "__main__":
#     import argparse
#     parser = argparse.ArgumentParser()
#     parser.add_argument('session_date', type=str)
#     parser.add_argument('mouse_id', type=str)
#     parser.add_argument('--recording_nums', nargs="+", type=str, default=["1", "2", "3"])
#     parser.add_argument('--probes', nargs="+", type=list, default=["C", "E"])
#     args = parser.parse_args()
#     batch_run(args.session_date, args.mouse_id, args.recording_nums, args.probes)
