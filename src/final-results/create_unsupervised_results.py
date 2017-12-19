import pandas as pd 
import pdb

import numpy as np

f = open('unsupervised_results.txt').readlines()


methods = ['LDPS', 'Jiffy', 'K-Shape']


LDPS = [0.825700105384,  0.553519202607, 0.979997392802, 0.938567642168, 0.869359331476, 0.539748743719]
Jiffy = [0.84943170195, 0.746078815424, 0.979605172894, 0.965358096901, 0.882760755, 0.586130653266]
kshape = [0.937753231256, 0.545579251384, 'none', 0.961568127392, 0.474899411947, 0.623115577889]
"""


datasets = ['arabic_digits', 'wafer', 'auslan', 'trajectories', 'libras', 'ecg']

results = [LDPS, Jiffy, kshape]

results_dicts = []
for method, result in zip(methods, results):
	for dataset, ri in zip(datasets, result):
		result = dict()
		result['method'] = method
		result['dataset'] = dataset
		result['RI'] = ri
		results_dicts.append(result)

df = pd.DataFrame(results_dicts)
df.to_csv('unsupervised_results.csv')


"""
LDPS = np.array([0.825700105384,  0.553519202607,  0.938567642168, 0.869359331476, 0.539748743719])
Jiffy = np.array([0.84943170195, 0.746078815424, 0.965358096901, 0.882760755, 0.586130653266])
kshape = np.array([.93, 0.545579251384, 0.961568127392, 0.474899411947, 0.623115577889])

pdb.set_trace()