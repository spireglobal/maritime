import csv
from keys import decode_keys
from pyais import decode_msg
from pyais import exceptions as pe


def decode_line(line):
    result: dict = dict()
    try:
        # Decoded message is in a dictionary
        result = decode_msg(line)
    except pe.InvalidNMEAMessageException as e:
        pass
    return result


decode_me: list = list()
with open('raw.txt', 'r') as f:
    lines = f.readlines()
    # skip last few line
    total_lines = len(lines)
    for i in range(total_lines -3):
        line = lines[i]
        if 'g:' not in line:
            # get only message portion
            loc = line.find('!')
            line = line[loc:]
        decode_me.append(line)


with open('decoded.csv', 'a+') as d:
    writer = csv.DictWriter(
        d, fieldnames=decode_keys)
    writer.writeheader()
    for line in decode_me:
        decoded = decode_line(line)
        if decoded:
            writer.writerow(decoded)






