from multi_cnn import test_model


mv_datasets = ['ecg', 'arabic_digits', 'libras', 'wafer', 'auslan', 'trajectories']

for dataset in mv_datasets:
	print dataset
	test_model(dataset, .2, 40)