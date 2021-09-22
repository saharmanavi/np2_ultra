import argparse
from np2_ultra.scripts import transfer, kilosort, waveforms

'''
Runs transfer to data drive, kilosort, and waveform extraction on a session.
See individual scripts for documentation on arguments.
'''

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    #for all scripts, required
    parser.add_argument('date', type=str)
    parser.add_argument('mouse_id', type=str)
    ##optional args
    #for transfer
    parser.add_argument('--destination', nargs="+", default=('dest_root', 'np2_data'))
    parser.add_argument('--openephys_folder',default='false')
    parser.add_argument('--path_to_files', default=None, type=str)
    #for kilosort and waveforms
    parser.add_argument('--probes_to_run', nargs="+", default='all')
    parser.add_argument('--recordings_to_run', nargs="+", default='all')
    parser.add_argument('--pxi_dict', default='default')
    #for waveforms
    parser.add_argument('--use_json_params', default=None)

    args = parser.parse_args()

    transfer.TransferFiles(args.date, args.mouse_id, args.destination, args.openephys_folder, args.path_to_files).run_it()
    kilosort.RunKilosort(args.date, args.mouse_id, args.probes_to_run, args.recordings_to_run, args.pxi_dict)
    waveforms.GetWaveforms(args.date, args.mouse_id, args.probes_to_run, args.recordings_to_run, args.pxi_dict, args.use_json_params).run_it()
