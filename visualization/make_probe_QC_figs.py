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

from ..tools.get_session_files_info import GetFiles


class MakeQCFigs():
    def __init__(self, session_date, mouse_id, ultra_only=False, root_dir=r"\\10.128.54.155\Data"):
        self.session_name = "{}_{}".format(session_date, mouse_id)
        if ultra_only==True:
            probes = ['C', 'E']
        else:
            probes = ['A', 'C', 'E']

        self.gf = GetFiles(session_date, mouse_id, probes=probes, root_dir=root_dir)
        save_dir = self.gf.analysis_dir
        data_dirs_dict = self.gf.data_dirs
        metadata_dict = self.gf.session_params
        self.make_pdf(save_dir, data_dirs_dict, metadata_dict)

    def plot_probe_qc(self, probeRows, probeCols, raw_data, axs):
        """probe is just the letter, recording is formatted 'recordingN'"""
        probeMean = np.zeros((probeRows,probeCols))
        probeStd = np.zeros((probeRows,probeCols))
        jmax = probeCols - 1
        j = 0
        for ch,d in enumerate(raw_data[:,:300000]):
            i = ch//probeCols
            probeMean[i,j] = d.mean()
            probeStd[i,j] = d.std()
            if j==jmax:
                j = 0
            else:
                j += 1
        im = axs[0].imshow(probeMean,cmap='gray')
        cb = plt.colorbar(im,ax=axs[0],fraction=0.05,pad=0.04,shrink=0.5)
        cb.ax.tick_params(labelsize=5)
        axs[0].set_title('raw mean')
        im = axs[1].imshow(probeStd,cmap='gray')
        cb = plt.colorbar(im,ax=axs[1],fraction=0.05,pad=0.04,shrink=0.5)
        cb.ax.tick_params(labelsize=5)
        axs[1].set_title('raw std')

    def make_pdf(self, save_dir, data_dirs_dict, metadata_dict):

        pdf_file = PdfPages(os.path.join(save_dir, '{}_session_summary.pdf'.format(self.gf.s_id)))
        for recording in data_dirs_dict.keys():
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

            ax_dict = {'A': {'name': axnames_1,
                            'mean': axmean_1,
                            'std': axstd_1},
                        'C': {'name': axnames_2,
                            'mean': axmean_2,
                            'std': axstd_2},
                        'E': {'name': axnames_3,
                            'mean': axmean_3,
                            'std': axstd_3}}

            axtitle.text(.5,.5,"{} {} {} {}".format(metadata_dict['date'],
                                                    metadata_dict['mouse_id'],
                                                    metadata_dict['genotype'],
                                                    recording),
                         size=18, horizontalalignment='center', verticalalignment='center')
            axtitle.axis('off')

            for probe in data_dirs_dict[recording].keys():
                try:
                    ax_dict[probe]['name'].text(.5,.5, "Probe {} depth={} \nn_units={}".format(probe,
                                                                                                metadata_dict['probe_depths'][recording]['probe{}'.format(probe)],
                                                                                                "num_good_units",
                                                size=14, horizontalalignment='center', verticalalignment='center'))
                    ax_dict[probe]['name'].axis('off')

                    probeRows, probeCols, probeX, probeY = self.gf.get_probe_info(probe)
                    raw_data = self.gf.get_raw_data(data_dirs_dict[recording][probe])
                    self.plot_probe_qc(probeRows, probeCols, raw_data, axs=[ax_dict[probe]['mean'], ax_dict[probe]['std']])

                except:
                    ax_dict[probe]['name'].text(.5,.5, "no Probe {} data".format(probe),
                                   size=14, horizontalalignment='center', verticalalignment='center')
                    ax_dict[probe]['name'].axis('off')
                    ax_dict[probe]['mean'].axis('off')
                    ax_dict[probe]['std'].axis('off')

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
