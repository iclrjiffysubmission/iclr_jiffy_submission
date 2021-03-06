import random
import numpy as np
import time
import tensorflow as tf 
import input_data
import math
import sys

from parse_dataset.readUcr import UCRDataset
from itertools import product


import pdb
from utils import plot_filters, normalize_rows, evaluate_test_embedding, classify_sample, next_batch, dist

batch_size = 128 

def create_pairs(x, digit_indices, labels):
    '''Positive and negative pair creation.
    Alternates between positive and negative pairs.
    '''
    n_classes = len(labels)
    n = min([len(digit_indices[d]) for d in range(n_classes)]) - 1
    pairs = []
    tags = []
    for j, d in enumerate(labels):
        eq_pairs = list(product(digit_indices[j], digit_indices[j]))
        eq_pairs = filter(lambda x: x[0] < x[1], eq_pairs)
        for pair in eq_pairs:
            pairs.append([x[pair[0]], x[pair[1]]])
            tags.append(1)
        for i in range(j+1, len(labels)):
            diff_pairs = list(product(digit_indices[j], digit_indices[i]))
            for pair in diff_pairs:
                pairs.append([x[pair[0]], x[pair[1]]])
                tags.append(-1)
        """
        for i in range(n):
            z1, z2 = digit_indices[j][i], digit_indices[j][i+1]
            pairs += [[x[z1], x[z2]]]
            inc = random.randrange(n_classes)
            dn_i = ((j + inc) % n_classes)
            z1, z2 = digit_indices[j][i], digit_indices[dn_i][i]
            pairs += [[x[z1], x[z2]]]
            tags += [1, 0]
        """
    return np.array(pairs), np.array(tags)


def mlp(input_,input_dim,output_dim,name="mlp"):
    with tf.variable_scope(name):
        w = tf.get_variable('w',[input_dim,output_dim],tf.float32,tf.random_normal_initializer(mean = 0.001, stddev=0.05))
        return tf.nn.relu(tf.matmul(input_,w))
        
def build_model_mlp(X_,_dropout, input_length):

    model = mlpnet(X_,_dropout, input_length)
    return model

def mlpnet(image,_dropout, ts_length):
    l1 = mlp(image,ts_length,128,name='l1')
    l1 = tf.nn.dropout(l1,_dropout)
    l2 = mlp(l1,128,128,name='l2')
    l2 = tf.nn.dropout(l2,_dropout)
    l3 = mlp(l2,128,128,name='l3')
    return l3

def contrastive_loss(y,d):
    tmp= (.5*y + .5) *tf.square(d)
    #tmp= tf.mul(y,tf.square(d))
    tmp2 = (1-(.5*y + .5)) *tf.square(tf.maximum((1 - d),0))
    return tf.reduce_sum(tmp +tmp2)/batch_size/2

def c_loss(y, model1, model2):
    new_y = tf.scalar_mul(-1, y)
    b = tf.matmul(tf.diag(tf.squeeze(new_y)),model2)
    c = model1 + b
    return tf.reduce_sum(tf.norm(c, axis=1))/batch_size


def compute_accuracy(prediction,labels):
    new_labels = np.array([.5*g + .5 for g in labels])
    x = np.array([prediction.ravel() > .5])
    return np.abs(x-new_labels.ravel()).mean()
    #return labels[prediction.ravel() < 0.5].mean()
    #return tf.reduce_mean(labels[prediction.ravel() < 0.5])


def regularizer(model1, model2, r):
    norm1 = tf.norm(model1, axis=1)
    norm2 = tf.norm(model2, axis=1)
    a1 = tf.square(tf.subtract(norm1, r))
    b1 = tf.square(norm2 - r)
    x = .5*tf.reduce_sum(tf.add(a1, b1))/batch_size
    return x


tf.reset_default_graph()
ucr_dataset = UCRDataset("../../../time-series/ucr_data/" + sys.argv[1]) 

X_train = ucr_dataset.Xtrain
y_train = ucr_dataset.Ytrain 
X_test = ucr_dataset.Xtest
y_test = ucr_dataset.Ytest

labels = np.unique(y_train)
r=4
digit_indices = [np.where(y_train == i)[0] for i in labels]
tr_pairs, tr_y = create_pairs(X_train, digit_indices, labels)
digit_indices = [np.where(y_test == i)[0] for i in labels]
te_pairs, te_y = create_pairs(X_test, digit_indices, labels)

p = np.random.permutation(len(tr_pairs))
tr_pairs = tr_pairs[p]
tr_y = tr_y[p]


