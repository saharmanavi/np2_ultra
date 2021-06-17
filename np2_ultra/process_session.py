import argparse
from np2_ultra.scripts import transfer, kilosort, waveforms

'''
Runs transfer to data drive, kilosort, and waveform extraction on a session.
Can specify recordings/probes but no other custom parameters.
'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    #for all scripts
    parser.add_argument('date', type=str)
    parser.add_argument('mouse_id', type=str)
    #for kilosort and waveforms
    parser.add_argument('--probes_to_run', nargs="+", default='all')
    parser.add_argument('--recordings_to_run', nargs="+", default='all')

    args = parser.parse_args()

    transfer.TransferFiles(args.date, args.mouse_id).run_it()
    kilosort.RunKilosort(args.date, args.mouse_id, args.probes_to_run, args.recordings_to_run)
    waveforms.GetWaveforms(args.date, args.mouse_id, args.probes_to_run, args.recordings_to_run).run_it()
