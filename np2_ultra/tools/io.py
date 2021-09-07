import json
import os
import np2_ultra.files as files

def read_computer_names(path_to_json=None):
    '''
    path_to_json: can enter an absolute path to json file or use default path (leave as None)
    '''
    if path_to_json is not None:
        with open(path_to_json, "r") as c:
            comp_dict = json.load(c)
    else:
        current_dir = os.getcwd()
        os.chdir(os.path.dirname(files.__file__))
        with open("computer_names.json", "r") as c:
            comp_dict = json.load(c)
        os.chdir(current_dir)
    return comp_dict

def read_pxi_dict(path_to_json=None):
    '''
    path_to_json: can enter an absolute path to json file in case of new probe config. Custom json MUST include all the same keys as default.
                  To use default path, leave as None.
    '''
    if path_to_json is not None:
        with open(path_to_json, "r") as p:
            pxi_dict = json.load(p)
    else:
        current_dir = os.getcwd()
        os.chdir(os.path.dirname(files.__file__))
        with open("pxi_dict.json", "r") as c:
            pxi_dict = json.load(c)
        os.chdir(current_dir)
    return pxi_dict


def get_paths_to_kilosort_templates():
    '''
    Returns the locations of the kilosort template .m files for the 1.0 and ultra probe sorting.
    '''
    current_dir = os.getcwd()
    os.chdir(os.path.dirname(files.__file__))
    one_oh = os.path.join(os.getcwd(), "kilosort_main_one_oh.m")
    ultra = os.path.join(os.getcwd(), "kilosort_main_ultra.m")
    os.chdir(current_dir)
    return one_oh, ultra
