import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def get_probe_info(probe):
    num_channels = 384
    if probe=='A':
        probeRows = 96
        probeCols = 4

        x_spacing = 16
        x_start = 11
        probeX = np.arange(x_start,x_spacing*probeCols, x_spacing)

        y_spacing = 20
        n_row = probeRows*2
        y_start = 20
        probeY = np.arange(y_start, y_spacing*n_row+1, y_spacing)

    elif (probe=='C') or (probe=='E'):
        probeRows = 48
        probeCols = 8
        channelSpacing = 6 # microns
        probeX = np.arange(probeCols)*channelSpacing
        probeY = np.arange(probeRows)*channelSpacing
    return probeRows, probeCols, probeX, probeY


def grid_of_waveforms(probe, cluster_template, channel_positions, y_range=None):
    """Probe is just the letter (A, C, E)
    cluster_template is 2d waveform from one timepoint (pre-normalized how you want it)
    y_range is range of probe rows to plot"""
    probeRows, probeCols, probeX, probeY = get_probe_info(probe)

    fig = plt.figure(figsize=(5,15))
    gs = matplotlib.gridspec.GridSpec(probeRows,probeCols)

    peaks = np.unravel_index(np.argmin(cluster_template), cluster_template.shape)
    peakChan = peaks[1]
    peakTime = peaks[0]

    ymin = cluster_template[:, peakChan].min() * 1.1
    ymax = cluster_template[:, peakChan].max() * 1.1

    for ind in range(cluster_template.shape[1]):
        chX, chY = channel_positions[ind]
        i = probeRows-1-np.where(probeY==chY)[0][0]
        j = np.where(probeX==chX)[0][0]
        ax = fig.add_subplot(gs[i,j])
        clr = 'r' if ind==peakChan else 'k'
        ax.plot(cluster_template[15:75, ind],color=clr,lw=1) #15:75 is the range of sample times to show for each waveform

        for side in ('right','top','left','bottom'):
            ax.spines[side].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_ylim([ymin,ymax])

    return fig

def plot_probe_view(probe, cluster_template, channel_positions, peak_time=30):
    probeRows, probeCols, probeX, probeY = get_probe_info(probe)
    t = cluster_template[peak_time, :]
    minv = np.percentile(t, .99)
    c = minv / 2
    maxv = 0

    fig, ax = plt.subplots(figsize=(3,10))
    templateAmp = np.zeros((probeRows,probeCols))
    for ind,ch in enumerate(t):
        chX,chY = channel_positions[ind]
        i = probeRows-1-np.where(probeY==chY)[0][0]
        j = np.where(probeX==chX)[0][0]
        templateAmp[i,j] = ch

    sns.heatmap(templateAmp, cmap='seismic_r',
               vmin = minv, vmax = maxv,
                center=c,
               square=True,
               )

    ax.set_yticks([])
    ax.set_xticks([])

    return fig
