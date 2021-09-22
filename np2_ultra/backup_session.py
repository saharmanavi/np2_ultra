import argparse
from np2_ultra.scripts import transfer

'''
Backs up a session to backup drive.
'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('date', type=str)
    parser.add_argument('mouse_id', type=str)
    parser.add_argument('--destination', nargs="+", default=("backup_drive",''))
    parser.add_argument('--openephys_folder',default='false')
    parser.add_argument('--path_to_files', default=None, type=str)

    args = parser.parse_args()

    try:
        transfer.TransferFiles(args.date, args.mouse_id, args.destination, args.openephys_folder, args.path_to_files).run_it()
    except IOError as e:
        print("Something went wrong. If there isn't enough space on the current backup drive, change the drive name in compuer_names.json")
        print(e)
        pass
