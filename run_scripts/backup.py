import os
import shutil
import glob2
import time
from ..processing.xfer_files_run_ks import XferFilesRunKS

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--sort_A', nargs="+", type=bool, default=True)
    parser.add_argument('--destination', nargs="+", type=tuple, default=("backup_drive",''))
    args = parser.parse_args()
    runner = XferFilesRunKS(args.date, args.mouse_id, args.sort_A, args.destination)
    runner.xfer_ephys_data()
    runner.xfer_sync_data()
    runner.xfer_opto_data()
