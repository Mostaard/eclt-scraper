import csv
from collections import defaultdict

ovps = csv.DictReader(open('output/ovp.csv', encoding='utf-8-sig'))

counter_dict = dict()
for ovp in ovps:
    if ovp['ex_type'] not in counter_dict.keys():
        counter_dict[ovp['ex_type']] = 0
    else:
        counter_dict[ovp['ex_type']] += 1

print(sorted(counter_dict.items(), key=lambda x: x[1], reverse=True))
