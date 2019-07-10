import tensorflow as tf
import numpy as np
import pandas as pd
import scipy.io as sio
from data.load_beta_data import load_beta_data, load_beta_data_pool1, load_beta_data_pool2, load_beta_data_pool3
from data.load_single_data import test_batch
from model.CNN_BN import BaseCNN


def one_hot(labels, n_class = 7):
	""" One-hot encoding """
	expansion = np.eye(n_class)
	y = expansion[:, labels-1].T
	assert y.shape[1] == n_class, "Wrong number of labels!"
	return y
fliter = [16, 32, 64, 128]
chan = [9, 5, 5, 3, 3, 2, 2]
# 神经网络的参数
bat = [5424, 10376, 7310, 5228, 4284, 2870, 6015, 4192, 8457, 8026, 7781, 10608, 916, 4338, 2089]
Batch_Size = 100
Learning_Rate_Base = 0.0005
Learning_Rate_Decay = 0.99
Regularazition_Rate = 0.0005
Training_Steps = 967
Moving_Average_Decay =0.99
Model_Save_Path = "H:/SpaceWork/EEG_Work/Model/CNN_BN_v12"
Model_Name = "model.ckpt"
def evaluate(num):
    # num 表示要取那个人的数据
    # return 第num 个人数据经过测试得到数据。
    with tf.name_scope("input"):
        input_x = tf.placeholder(tf.float32, [bat[num], 500, 9, 1], name='EEG-input')  # 数据的输入，第一维表示一个batch中样例的个数
        input_y = tf.placeholder(tf.float32, [None, 7], name='EEG-lable')  # 一个batch里的lable
    regularlizer = tf.contrib.layers.l2_regularizer(Regularazition_Rate)#本来测试的时候不用加这个
    is_training = tf.cast(False, tf.bool)
    out = BaseCNN(input_x, is_training, regularlizer)
    y = out['logit']
    with tf.name_scope("test_acc"):
        correct_predection = tf.equal(tf.argmax(y,1),tf.argmax(input_y,1))
        accuracy = tf.reduce_mean(tf.cast(correct_predection,tf.float32))
        tf.summary.scalar('test_acc', accuracy)
    variable_averages = tf.train.ExponentialMovingAverage(Moving_Average_Decay)
    variables_to_restore = variable_averages.variables_to_restore()
    saver = tf.train.Saver(variables_to_restore)
    with  tf.Session() as sess:
        ckpt = tf.train.get_checkpoint_state(Model_Save_Path)
        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess,ckpt.model_checkpoint_path)
            global_step = ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1]
            x, y = test_batch(num)#获取第x个人的数据
            reshape_xs = np.reshape(x,(-1,500,9,1))
            ys = one_hot(y)
            conv1, pool1, conv2, pool2, conv3, pool3, conv4, pool4, acc_score =sess.run([out['conv1'], out['pool1'], out['conv2'], out['pool2'],
                                                                                         out['conv3'], out['pool3'], out['conv4'], out['pool4'],
                                                                                         accuracy],feed_dict={input_x: reshape_xs, input_y: ys})
            print("Afer %s training step, test accuracy = %g" % (global_step,acc_score))
        else :
            print("No checkpoint file found")
    return  conv1, pool1, conv2, pool2, conv3, pool3, conv4, pool4
def get_corr_fliter(num,data,channle,fliter,pool):
    """

    :param num: 要处理的第几个人的数据
    :param data: 神经网络处理得到的数据
    :param channle: 神经网络下的通道数
    :param fliter: 该data下的滤波器数
    :return:
    """
    list = []
    # con = evaluate(num,9,'conv1',16,2712000)#返回各通道滤波器下的list evaluate(num,channel,name,fliter,size):
    # num 表示要取那个人的数据，channel 表示对那个隐藏层通道数据感兴趣，name表示是哪一层，fliter 表示神经网络中间层滤波器的数量 size隐藏层处理数据长度
    # return 第num 个人数据经过测试得到的在name层处理后的输出数据对应channel的值。
    for i in range(channle):
        temp = data[i]#得到第k通道下各滤波器数据
        oneObject = []
        for j in range(9):
            if pool ==0:
                ga = load_beta_data(num,j)#获取要进行相关性分析的对象数据
            if pool>0 and pool <=2:
                ga = load_beta_data_pool1(num,j)
            if pool>2 and pool <=4:
                ga = load_beta_data_pool2(num,j)
            if pool>4 and pool <=6:
                ga = load_beta_data_pool3(num,j)
            cost = []
            for k in range(fliter):
                cor = pd.DataFrame({'raw': temp[k], 'gamma': ga})  # 构建相关性的数据型
                cost.append(cor.raw.corr(cor.gamma))  # 得到各滤波器与预处理数据的相关性值
            x = np.mean(cost)
            oneObject.append(x)  # oneObject 为一维矩阵
            print("神经网络第 %g通道后的数据与原通道 %g的相关性为：%g " % (i,j,x))
        list.append(oneObject)  # 二维矩阵
    return list

def sum(num):
    conv1, pool1, conv2, pool2, conv3, pool3, conv4, pool4 = evaluate(num)
    name = [conv1, pool1, conv2, pool2, conv3, pool3, conv4, pool4]
    name1 = ['conv1', 'pool1', 'conv2', 'pool2', 'conv3', 'pool3', 'conv4', 'pool4']
    X_corr = []
    # channel_name = ['Lflv', 'Rflv', 'BP', '1', '2', '3', '4', '5', '6']
    channel = ['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7']
    for i in range(7):
        #     print(fliter[int(i/2)])`
        data = name[i]
        list = []
        size = data.shape[0] * data.shape[1]  # 对应滤波alpha or gamma or ... 原始数据通道铺平的长度
        for j in range(chan[i]):  # 隐藏层各通道
            flag = []
            for k in range(fliter[int(i / 2)]):  # 神经网络fliter器数量
                temp = data[:, :, j, k]  #
                temp = np.reshape(temp, [size])
                flag.append(temp)  # 第j个通道下各滤波器下的值
            list.append(flag)  # 所有通道
        print("第%g神经层数据相关性处理开始：" % (i))
        channel[i] = get_corr_fliter(num, list, chan[i], fliter[int(i / 2)], i)
        channel[i] = np.array(channel[i])
        channel[i] = np.reshape(channel[i],(-1,9))

    sio.savemat('D:/data_corr/beta/'+str(num)+'.mat', {name1[0]:channel[0], name1[1]:channel[1], name1[2]:channel[2], name1[3]:channel[3], name1[4]:channel[4],name1[5]:channel[5],name1[6]:channel[6]})





def main(argv=None):
    for i in range(8, 15):
        tf.reset_default_graph() # Python的控制台会保存上次运行结束的变量，需要将之前的结果清除
        sum(i)
    # sum(0) # 计算第num个人的数据分析



if __name__ == '__main__':
    tf.app.run()