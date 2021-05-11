import json


def read_computer_names():
    with open(r"..\files\np2_comp_names.json", "r") as c:
        comp_dict = json.load(c)
    return comp_dict

# if __name__ == "__main__":
#     read_computer_names()
