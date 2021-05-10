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
    args = parser.parse_args()
    runner = XferFilesRunKS(args.date, args.mouse_id, args.sort_A)
    runner.run_it()
