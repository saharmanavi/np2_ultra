import sys
sys.path.append(r"C:\Users\saharm\Documents\CODE\local_code\np2_processing")
from get_ultra_waveforms import get_ultra_waveforms
import itertools

def batch_run(session_date, mouse_id, recording_nums=["1", "2", "3"], probes=["C", "E"]):
    for s in itertools.product(probes, recording_nums):
        try:
            probe_label = s[0][0]
        except:
            probe_label = s[0]
        try:
            recording_num = s[1][0]
        except:
            recording_num = s[1]
        print("running {} {}".format(probe_label, recording_num))
        get_ultra_waveforms(probe_label, session_date, mouse_id, recording_num).run_it()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('session_date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--recording_nums', nargs="+", type=str, default=["1", "2", "3"])
    parser.add_argument('--probes', nargs="+", type=list, default=["C", "E"])
    args = parser.parse_args()
    batch_run(args.session_date, args.mouse_id, args.recording_nums, args.probes)
