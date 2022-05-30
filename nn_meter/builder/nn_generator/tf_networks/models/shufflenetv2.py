import tensorflow as tf 
from .ops import  *
from .utils import  *

class ShuffleNetV2:
    def __init__(self, x, cfg, version = None, sample = False, enable_out = False):  ## change channel number, kernel size
        self.input = x
        self.num_classes = cfg['n_classes']
        self.enable_out = enable_out

        self.bcs = [24] + [116] * 4 + [232] * 8 + [464] * 4 + [1024]
        self.bks = [3] + [3] * (4 + 8 + 4) + [1]
        self.bes = [1] + [6] * 16

        self.cs = get_sampling_channels(cfg['sample_space']['channel']['start'], cfg['sample_space']['channel']['end'], cfg['sample_space']['channel']['step'], len(self.bcs))
        self.ks = get_sampling_ks(cfg['sample_space']['kernelsize'], len(self.bks))
        self.mcs = get_sampling_channels(cfg['sample_space']['mid_channel']['start'], cfg['sample_space']['mid_channel']['end'], cfg['sample_space']['mid_channel']['step'], len(self.bcs))

        self.config = {}
        if sample == True:
            if len(self.cs) < 18:
                i = len(self.cs)
                self.cs.append([1 for _ in range(i)])
            if len(self.ks) < 18:
                i = len(self.ks)
                self.ks.append([3 for _ in range(i)] )
            self.ncs = [int(self.bcs[index] * self.cs[index]) for index in range(len(self.bcs))]
            self.nks = self.ks
        else:
            self.ncs = self.bcs 
            self.mcs = [1] * 17
            self.nks = self.bks 
            self.nes = self.bes

        self.sconfig = '_'.join([str(x) for x in self.nks]) + '-' + '_'.join([str(x) for x in self.ncs]) + '-' + '_'.join([str(x) for x in self.mcs])
        self.out = self.build()

    def add_to_log(self, op, cin, cout, ks, stride, layername, inputh, inputw):
        self.config[layername] = {}
        self.config[layername]['op'] = op
        self.config[layername]['cin'] = cin
        self.config[layername]['cout'] = cout
        self.config[layername]['ks'] = ks
        self.config[layername]['stride'] = stride 
        self.config[layername]['inputh'] = inputh
        self.config[layername]['inputw'] = inputw 

    def addblock_to_log(self, op, cin, cout, ks, stride, layername, inputh, inputw, es):
        self.config[layername] = {}
        self.config[layername]['op'] = op
        self.config[layername]['cin'] = cin
        self.config[layername]['cout'] = cout
        self.config[layername]['ks'] = ks
        self.config[layername]['stride'] = stride 
        self.config[layername]['inputh'] = inputh
        self.config[layername]['inputw'] = inputw 
        self.config[layername]['es'] = es

    def build(self):
        x = conv2d(self.input, self.ncs[0], self.nks[0], opname = 'conv1', stride = 2, padding = 'SAME') #def conv2d(_input, out_features, kernel_size, opname = '', stride = 1, padding = 'SAME', param_initializer = None):
        x = batch_norm(x, opname = 'conv1.bn')
        x = activation(x, 'relu', opname = 'conv1.relu')
        self.add_to_log('conv-bn-relu', 3, self.ncs[0], self.nks[0], 2, 'layer1', self.input.shape.as_list()[1], self.input.shape.as_list()[2])

        (h, w) = x.shape.as_list()[1:3]
        x = max_pooling(x, 3, 2, opname = 'conv1')
        self.add_to_log('max-pool', self.ncs[0], self.ncs[0], 3, 2, 'layer2', h, w)
        r = [4, 8, 4]
        s = [2, 2, 2]

        layercount = 2
        lastchannel = self.ncs[0]

        for index in range(len(r)):
            stride = s[index]
            layers = r[index]
            ep = r[index]
            for j in range(layers):
                sr = stride if j == 0 else 1

                if self.enable_out == False and sr == 1:
                    c_current = lastchannel
                else:
                    c_current = self.ncs[layercount-1]

                (h, w) = x.shape.as_list()[1: 3]
                x, log = shufflev2_unit(x, self.nks[layercount - 2], int(x.get_shape()[3]), c_current, sr,
                                        self.mcs[layercount-2], name = 'layer' + str(layercount), log = True)
                self.config.update(log)
                lastchannel = c_current
                layercount  += 1

        (h, w) = x.shape.as_list()[1:3]

        x = conv2d(x, self.ncs[layercount - 1], 1, opname = 'conv' + str(layercount) + '.1', stride = 1)
        x = batch_norm(x, opname = 'conv' + str(layercount) + '.1')
        x = activation(x, 'relu', opname = 'conv' + str(layercount) + '.1')
        self.add_to_log('conv-bn-relu', self.ncs[layercount - 2], self.ncs[layercount - 1], 1, 1, 'layer' + str(layercount) + '.1', h, w)

        x = tf.reduce_mean(x, axis = [1, 2], keep_dims = True)
        x = flatten(x)
        self.add_to_log('global-pool', self.ncs[layercount-1], self.ncs[layercount-1], None, None, 'layer' + str(layercount + 1), 1, 1)

        x = fc_layer(x, self.num_classes, opname = 'fc' + str(layercount + 1))
        self.add_to_log('fc', self.ncs[layercount-1], self.num_classes, None, None, 'layer' + str(layercount + 2), None, None)

        return x