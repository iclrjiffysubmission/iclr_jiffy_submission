import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.python.framework import ops
from tensorflow.python.ops import clip_ops
import pdb
import sys

sys.path.insert(0, '../')
from time_series.src.clean_datasets import cv_splits_for_dataset

from time_series.tsne_python import tsne
from time_series.parse_dataset.readUcr import UCRDataset
from time_series.parse_dataset.readEEG import loadEEG
from time_series.src.clean_datasets import cv_splits_for_dataset

import seaborn


from time_series.models.utils import evaluate_test_embedding, standardize_ts_lengths, UCR_DATASETS, MV_DATASETS

POOL_PCTG = .1

"""Hyperparameters"""
num_filt_1 = 8    #Number of filters in first conv layer
num_fc_1 = 40       #Number of neurons in hully connected layer
max_iterations = 8000
batch_size = 32
dropout = 1      #Dropout rate in the fully connected layer
plot_row = 5        #How many rows do you want to plot in the visualization
learning_rate = 2e-4


def bias_variable(shape, name):
  initial = tf.constant(0.1, shape=shape)
  return tf.Variable(initial, name = name)

def conv2d(x, W):
  return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

def max_pool_2x2(x, pool_width):
  return tf.nn.max_pool(x, ksize=[1, 1, pool_width, 1],
                        strides=[1, 1, 1, 1], padding='SAME')


def plot_seaborn(data):
  for i, row in enumerate(data):
    y_range = np.max(row) - np.min(row)
    data[i+1:] += y_range

  seaborn.tsplot(data=data)