# Initializing the variables
init = tf.initialize_all_variables()
# the data, shuffled and split between train and test sets
"""
X_train = normalize_rows(X_train)
X_test = normalize_rows(X_test)
"""
ts_length = len(X_train[0])
batch_size = 128
global_step = tf.Variable(0,trainable=False)
starter_learning_rate = 0.001
learning_rate = tf.train.exponential_decay(starter_learning_rate,global_step,10,0.1,staircase=True)
# create training+test positive and negative pairs
images_L = tf.placeholder(tf.float32,shape=([None,ts_length]),name='L')
images_R = tf.placeholder(tf.float32,shape=([None,ts_length]),name='R')
labels = tf.placeholder(tf.float32,shape=([None,1]),name='gt')
dropout_f = tf.placeholder("float")
with tf.variable_scope("siamese") as scope:
    model1= build_model_mlp(images_L,dropout_f, ts_length)
    scope.reuse_variables()
    model2 = build_model_mlp(images_R,dropout_f, ts_length)

distance  = tf.sqrt(tf.reduce_sum(tf.pow(tf.subtract(model1,model2),2),1,keep_dims=True))
#loss = contrastive_loss(labels,distance) + regularizer(model1, model2, r)
loss = c_loss(labels, model1, model2) + regularizer(model1, model2, r)
ugh = c_loss(labels, model1, model2)
regularization = regularizer(model1, model2, r)
#contrastice loss
t_vars = tf.trainable_variables()
d_vars  = [var for var in t_vars if 'l' in var.name]
batch = tf.Variable(0)
optimizer = tf.train.AdamOptimizer(learning_rate = 0.00015).minimize(loss)
#optimizer = tf.train.RMSPropOptimizer(0.00001,momentum=0.9,epsilon=1e-6).minimize(loss)
    # Launch the graph
f1 = open('X_output.txt', 'w')
f2 = open('X_labels.txt', 'w')
f1_t = open('X_output_test.txt', 'w')
f2_t = open('X_labels_test.txt', 'w')

with tf.Session() as sess:
#sess.run(init)
    tf.global_variables_initializer().run()
    # Training cycle
    for epoch in range(400):
        avg_loss = 0.
        avg_acc = 0.
        avg_r = 0.
        avg_c = 0.
        total_batch = int(tr_pairs.shape[0]/batch_size)
        start_time = time.time()
        # Loop over all batches
        for i in range(total_batch):
            s  = i * batch_size
            e = (i+1) *batch_size
            # Fit training using batch data
            input1,input2,y =next_batch(s,e,tr_pairs,tr_y)
            pdb.set_trace()
            feature1_before=model1.eval(feed_dict={images_L:input1,dropout_f:0.9})
            _,loss_value,predict, r_loss, lol=sess.run([optimizer,loss,distance, regularization, ugh], feed_dict={images_L:input1,images_R:input2 ,labels:y,dropout_f:0.9})
            feature1=model1.eval(feed_dict={images_L:input1,dropout_f:0.9})
            feature2=model2.eval(feed_dict={images_R:input2,dropout_f:0.9})
            tr_acc = compute_accuracy(predict,y)
            if math.isnan(tr_acc) and epoch != 0:
                print('tr_acc %0.2f' % tr_acc)
            avg_loss += loss_value
            avg_acc +=tr_acc*100
            avg_r += r_loss
            avg_c += lol


        #print('epoch %d loss %0.2f' %(epoch,avg_loss/total_batch))
        duration = time.time() - start_time
        print('epoch %d  time: %f loss %0.5f r_loss %0.5f c_loss %0.5f acc %0.2f' %(epoch,duration,avg_loss/(total_batch), avg_r/total_batch, avg_c/total_batch, avg_acc/total_batch))
    y = np.reshape(tr_y,(tr_y.shape[0],1))
    predict=distance.eval(feed_dict={images_L:tr_pairs[:,0],images_R:tr_pairs[:,1],labels:y,dropout_f:1.0})
    tr_acc = compute_accuracy(predict,y)
    print('Accuracy training set %0.2f' % (100 * tr_acc))

    # Test model
    predict=distance.eval(feed_dict={images_L:te_pairs[:,0],images_R:te_pairs[:,1],labels:y,dropout_f:1.0})
    y = np.reshape(te_y,(te_y.shape[0],1))
    te_acc = compute_accuracy(predict,y)
    print('Accuracy test set %0.2f' % (100 * te_acc))

    train_embedding=model1.eval(feed_dict={images_L:X_train,dropout_f:1.0})

    for coord, label in zip(train_embedding, y_train):
        f1.write(' '.join([str(a) for a in coord]) + "\n")
        f2.write(str(label) + "\n")

    test_embedding = model1.eval(feed_dict={images_L:X_test,dropout_f:1.0})

    for coord, label in zip(test_embedding, y_test):
        f1_t.write(' '.join([str(a) for a in coord]) + "\n")
        f2_t.write(str(label) + "\n")

    accuracy = evaluate_test_embedding(train_embedding, y_train, test_embedding, y_test)
    print('Accuracy given NN approach %0.2f' %(100*accuracy))
