import matplotlib.pyplot as plt
import numpy as np
import pdb
import sys
from readUcr import UCRDataset

from ts_autoencoder import dae_stackedconv_model

embedding_size = 10
kernel_size = 12
n_filters = 1
pool_size = 5
VERBOSE_VAL = 0
N_EPOCHS = 1000


def plot_evolution(fnames, dataset):
	UCR_DATA_DIR = os.path.expanduser('~/Documents/MEng/time_series/ucr_data/')
	ucr_dataset = UCRDataset(UCR_DATA_DIR + dataset)

	X_train = np.expand_dims(ucr_dataset.Xtrain, 2)
	y_train = ucr_dataset.Ytrain
	X_val = np.expand_dims(ucr_dataset.Xtest[:2], 2)
	y_val = ucr_dataset.Ytest[:2]
	X_test = np.expand_dims(ucr_dataset.Xtest,2)
	y_test = ucr_dataset.Ytest

	n = max([np.max([v.shape[0] for v in X_train]), np.max([v.shape[0] for v in X_test])])
	if n % 2 != 0:
	n += 1
	X_train = standardize_ts_lengths_1(X_train, n)
	X_test = standardize_ts_lengths_1(X_test, n)
	X_train = normalize_rows(X_train)
	X_test = normalize_rows(X_test)

	img_shape = X_train.shape[1:]

	m = dae_stackedconv_model(img_shape, embedding_size, kernel_size, n_filters, pool_size)

	for fname in fnames:
		m.load_weights(fname)
		model.compile(optimizer=adam, loss='mean_absolute_error')
		pdb.set_trace()