def test_model(dataset, pool_pctg, layer_size_1):
  tf.reset_default_graph()
  if dataset in UCR_DATASETS:
    ucr_dataset = UCRDataset("../ucr_data/" + dataset)
    X_train = ucr_dataset.Xtrain
    y_train = ucr_dataset.Ytrain


    X_val = ucr_dataset.Xtest[:2]
    y_val = ucr_dataset.Ytest[:2]
    X_test = ucr_dataset.Xtest[2:]
    y_test = ucr_dataset.Ytest[2:]
    N = X_train.shape[0]
    Ntest = X_test.shape[0]
    D = 1 # Number of varialbes represented in time series
    D_ts = X_train.shape[1]
    X_train = np.expand_dims(X_train, 1)
    X_test = np.expand_dims(X_test, 1)
  elif dataset in MV_DATASETS:
    dataset = cv_splits_for_dataset(dataset)
    dataset_idx = min(4, len(dataset)-1)
    X_train = dataset[dataset_idx].X_train
    y_train = dataset[dataset_idx].y_train
    X_test = dataset[dataset_idx].X_test
    y_test = dataset[dataset_idx].y_test
    
    n = max([np.max([v.shape[0] for v in X_train]), np.max([v.shape[0] for v in X_test])])
    X_train = standardize_ts_lengths(X_train, n)
    X_test = standardize_ts_lengths(X_test, n)

    
    N = X_train.shape[0]
    Ntest = X_test.shape[0]
    D = X_train.shape[1]
    D_ts = X_train.shape[2]
  else: 
    
    X_train, y_train, X_test, y_test = loadEEG()
    X_val = X_test[:2]
    y_val = y_test[:2]
    X_test = X_test[2:]
    y_test = y_test[2:]
    
    n = max([np.max([v.shape[0] for v in X_train]), np.max([v.shape[0] for v in X_test])])
    X_train = standardize_ts_lengths(X_train, n)
    X_test = standardize_ts_lengths(X_test, n)

    N = X_train.shape[0]
    Ntest = X_test.shape[0]
    D = X_train.shape[1]
    D_ts = X_train.shape[2]

  X_val = X_test[:2]
  y_val = y_test[:2]
  X_test = X_test[2:]
  y_test = y_test[2:]
  pool_width = max(int(POOL_PCTG*D),2)
  stride_width = 1
  base = np.min(y_train)  #Check if data is 0-based
  if base != 0:
    y_train -=base
    y_test -= base
  y_val = y_test[:2]


  num_classes = len(np.unique(y_train))
  num_fc_1 = layer_size_1
  epochs = np.floor(batch_size*max_iterations / N)
  print('Train with approximately %d epochs' %(epochs))

  x = tf.placeholder("float", shape=[None, D, D_ts], name = 'Input_data')
  y_ = tf.placeholder(tf.int64, shape=[None], name = 'Ground_truth')
  keep_prob = tf.placeholder("float")
  bn_train = tf.placeholder(tf.bool)

  with tf.name_scope("Reshaping_data") as scope:
    x_image = tf.reshape(x, [-1,D,D_ts,1])

    initializer = tf.contrib.layers.xavier_initializer()
    """Build the graph"""
    # ewma is the decay for which we update the moving average of the
    # mean and variance in the batch-norm layers
  with tf.name_scope("Conv1") as scope:
    W_conv1 = tf.get_variable("Conv_Layer_1", shape=[1, 5, 1, num_filt_1],initializer=initializer)
    b_conv1 = bias_variable([num_filt_1], 'bias_for_Conv_Layer_1')
    a_conv1 = conv2d(x_image, W_conv1) + b_conv1

    h_relu = tf.nn.relu(a_conv1)
    h_conv1 = max_pool_2x2(h_relu, pool_width)

  with tf.name_scope("Fully_Connected1") as scope:
    h_conv3_flat = tf.contrib.layers.flatten(h_conv1)
    W_fc1 = tf.get_variable("Fully_Connected_layer_1", shape=[D*num_filt_1*D_ts*(1./stride_width), num_fc_1],initializer=initializer)
    b_fc1 = bias_variable([num_fc_1], 'bias_for_Fully_Connected_Layer_1')
    h_fc1 = tf.nn.relu(tf.matmul(h_conv3_flat, W_fc1) + b_fc1)

  with tf.name_scope("Fully_Connected2") as scope:
    h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)
    W_fc2 = tf.get_variable("W_fc2", shape=[num_fc_1, num_classes],initializer=initializer)
    b_fc2 = tf.Variable(tf.constant(0.1, shape=[num_classes]),name = 'b_fc2')
    h_fc2 = tf.matmul(h_fc1_drop, W_fc2) + b_fc2

  with tf.name_scope("SoftMax") as scope:
      regularization = .001
      regularizers = (tf.nn.l2_loss(W_conv1) + tf.nn.l2_loss(b_conv1)
                    + tf.nn.l2_loss(W_fc2) + tf.nn.l2_loss(b_fc2))
      loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=h_fc2,labels=y_)

      cost = tf.reduce_sum(loss) / batch_size
      cost += regularization*regularizers
      loss_summ = tf.summary.scalar("cross entropy_loss", cost)
  with tf.name_scope("train") as scope:
      tvars = tf.trainable_variables()
      #We clip the gradients to prevent explosion
      grads = tf.gradients(cost, tvars)
      optimizer = tf.train.AdamOptimizer(learning_rate)
      gradients = list(zip(grads, tvars))
      train_step = optimizer.apply_gradients(gradients)
      # The following block plots for every trainable variable
      #  - Histogram of the entries of the Tensor
      #  - Histogram of the gradient over the Tensor
      #  - Histogram of the grradient-norm over the Tensor
      numel = tf.constant([[0]])
      for gradient, variable in gradients:
        if isinstance(gradient, ops.IndexedSlices):
          grad_values = gradient.values
        else:
          grad_values = gradient

        numel +=tf.reduce_sum(tf.size(variable))

        h1 = tf.summary.histogram(variable.name, variable)
        h2 = tf.summary.histogram(variable.name + "/gradients", grad_values)
        h3 = tf.summary.histogram(variable.name + "/gradient_norm", clip_ops.global_norm([grad_values]))
  with tf.name_scope("Evaluating_accuracy") as scope:

      correct_prediction = tf.equal(tf.argmax(h_fc2,1), y_)
      accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"))
      accuracy_summary = tf.summary.scalar("accuracy", accuracy)


  #Define one op to call all summaries
  merged = tf.summary.merge_all()


  # For now, we collect performances in a Numpy array.
  # In future releases, I hope TensorBoard allows for more
  # flexibility in plotting
  #perf_collect = np.zeros((3,int(np.floor(max_iterations /100))))
  cost_ma = 0.0
  acc_ma = 0.0

  patience_window = 20
  last_10_val = [0 for i in range(patience_window)]
  with tf.Session() as sess:
    writer = tf.summary.FileWriter("./log_tb", sess.graph)

    sess.run(tf.global_variables_initializer())

    step = 0      # Step is a counter for filling the numpy array perf_collect
    for i in range(int(max_iterations)):
      batch_ind = np.random.choice(N,batch_size,replace=False)
      #batch_ind = np.arange(N)
      #batch_ind = batch_ind[(i*batch_size)%N:((i+1)*batch_size)%N]

      if i==0:
          # Use this line to check before-and-after test accuracy
          result = sess.run(accuracy, feed_dict={ x: X_test, y_: y_test, keep_prob: 1.0, bn_train : False})
          acc_test_before = result

      if i%50 == 0:
        #Check training performance

        result = sess.run([cost,accuracy],feed_dict = { x: X_train, y_: y_train, keep_prob: 1.0, bn_train : False})
        #perf_collect[1,step] = acc_train = result[1]
        acc_train = result[1]
        cost_train = result[0]

        #Check validation performance
        
        #result = sess.run([accuracy,cost,merged], feed_dict={ x: X_val, y_: y_val, keep_prob: 1.0, bn_train : False})
        #perf_collect[0,step] = acc_val = result[0]
        #cost_val = result[1]
        cost_val = 10
        acc_val = 10
        if i == 0: cost_ma = cost_train
        if i == 0: acc_ma = acc_train
        cost_ma = 0.8*cost_ma+0.2*cost_train
        acc_ma = 0.8*acc_ma + 0.2*acc_train
        train_embedding = h_fc1.eval(feed_dict = {x: X_train, y_: y_train, keep_prob: 1.0, bn_train : False })
        test_embedding = h_fc1.eval(feed_dict = {x: X_test, y_: y_train, keep_prob: 1.0, bn_train : False })
        gg = evaluate_test_embedding(train_embedding, y_train, test_embedding, y_test)
        print('Accuracy given NN approach %0.2f' %(100*gg))
        last_10_val[(i/200) % patience_window] = acc_val
        #if last_10_val.count(last_10_val[0]) == len(last_10_val) and i > 3000:
        #  print 'Stopping early!'
        #  break


        writer.flush()  #Don't forget this command! It makes sure Python writes the summaries to the log-file
     #   print("At %5.0f/%5.0f Cost: train%5.3f val%5.3f(%5.3f) Acc: train%5.3f val%5.3f(%5.3f) " % (i,max_iterations, cost_train,cost_val,cost_ma,acc_train,acc_val,acc_ma))
        step +=1
      gg = h_relu.eval(feed_dict={x:X_train[batch_ind], y_: y_train[batch_ind], keep_prob: dropout, bn_train : False})
      sess.run(train_step,feed_dict={x:X_train[batch_ind], y_: y_train[batch_ind], keep_prob: dropout, bn_train : False})
    result = sess.run([accuracy,numel], feed_dict={ x: X_test, y_: y_test, keep_prob: 1.0, bn_train : False})
    acc_test = result[0]
    print('The network has %s trainable parameters'%(result[1]))

    train_embedding = h_fc1.eval(feed_dict = {x: X_train, y_: y_train, keep_prob: 1.0, bn_train : False })
    test_embedding = h_fc1.eval(feed_dict = {x: X_test, y_: y_train, keep_prob: 1.0, bn_train : False })
    gg = evaluate_test_embedding(train_embedding, y_train, test_embedding, y_test)
    print('Accuracy given NN approach %0.2f' %(100*gg))
    return gg


"""Additional plots"""
"""
print('The accuracy on the test data is %.3f, before training was %.3f' %(acc_test,acc_test_before))
plt.figure()
plt.plot(perf_collect[0],label='Valid accuracy')
plt.plot(perf_collect[1],label = 'Train accuracy')
plt.axis([0, step, 0, np.max(perf_collect)])
plt.legend()
"""

#test_model(sys.argv[1], .2, 40)
#plt.show()
# We can now open TensorBoard. Run the following line from your terminal
# tensorboard --logdir=./log_tb
