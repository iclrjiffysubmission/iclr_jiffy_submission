import pdb

f = open('layer_size_comparison.csv', 'r').readlines()
split_lines = [x.split(',')[:3] for x in f]
split_lines = [','.join(x) + '\n'  for x in split_lines]
f_out = open('new_comparison_file', 'w')

for line in split_lines:
    f_out.write(line)

