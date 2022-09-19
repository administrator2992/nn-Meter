# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
from nn_meter.builder.utils import make_divisible
from nn_meter.builder.kernel_predictor_builder.predictor_builder.utils import get_conv_flop_params, get_dwconv_flop_params, get_fc_flop_params


def add_flops_param(res):
    for kernel in res:
        if kernel == 'conv-bn-relu':
            for item in res[kernel]:
                hw, cin, cout, kernel_size, stride = item
                flops, params = get_conv_flop_params(hw, cin, cout, kernel_size, stride)
                flops /= 2e6
                params /= 1e6
                item.extend([flops, params])
        elif kernel == 'dwconv-bn-relu':
            for item in res[kernel]:
                hw, _, cout, kernel_size, stride = item
                flops, params = get_dwconv_flop_params(hw, cout, kernel_size, stride)
                flops /= 2e6
                params /= 1e6
                item.extend([flops, params])
        elif kernel == 'fc':
            for item in res[kernel]:
                cin, cout = item
                flops, params = get_fc_flop_params(cin, cout)
                flops /= 2e6
                params /= 1e6
                item.extend([flops, params])
    return res
                


def get_block_arch_by_name(block, hw, cin, cout, kernel_size, expand_ratio, stride):

    if block == "FirstConvBlock_hswish": 
        '''
        get_block_arch_by_name("FirstConvBlock_hswish", 224, 3, 16, 3, 0, 2) 
        ############ conv-bn-relu 1.3386911250000026
        ([224, 3, 16, 3, 2, 5.619712, 0.000448], 1.3386911250000026)
        ############ hswish 0.48690411216216334
        ([112, 16], 0.48690411216216334)
        '''
        res = {
            'conv-bn-relu': [
                [hw, cin, cout, kernel_size, stride]
            ],
            'hswish': [
                [hw // stride, cout]
            ]
        }
        
    elif block == "FirstConvBlock_relu":
        '''
        get_block_arch_by_name("FirstConvBlock_relu", 224, 3, 16, 3, 0, 2) 
        ############ conv-bn-relu 1.3386911250000026
        ([224, 3, 16, 3, 2, 5.619712, 0.000448], 1.3386911250000026)
        '''
        res = {
            'conv-bn-relu': [
                [hw, cin, cout, kernel_size, stride]
            ]
        }
    elif block == "FinalExpandBlock_hswish":
        res = {
            'conv-bn-relu': [
                [hw, cin, cout, kernel_size, stride]
            ],
            'hswish': [
                [hw // stride, cout]
            ]
        }
    elif block == "FinalExpandBlock_swish":
        res = {
            'conv-bn-relu': [
                [hw, cin, cout, kernel_size, stride]
            ],
            'swish': [
                [hw // stride, cout]
            ]
        }
    elif block == "FinalExpandBlock_relu":
        res = {
            'conv-bn-relu': [
                [hw, cin, cout, kernel_size, stride]
            ]
        }
    elif block == "FeatureMixBlock_hswish":
        res = {
            'gap': [
                [hw, cin]
            ],
            'conv-bn-relu': [
                [1, cin, cout, kernel_size, stride]
            ],
            'hswish': [
                [1, cout]
            ]
        }
    elif block == "FeatureMixBlock_relu":
        res = {
            'gap': [
                [hw, cin]
            ],
            'conv-bn-relu': [
                [1, cin, cout, kernel_size, stride]
            ]
        }
    elif block == "FeatureMixBlock_swish":
        res = {
            'gap': [
                [hw, cin]
            ],
            'conv-bn-relu': [
                [1, cin, cout, kernel_size, stride]
            ]
        }
    elif block == "LogitsBlock":
        '''
        get_block_arch_by_name("LogitsBlock", 1, 1280, 1000, 0, 0, 0)
        ############ gap 0.17857104864864878
        ([1, 1280], 0.17857104864864878)
        ############ fc 0.25056936216216186
        ([1280, 1000, 1.2805, 2.561], 0.25056936216216186)
        '''
        res = {
            'fc': [
                [cin, cout]
            ]
        }
    
    # ResNetBlock
    elif block == "ResNetBlock_ds_relu":
        '''
        get_block_arch_by_name("ResNetBlock_ds_relu", 224, 3, 16, 3, 3, 2)
        # ############ conv-bn-relu 10.479946887187499
        # ([224, 3, 48, 1, 1, 9.633792, 0.000192], 1.4586173656249992)
        # ([224, 48, 48, 3, 2, 260.714496, 0.020784], 7.908706312499999)
        # ([112, 48, 16, 1, 1, 9.834496, 0.000784], 0.5328625718749995)
        # ([224, 3, 16, 1, 2, 0.802816, 6.4e-05], 0.5797606371875004)
        # ############ add-relu 0.2508110596846853
        # ([112, 16, 16], 0.2508110596846853)
        '''
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride], 
            ],
            'add-relu': [
                [hw // stride, cout, cout]
            ]
        }
        
    elif block == "ResNetBlock_nods_relu":
        '''
        ############ conv-bn-relu 78.5685154687502
        ([112, 64, 192, 1, 1, 156.54912, 0.01248], 4.483061250000012)
        ([112, 192, 192, 3, 1, 4164.206592, 0.331968], 70.3057246875002)
        ([112, 192, 64, 1, 1, 154.943488, 0.012352], 3.7797295312500028)
        ############ add-relu 1.0211713975975982
        ([112, 64, 64], 1.0211713975975982)
        '''
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw, feature_size, cout, 1, 1],
            ],
            'add-relu': [
                [hw, cout, cout]
            ]
        }
        
    elif block == "ResNetBlock_ds_hswish":
        '''
        ############ conv-bn-relu 10.479946887187499
        ([224, 3, 48, 1, 1, 9.633792, 0.000192], 1.4586173656249992)
        ([224, 48, 48, 3, 2, 260.714496, 0.020784], 7.908706312499999)
        ([112, 48, 16, 1, 1, 9.834496, 0.000784], 0.5328625718749995)
        ([224, 3, 16, 1, 2, 0.802816, 6.4e-05], 0.5797606371875004)
        ############ hswish 7.977336407400266
        ([224, 48], 6.0668093564993555)
        ([112, 48], 1.423622938738747)
        ([112, 16], 0.48690411216216334)
        ############ add 0.2562164959459452
        ([112, 16, 16], 0.2562164959459452)
        '''
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride], 
            ],
            'hswish':[
                [hw, feature_size],
                [hw // stride, feature_size],
                [hw // stride, cout]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }
        
    elif block == "ResNetBlock_nods_hswish":
        '''
        ############ conv-bn-relu 78.5685154687502
        ([112, 64, 192, 1, 1, 156.54912, 0.01248], 4.483061250000012)
        ([112, 192, 192, 3, 1, 4164.206592, 0.331968], 70.3057246875002)
        ([112, 192, 64, 1, 1, 154.943488, 0.012352], 3.7797295312500028)
        ############ hswish 13.263483532947243
        ([112, 192], 5.691717582689833)
        ([112, 192], 5.691717582689833)
        ([112, 64], 1.8800483675675763)
        ############ add 1.0093378702702738
        ([112, 64, 64], 1.0093378702702738)
        '''
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw, feature_size, cout, 1, 1],
            ],
            'hswish': [
                [hw, feature_size],
                [hw, feature_size],
                [hw, cout]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    # ResNetSEBlock
    elif block == "ResNetSEBlock_ds_relu":
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride], 
            ],
            'add-relu': [
                [hw // stride, cout, cout]
            ],
            'resnet-se': [
                [hw // stride, feature_size, make_divisible(cin // 4)]
            ]
        }
        
    elif block == "ResNetSEBlock_nods_relu":
        '''
        ############ conv-bn-relu 78.5685154687502
        ([112, 64, 192, 1, 1, 156.54912, 0.01248], 4.483061250000012)
        ([112, 192, 192, 3, 1, 4164.206592, 0.331968], 70.3057246875002)
        ([112, 192, 64, 1, 1, 154.943488, 0.012352], 3.7797295312500028)
        ############ add-relu 1.0211713975975982
        ([112, 64, 64], 1.0211713975975982)
        '''
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw, feature_size, cout, 1, 1],
            ],
            'add-relu': [
                [hw, cout, cout]
            ],
            'resnet-se': [
                [hw, feature_size, make_divisible(cin // 4)]
            ]
        }
        
    elif block == "ResNetSEBlock_ds_hswish":
        '''
        ############ conv-bn-relu 10.479946887187499
        ([224, 3, 48, 1, 1, 9.633792, 0.000192], 1.4586173656249992)
        ([224, 48, 48, 3, 2, 260.714496, 0.020784], 7.908706312499999)
        ([112, 48, 16, 1, 1, 9.834496, 0.000784], 0.5328625718749995)
        ([224, 3, 16, 1, 2, 0.802816, 6.4e-05], 0.5797606371875004)
        ############ hswish 7.977336407400266
        ([224, 48], 6.0668093564993555)
        ([112, 48], 1.423622938738747)
        ([112, 16], 0.48690411216216334)
        ############ add 0.2562164959459452
        ([112, 16, 16], 0.2562164959459452)
        '''
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride], 
            ],
            'hswish':[
                [hw, feature_size],
                [hw // stride, feature_size],
                [hw // stride, cout]
            ],
            'add': [
                [hw // stride, cout, cout]
            ],
            'resnet-se': [
                [hw // stride, feature_size, make_divisible(cin // 4)]
            ]
        }
        
    elif block == "ResNetSEBlock_nods_hswish":
        '''
        ############ conv-bn-relu 78.5685154687502
        ([112, 64, 192, 1, 1, 156.54912, 0.01248], 4.483061250000012)
        ([112, 192, 192, 3, 1, 4164.206592, 0.331968], 70.3057246875002)
        ([112, 192, 64, 1, 1, 154.943488, 0.012352], 3.7797295312500028)
        ############ hswish 13.263483532947243
        ([112, 192], 5.691717582689833)
        ([112, 192], 5.691717582689833)
        ([112, 64], 1.8800483675675763)
        ############ add 1.0093378702702738
        ([112, 64, 64], 1.0093378702702738)
        '''
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, feature_size, kernel_size, stride],
                [hw, feature_size, cout, 1, 1],
            ],
            'hswish': [
                [hw, feature_size],
                [hw, feature_size],
                [hw, cout]
            ],
            'add': [
                [hw, cout, cout]
            ],
            'resnet-se': [
                [hw, feature_size, make_divisible(cin // 4)]
            ]
        }
    
    
    # MobileNetV1DualBlock
    elif block == "MobileNetV1DualBlock_ds":
        '''
        ############ dwconv-bn-relu 0.8327714910331794
        ([112, 64, 64, 3, 1, 8.02816, 0.00064], 0.8327714910331794)
        ############ conv-bn-relu 3.0310546874999935
        ([112, 64, 128, 1, 1, 104.36608, 0.00832], 3.0310546874999935)
        '''
        res = {
            'dwconv-bn-relu': [
                [hw, cin, cin, kernel_size, stride],
                [hw // stride, cout, cout, kernel_size, 1]
            ],
            'conv-bn-relu': [
                [hw // stride, cin, cout, 1, 1],
                [hw // stride, cout, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'add':[
                [hw // stride, cout, cout]
            ]
        }
    
    elif block == "MobileNetV1DualBlock_nods":
        '''
        ############ dwconv-bn-relu 0.8327714910331794
        ([112, 64, 64, 3, 1, 8.02816, 0.00064], 0.8327714910331794)
        ############ conv-bn-relu 3.0310546874999935
        ([112, 64, 128, 1, 1, 104.36608, 0.00832], 3.0310546874999935)
        '''
        assert cin == cout and stride == 1
        res = {
            'dwconv-bn-relu': [
                [hw, cin, cin, kernel_size, stride],
                [hw, cout, cout, kernel_size, 1]
            ],
            'conv-bn-relu': [
                [hw // stride, cin, cout, 1, 1],
                [hw // stride, cout, cout, 1, 1]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    # MobileNetV2ResBlock & MobileNetV3ResBlock
    elif block == "MobileNetV3ResBlock_res_relu":
        '''
        ## -------- conv-bn-relu 156.15345097560976
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 73.92951073170747)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 82.22394024390228)
        ## -------- dwconv-bn-relu 36.64503500000003
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 36.64503500000003)
        ## -------- se 3.13890996551725
        ([224, 192], 3.13890996551725)
        ## -------- add 0.01680175438596493
        ([224, 64, 64], 0.01680175438596493)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw, feature_size]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }
        
    elif block =="MobileNetV3ResBlock_forceres_relu":
        '''
        conv-bn-relu, 1.3370139341463414, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.0323349585365873, 56, 48, 64, 1, 1, 9.834496, 0.003136
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        se, 0.20650520000000067, 56, 48
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw // stride, feature_size]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }

    elif block == "MobileNetV3ResBlock_res_swish":
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'swish': [
                [hw, feature_size],
                [hw, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw, feature_size]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    elif block =="MobileNetV3ResBlock_forceres_swish":
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'swish': [
                [hw, feature_size],
                [hw // stride, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw // stride, feature_size]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }

    elif block == "MobileNetV3ResBlock_res_swish":
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'swish': [
                [hw, feature_size],
                [hw, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw, feature_size]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    elif block == "MobileNetV3ResBlock_forceres_swish":
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'swish': [
                [hw, feature_size],
                [hw // stride, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw // stride, feature_size]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }

    elif block == 'FusedMBConvSEResBlock_res_swish':
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, kernel_size, stride],
                [hw // stride, feature_size, cout, 1, 1],
            ],
            'swish': [
                [hw // stride, feature_size]
            ],
            'se': [ 
                [hw // stride, feature_size]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }

    elif block == 'FusedMBConvSEResBlock_forceres_swish':
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, kernel_size, stride],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'swish': [
                [hw // stride, feature_size]
            ],
            'se': [ 
                [hw // stride, feature_size]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }

    elif block == "MobileNetV3K3ResBlock_res_swish":

        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'swish': [
                [hw, feature_size],
                [hw, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, 3, stride]
            ],
            'se': [
                [hw, feature_size]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }
        num_dwconv = {3:1, 5:2, 7:3}[kernel_size]
        for _ in range(num_dwconv - 1):
            res['dwconv-bn-relu'].append([hw // stride, feature_size, feature_size, 3, 1])
        
    elif block == "MobileNetV3K3ResBlock_forceres_swish":
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'swish': [
                [hw, feature_size],
                [hw // stride, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, 3, stride]
            ],
            'se': [
                [hw // stride, feature_size]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }
        num_dwconv = {3:1, 5:2, 7:3}[kernel_size]
        for _ in range(num_dwconv - 1):
            res['dwconv-bn-relu'].append([hw // stride, feature_size, feature_size, 3, 1])

    elif block == "MobileNetV2K3ResBlock_res_relu":
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, 3, stride]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }
        num_dwconv = {3:1, 5:2, 7:3}[kernel_size]
        for _ in range(num_dwconv - 1):
            res['dwconv-bn-relu'].append([hw // stride, feature_size, feature_size, 3, 1])
        
    elif block == "MobileNetV2K3ResBlock_forceres_relu":
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, 3, stride]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }
        num_dwconv = {3:1, 5:2, 7:3}[kernel_size]
        for _ in range(num_dwconv - 1):
            res['dwconv-bn-relu'].append([hw // stride, feature_size, feature_size, 3, 1])

    elif block == "MobileNetV2ResBlock_res_relu":
        '''
        ############ conv-bn-relu 30.729888468749948
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 16.298127874999988)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 14.431760593749962)
        ############ dwconv-bn-relu 25.73912930555556
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 25.73912930555556)
        ############ add 4.051908842105283
        ([224, 64, 64], 4.051908842105283)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }
        
    elif block == "MobileNetV2ResBlock_forceres_relu":
        '''
        conv-bn-relu, 1.3370139341463414, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.0323349585365869, 56, 48, 64, 1, 1, 9.834496, 0.003136
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }
        
    elif block == "MobileNetV3ResBlock_res_hswish":
        '''
        ## -------- conv-bn-relu 156.15345097560976
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 73.92951073170747)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 82.22394024390228)
        ## -------- hswish 6.237716736842104
        ([224, 192], 3.118858368421052)
        ([224, 192], 3.118858368421052)
        ## -------- dwconv-bn-relu 36.64503500000003
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 36.64503500000003)
        ## -------- se 3.13890996551725
        ([224, 192], 3.13890996551725)
        ## -------- add 0.01680175438596493
        ([224, 64, 64], 0.01680175438596493)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'hswish': [
                [hw, feature_size],
                [hw, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw, feature_size]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }
        
    elif block == "MobileNetV3ResBlock_forceres_hswish":
        '''
        conv-bn-relu, 1.3370139341463416, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.032334958536587, 56, 48, 64, 1, 1, 9.834496, 0.003136
        hswish, 0.6711426578947358, 112, 48
        hswish, 0.15845252631578968, 56, 48
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        se, 0.20650520000000067, 56, 48
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'hswish': [
                [hw, feature_size],
                [hw // stride, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw // stride, feature_size]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }
        
    elif block == "MobileNetV2ResBlock_res_hswish":
        '''
        ############ conv-bn-relu 30.729888468749948
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 16.298127874999988)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 14.431760593749962)
        ############ hswish 43.981615621621536
        ([224, 192], 21.990807810810768)
        ([224, 192], 21.990807810810768)
        ############ dwconv-bn-relu 25.73912930555556
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 25.73912930555556)
        ############ add 4.051908842105283
        ([224, 64, 64], 4.051908842105283)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'hswish': [
                [hw, feature_size],
                [hw, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }
        
    elif block == "MobileNetV2ResBlock_forceres_hswish":
        '''
        conv-bn-relu, 1.3370139341463414, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.0323349585365869, 56, 48, 64, 1, 1, 9.834496, 0.003136
        hswish, 0.6711426578947358, 112, 48
        hswish, 0.15845252631578968, 56, 48
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1],
                [hw, cin, cout, 1, stride]
            ],
            'hswish': [
                [hw, feature_size],
                [hw // stride, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'add': [
                [hw // stride, cout, cout]
            ]
        }

    # MobileNetV1Block
    elif block == "MobileNetV1Block":
        '''
        ############ dwconv-bn-relu 0.8327714910331794
        ([112, 64, 64, 3, 1, 8.02816, 0.00064], 0.8327714910331794)
        ############ conv-bn-relu 3.0310546874999935
        ([112, 64, 128, 1, 1, 104.36608, 0.00832], 3.0310546874999935)
        '''
        res = {
            'dwconv-bn-relu': [
                [hw, cin, cin, kernel_size, stride]
            ],
            'conv-bn-relu': [
                [hw // stride, cin, cout, 1, 1]
            ]
        }

    elif block == "MobileNetV3Block_res_relu":
        '''
        ## -------- conv-bn-relu 156.15345097560976
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 73.92951073170747)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 82.22394024390228)
        ## -------- dwconv-bn-relu 36.64503500000003
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 36.64503500000003)
        ## -------- se 3.13890996551725
        ([224, 192], 3.13890996551725)
        ## -------- add 0.01680175438596493
        ([224, 64, 64], 0.01680175438596493)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw, feature_size]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    elif block =="MobileNetV3Block_nores_relu":
        '''
        conv-bn-relu, 1.3370139341463414, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.0323349585365873, 56, 48, 64, 1, 1, 9.834496, 0.003136
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        se, 0.20650520000000067, 56, 48
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw // stride, feature_size]
            ],
        }

    elif block == "MobileNetV2Block_res_relu":
        '''
        ############ conv-bn-relu 30.729888468749948
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 16.298127874999988)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 14.431760593749962)
        ############ dwconv-bn-relu 25.73912930555556
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 25.73912930555556)
        ############ add 4.051908842105283
        ([224, 64, 64], 4.051908842105283)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    elif block == "MobileNetV2Block_nores_relu":
        '''
        conv-bn-relu, 1.3370139341463414, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.0323349585365869, 56, 48, 64, 1, 1, 9.834496, 0.003136
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ]
        }

    elif block == "MobileNetV3Block_res_hswish":
        '''
        ## -------- conv-bn-relu 156.15345097560976
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 73.92951073170747)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 82.22394024390228)
        ## -------- hswish 6.237716736842104
        ([224, 192], 3.118858368421052)
        ([224, 192], 3.118858368421052)
        ## -------- dwconv-bn-relu 36.64503500000003
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 36.64503500000003)
        ## -------- se 3.13890996551725
        ([224, 192], 3.13890996551725)
        ## -------- add 0.01680175438596493
        ([224, 64, 64], 0.01680175438596493)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'hswish': [
                [hw, feature_size],
                [hw, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw, feature_size]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    elif block == "MobileNetV3Block_nores_hswish":
        '''
        conv-bn-relu, 1.3370139341463416, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.032334958536587, 56, 48, 64, 1, 1, 9.834496, 0.003136
        hswish, 0.6711426578947358, 112, 48
        hswish, 0.15845252631578968, 56, 48
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        se, 0.20650520000000067, 56, 48
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1]
            ],
            'hswish': [
                [hw, feature_size],
                [hw // stride, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'se': [
                [hw // stride, feature_size]
            ],
        }

    elif block == "MobileNetV2Block_res_hswish":
        '''
        ############ conv-bn-relu 30.729888468749948
        ([224, 64, 192, 1, 1, 626.19648, 0.01248], 16.298127874999988)
        ([224, 192, 64, 1, 1, 619.773952, 0.012352], 14.431760593749962)
        ############ hswish 43.981615621621536
        ([224, 192], 21.990807810810768)
        ([224, 192], 21.990807810810768)
        ############ dwconv-bn-relu 25.73912930555556
        ([224, 192, 192, 3, 1, 96.33792, 0.00192], 25.73912930555556)
        ############ add 4.051908842105283
        ([224, 64, 64], 4.051908842105283)
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw, feature_size, cin, 1, 1]
            ],
            'hswish': [
                [hw, feature_size],
                [hw, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ],
            'add': [
                [hw, cout, cout]
            ]
        }

    elif block == "MobileNetV2Block_nores_hswish":
        '''
        conv-bn-relu, 1.3370139341463414, 112, 16, 48, 1, 1, 10.235904, 0.000816
        conv-bn-relu, 1.0323349585365869, 56, 48, 64, 1, 1, 9.834496, 0.003136
        hswish, 0.6711426578947358, 112, 48
        hswish, 0.15845252631578968, 56, 48
        dwconv-bn-relu, 1.0788487708333323, 112, 48, 48, 3, 2, 1.50528, 0.00048
        '''
        feature_size = make_divisible(cin * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, feature_size, 1, 1],
                [hw // stride, feature_size, cout, 1, 1]
            ],
            'hswish': [
                [hw, feature_size],
                [hw // stride, feature_size]
            ],
            'dwconv-bn-relu': [
                [hw, feature_size, feature_size, kernel_size, stride]
            ]
        }

    elif block.startswith("ResNetBugBlock_nods"):
        res = {
        }
        
    elif block.startswith("ResNetBugBlock_ds"):
        feature_size = make_divisible(cout * expand_ratio)
        res = {
            'conv-bn-relu': [
                [hw, cin, cout, 1, stride], 
            ],
        }
    else:
        raise ValueError(block)
    res = add_flops_param(res)
    # print(res)
    return res
