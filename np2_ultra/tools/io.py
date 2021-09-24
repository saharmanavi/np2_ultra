import json
import os
import np2_ultra.files as files

def read_computer_names(path_to_json='default'):
    '''
    path_to_json: can enter an absolute path to json file or use default path (leave as None)
    '''
    if path_to_json == 'default':

        current_dir = os.getcwd()
        os.chdir(os.path.dirname(files.__file__))
        with open("computer_names.json", "r") as c:
            comp_dict = json.load(c)
        os.chdir(current_dir)
    else:

        with open(path_to_json, "r") as c:
            comp_dict = json.load(c)

    return comp_dict

def read_pxi_dict(path_to_json='default'):
    '''
    path_to_json: can enter an absolute path to json file in case of new probe config. Custom json MUST include all the same keys as default.
                  To use default path, leave as None.
    '''
    if path_to_json == 'default':
        current_dir = os.getcwd()
        os.chdir(os.path.dirname(files.__file__))
        with open("pxi_dict.json", "r") as c:
            pxi_dict = json.load(c)
        os.chdir(current_dir)

    elif path_to_json != 'default':
        with open(path_to_json, "r") as p:
            pxi_dict = json.load(p)

    return pxi_dict

def read_opto_params(path_to_json='default'):
    '''
    path_to_json: can enter an absolute path to json file in case of different opto params.
                Custom json MUST include all the same keys/format as default.
                  To use default path, leave as None.
    '''
    if path_to_json == 'default':
        current_dir = os.getcwd()
        os.chdir(os.path.dirname(files.__file__))
        with open("opto_params.json", "r") as c:
            opto_params = json.load(c)
        os.chdir(current_dir)

    elif path_to_json != 'default':
        with open(path_to_json, "r") as p:
            opto_params = json.load(p)

    return opto_params

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

def timestamp_checker(file_one, file_two, range=180):
    '''
    check whether two files/folders have similar enough timestamps that they could be from the same session.
    file_one, file_two are complete paths to files/folders
    range is time in seconds. default is 3 mins (180s)
    uses time last modified
    '''
    return abs(os.stat(file_one).st_mtime - os.stat(file_two).st_mtime) <= range
