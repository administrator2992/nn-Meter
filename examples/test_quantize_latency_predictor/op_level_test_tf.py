import os
import pickle
import tensorflow as tf
from tensorflow.keras import layers
from nn_meter.predictor import load_latency_predictor
from nn_meter.builder.backends import connect_backend
from nn_meter.builder import builder_config
from nn_meter.builder.modules.tf_networks.utils import get_inputs_by_shapes
from nn_meter.predictor.prediction.utils import latency_metrics_acc20 as latency_metrics
from nn_meter.builder.kernel_predictor_builder.predictor_builder.utils import get_flops_params

from nas_models.blocks.tf.mobilenetv3_block import HSigmoid
from nas_models.common import make_divisible
from op_code_tf import SE_NNMETER, SE_OFA, SE_xudong, HSwish_NNMETER, HSwish_OFA, HSwishBlock_xudong

workspace = "/data1/jiahang/working/pixel4_mobilenetv3_workspace"
builder_config.init(workspace)
backend_name='tflite_cpu_int8'
backend = connect_backend(backend_name)

output_path = "/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor"
output_name = os.path.join(output_path, "MobilenetV3_test")
predictor_name = "tflite27_cpu_int8"
# predictor_name = "cortexA76cpu_tflite21"
# predictor = load_latency_predictor(predictor_name)


def profile_and_predict(model, input_shape, name="se"):
    # print("\n")
    # print(model)
    # input_shape example [224, 224, 3]
    model(get_inputs_by_shapes([[*input_shape]]))
    tf.keras.models.save_model(model, output_name)

    res = backend.profile_model_file(output_name, output_path, input_shape=[[*input_shape]])
 
    # pred_lat = predictor.predict(model, "torch", input_shape=tuple([1] + input_shape), apply_nni=False) # in unit of ms
    pred_lat = sum(predictor.kernel_predictors[name].predict([[input_shape[0], input_shape[-1]]])) # in unit of ms
    print("profiled: ", res["latency"].avg, "predicted: ", pred_lat)
    # input_shape = list(model(get_inputs_by_shapes([[*input_shape]], 1)).shape)[1:]
    return res["latency"].avg, pred_lat


def profile_model(model, input_shape):
    # print("\n")
    # print(model)
    model(get_inputs_by_shapes([[*input_shape]]))
    # import pdb; pdb.set_trace()
    tf.keras.models.save_model(model, output_name)
    if backend_name == 'tflite_cpu_int8':
        res = backend.profile_model_file(output_name, output_path, input_shape=[[*input_shape]])
    else:
        res = backend.profile_model_file(output_name, output_path, input_shape=[[*input_shape]],
                                     close_xnnpack=True)

    return res["latency"].avg


def compare_op_hswish():
    configs = [
        # HW, CIN
        [112, 16], [28, 120], [14, 120], [14, 480], [14, 480],
        [14, 240], [14, 240], [14, 320], [14, 320], [14, 672],
        [14, 672], [14, 448], [14, 448], [14, 336], [14, 336],
        [14, 672], [7, 672], [7, 640], [7, 640], [7, 480],
        [7, 480], [7, 960], [1, 1280],
    ]
    models = [HSwish_NNMETER, HSwish_OFA]

    for model_cls in models:
        reals, preds = [], []
        for i, config in enumerate(configs):
            hwin, cin = config
            input_shape = [hwin, hwin, cin]
            model = model_cls()
            real, pred = profile_and_predict(model, input_shape, 'hswish')
            reals.append(real)
            preds.append(pred)

        rmse, rmspe, error, acc5, acc10, acc15 = latency_metrics(preds, reals)
        for item in zip(preds, reals):
            print(item)
        print(f"[Hswish] rmse: {rmse}, rmspe: {rmspe}, error: {error}, acc5: {acc5}, acc10: {acc10}, acc15: {acc15}")
    # [Hswish(nn-meter)] rmse: 0.005325419195994526, rmspe: 128.7342249029692, error: 0.03191439393194509, acc5: 0.9565217391304348, acc10: 0.9565217391304348, acc15: 0.9565217391304348
    # [Hswish(Xudong version)] rmse: 0.14610096071155015, rmspe: 611.0362854025838, error: 3.26282225890695, acc5: 0.0, acc10: 0.0, acc15: 0.0


def compare_op_se():
    configs = [
        # HW, CIN
        [28, 72], [28, 160], [14, 320], [14, 672],
        [14, 448], [14, 336], [7, 672], [7, 640], [7, 480]
    ]
    models = [SE_OFA]

    for model_cls in models:
        reals, preds = [], []
        for i, config in enumerate(configs):
            hwin, cin = config
            input_shape = [hwin, hwin, cin]
            model = model_cls(cin, hwin)
            real, pred = profile_and_predict(model, input_shape, 'se')
            reals.append(real)
            preds.append(pred)

        rmse, rmspe, error, acc5, acc10, acc15 = latency_metrics(preds, reals)
        for item in zip(preds, reals):
            print(item)
        print(f"[SE] rmse: {rmse}, rmspe: {rmspe}, error: {error}, acc5: {acc5}, acc10: {acc10}, acc15: {acc15}")

    # SE_NNMETER: [SE] rmse: 0.01494647811039525, rmspe: 12.331616679372031, error: 0.14495697356533918, acc5: 0.5555555555555556, acc10: 0.5555555555555556, acc15: 0.6666666666666666
    # SE_OFA: [SE] rmse: 2.0208344320323324, rmspe: 93.8414818102769, error: 1.0535283572775551, acc5: 0.0, acc10: 0.0, acc15: 0.0


def compare_op_dwconv():
    from tensorflow import keras
    from nas_models.blocks.tf.mobilenetv3_block import build_act
    class DwconvTest(tf.keras.Model):
        def __init__(self, kernel_size, strides, act):
            super().__init__()
            self.depth_conv = tf.keras.Sequential([
                        keras.layers.DepthwiseConv2D(kernel_size=kernel_size, strides=strides, padding='same'),
                        keras.layers.BatchNormalization(),
                        build_act(act)
                    ])
        def call(self, x):
            x = self.depth_conv(x)
            return x

    def profile_and_predict(model, input_shape, name="se"):
        print("\n")
        # print(model)
        # input_shape example [224, 224, 3]
        model(get_inputs_by_shapes([[*input_shape]]))
        tf.keras.models.save_model(model, output_name)

        res = backend.profile_model_file(output_name, output_path, input_shape=[[*input_shape]])
    
        # pred_lat = predictor.predict(model, "torch", input_shape=tuple([1] + input_shape), apply_nni=False) # in unit of ms
        pred_lat = sum(predictor.kernel_predictors[name].predict([[28, 240, 240, 3, 1, 1.8816, 0.0024]])) # in unit of ms
        print("profiled: ", res["latency"].avg, "predicted: ", pred_lat)
        # input_shape = list(model(get_inputs_by_shapes([[*input_shape]], 1)).shape)[1:]
        return res["latency"].avg, pred_lat
    predictor = load_latency_predictor(predictor_name)
    model = DwconvTest(3, 1, 'relu')
    # model(get_inputs_by_shapes([[28, 28, 240]], batch_size=1))
    profile_and_predict(model, [28, 28, 240], 'dwconv-bn-relu')


def get_feature(kernel_type, config_dict):
    needed_config = {
        "conv-bn-relu": ["HW", "CIN", "COUT", "KERNEL_SIZE", "STRIDES"],
        "dwconv-bn-relu": ["HW", "CIN", "COUT", "KERNEL_SIZE", "STRIDES"],
        "se": ["HW", "CIN"],
        "hswish": ["HW", "CIN"],
    }
    if "COUT" not in config_dict and "COUT" in needed_config[kernel_type]:
        config_dict["COUT"] = config_dict["CIN"]
    feature = [config_dict[data] for data in needed_config[kernel_type]]
    if kernel_type in ["conv-bn-relu", "dwconv-bn-relu"]:
        flop, param = get_flops_params(kernel_type, config_dict)
        flop /= 2e6
        param /= 1e6
        feature.extend([flop, param])
    return feature

## ------------- op level
from nn_meter.builder.modules.tf_networks.blocks import ConvBnRelu, DwConvBnRelu, HswishBlock, SEBlock

def op_level_test_conv(predictor_name):
    # conv-bn-relu
    with open(predictor_name, "rb") as f:
        predictor = pickle.load(f)

    reals, preds = [], []
    configs = [
        # mobilenet v3
        [224, 3, 16, 3, 2], [56, 48, 24, 1, 1], [56, 24, 144, 1, 1], [56, 144, 24, 1, 1], [56, 24, 96, 1, 1], [56, 96, 24, 1, 1],
        [28, 144, 40, 1, 1], [28, 40, 240, 1, 1], [28, 240, 40, 1, 1], [28, 40, 160, 1, 1], [28, 160, 40, 1, 1], [28, 40, 120, 1, 1],
        [28, 120, 40, 1, 1], [14, 160, 80, 1, 1], [14, 80, 320, 1, 1], [14, 320, 80, 1, 1], [14, 80, 480, 1, 1], [14, 480, 112, 1, 1],
        [14, 112, 672, 1, 1], [14, 672, 112, 1, 1], [14, 112, 448, 1, 1], [7, 448, 160, 1, 1], [7, 160, 640, 1, 1], [7, 640, 160, 1, 1],
        [7, 160, 960, 1, 1], [1, 960, 1280, 1, 1], [28, 96, 40, 1, 1], [14, 480, 80, 1, 1], [14, 80, 240, 1, 1], [14, 240, 112, 1, 1],
        [14, 448, 112, 1, 1], [7, 160, 480, 1, 1], [7, 480, 160, 1, 1], [112, 16, 96, 1, 1], [56, 24, 72, 1, 1], [28, 72, 40, 1, 1], 
        [14, 240, 80, 1, 1], [7, 672, 160, 1, 1], [7, 960, 160, 1, 1], [112, 16, 64, 1, 1], [56, 64, 24, 1, 1], [56, 72, 24, 1, 1], 
        [14, 120, 80, 1, 1], [14, 320, 112, 1, 1], [14, 112, 336, 1, 1], [14, 336, 112, 1, 1], [7, 336, 160, 1, 1]
        # resnet
        
    ]
    # for i, config in enumerate(configs):
    # for i, cout in enumerate(range(600, 681)):
    # for i, ks in enumerate([1, 3, 5, 7]):
    for i, c in enumerate([16, 32, 48, 64, 96, 128, 160, 240, 320, 480, 560]):
        # hwin, cin, cout, k, strides = config
        
        # hwin, cin, cout, k, strides = 28, 640, cout, 3, 1
        
        # hwin, cin, cout, k, strides = 14, 320, 320, ks, 1
        # hwin, cin, cout, k, strides = 56, 32, 32, ks, 1
        # hwin, cin, cout, k, strides = 56, 96, 96, ks, 1
        
        hwin, cin, cout, k, strides = 56, c, c, 1, 1
        config_in = {
            "HW": hwin,
            "CIN": cin,
            "COUT": cout,
            "KERNEL_SIZE": k,
            "STRIDES": strides
        }
        input_shape = [hwin, hwin, cin]
        model = ConvBnRelu(config_in).get_model()
        real = profile_model(model, input_shape)
        pred = predictor.predict([get_feature("conv-bn-relu", config_in)])[0]
        reals.append(real)
        preds.append(pred)

    rmse, rmspe, error, acc10, acc15, acc20 = latency_metrics(preds, reals)
    # for item in zip(reals, preds):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_conv.txt", "a").write(f'{item}\n')
    
    # for cin, res in zip(range(600, 681), reals):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_conv.txt", "a").write(f"cin: {cin}; profiled results: {res}\n")
    
    # # for ks, res in zip([1, 3, 5, 7], reals):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_conv.txt", "a").write(f"ks: {ks}; profiled results: {res}\n")
    
    for c, res in zip([16, 32, 48, 64, 96, 128, 160, 240, 320, 480, 560], reals):
        open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_conv.txt", "a").write(f"{c}, {res}\n")
    
    # open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_conv.txt", "a").write(f"[Conv-bn-relu] rmse: {rmse}, rmspe: {rmspe}, error: {error}, acc10: {acc10}, acc15: {acc15}, acc20: {acc20}\n")
    

def op_level_test_dwconv(predictor_name):
    with open(predictor_name, "rb") as f:
        predictor = pickle.load(f)
    # dwconv-bn-relu
    reals, preds = [], []
    configs = [
        [112, 16, 3, 1], [112, 48, 3, 2], [56, 144, 3, 1], [56, 96, 5, 1], [56, 144, 5, 2], [28, 240, 3, 1], [28, 160, 7, 1],
        [28, 120, 3, 1], [28, 160, 3, 2], [14, 320, 5, 1], [14, 480, 3, 1], [14, 672, 3, 1], [14, 448, 3, 2], [7, 640, 7, 1],
        [7, 640, 3, 1], [7, 640, 5, 1], [56, 96, 7, 2], [28, 240, 7, 1], [28, 160, 5, 2], [14, 240, 5, 1], [14, 448, 7, 1],
        [14, 448, 7, 2], [7, 480, 5, 1], [112, 96, 3, 2], [56, 144, 5, 1], [56, 72, 3, 2], [28, 240, 5, 1], [28, 160, 5, 1],
        [28, 240, 7, 2], [14, 480, 7, 1], [14, 320, 7, 1], [7, 480, 7, 1], [28, 120, 7, 1], [14, 240, 7, 1], [14, 448, 5, 1],
        [14, 672, 3, 2], [7, 960, 5, 1], [7, 480, 3, 1], [112, 64, 3, 2], [56, 72, 5, 1], [56, 144, 7, 1], [56, 96, 3, 1],
        [56, 144, 3, 2], [28, 120, 5, 2], [14, 320, 3, 1], [14, 448, 3, 1], [14, 672, 7, 2], [7, 960, 3, 1], [56, 96, 7, 1],
        [56, 72, 7, 1], [56, 72, 7, 2], [28, 120, 5, 1], [28, 160, 7, 2], [14, 672, 5, 1], [14, 672, 5, 2], [7, 960, 7, 1],
        [28, 120, 7, 2], [14, 240, 3, 1], [14, 480, 5, 1], [14, 336, 5, 1], [112, 48, 5, 2], [28, 160, 3, 1], [14, 336, 7, 2],
        [56, 72, 3, 1], [56, 72, 5, 2], [28, 240, 3, 2], [14, 336, 7, 1], [56, 96, 3, 2], [56, 96, 5, 2], [14, 336, 5, 2],
        [56, 144, 7, 2], [112, 96, 5, 2], [14, 448, 5, 2], [14, 336, 3, 1], [112, 64, 5, 2], [28, 240, 5, 2], [14, 336, 3, 2],
        [28, 120, 3, 2], [112, 48, 7, 2], [14, 672, 7, 1], [112, 64, 7, 2], [112, 96, 7, 2]
    ]
    real_latency = [0.191779, 0.233146, 0.490663, 1.78205, 0.662423, 0.20149, 1.22768, 0.0999926, 0.0466496, 0.320491, 0.103281, 0.144607,
                    0.033186, 0.210078, 0.0448492, 0.138192, 0.817935, 1.81479, 0.177331, 0.240303, 0.751388, 0.190102, 0.103441, 0.521081,
                    2.61812, 0.0942064, 1.04044, 0.700529, 0.46252, 0.802633, 0.540999, 0.154736, 1.01768, 0.405505, 0.449454, 0.0509808,
                    0.210771, 0.0337018, 0.320399, 1.47491, 4.69039, 0.315632, 0.188117, 0.144596, 0.0687029, 0.095886, 0.289421, 0.0669981,
                    3.19388, 2.6905, 0.660968, 0.574518, 0.311419, 0.679042, 0.174614, 0.316426, 0.251711, 0.0511541, 0.479948, 0.336547, 0.990568,
                    0.13269, 0.143569, 0.23922, 0.37097, 0.0702065, 0.56316, 0.116958, 0.460959, 0.0861975, 1.18116, 1.90973, 0.114181, 0.072314,
                    1.25432, 0.264163, 0.0251118, 0.0358999, 1.79139, 1.13197, 2.25581, 3.38345]
    assert len(configs) == len(real_latency)

    for i, config in enumerate(configs):
    # for i, cin in enumerate(range(600, 681)):
    # for i, ks in enumerate([1, 3, 5, 7]):
        hwin, cin, k, strides = config
        # hwin, cin, k, strides = 28, cin, 3, 1
        # hwin, cin, k, strides = 14, 320, ks, 1
        # hwin, cin, k, strides = 56, 32, ks, 1
        # hwin, cin, k, strides = 56, 96, ks, 1
        config_in = {
            "HW": hwin,
            "CIN": cin,
            "COUT": cin,
            "KERNEL_SIZE": k,
            "STRIDES": strides
        }
        input_shape = [hwin, hwin, cin]
        model = DwConvBnRelu(config_in).get_model()
        real = profile_model(model, input_shape)
        # real = real_latency[i]
        pred = predictor.predict([get_feature("dwconv-bn-relu", config_in)])[0]
        reals.append(real)
        preds.append(pred)
        open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_dwconv.txt", "a").write(f"{real}, {pred}\n")
            
    rmse, rmspe, error, acc10, acc15, acc20 = latency_metrics(preds, reals)
    # for cin, res in zip(range(600, 681), reals):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_dwconv.txt", "a").write(f"cin: {cin}; profiled results: {res}\n")
    # for item in zip(reals, preds):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_dwconv.txt", "a").write(f'{item}\n')
    # for ks, res in zip([1, 3, 5, 7], reals):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_dwconv.txt", "a").write(f"ks: {ks}; profiled results: {res}\n")
    open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_dwconv.txt", "a").write(f"[Dwconv-bn-relu] rmse: {rmse}, rmspe: {rmspe}, error: {error}, acc10: {acc10}, acc15: {acc15}, acc20: {acc20}\n")


def op_level_test_hswish(predictor_name):
    with open(predictor_name, "rb") as f:
        predictor = pickle.load(f)
    from nn_meter.builder.nn_generator.tf_networks.blocks import HswishBlock
    reals, preds = [], []
    configs = [
        [112, 16], [28, 120], [14, 120], [14, 480], [14, 480], [14, 240], [14, 320],
        [14, 672], [14, 672], [14, 448], [14, 448], [14, 336], [14, 336], [14, 672],
        [7, 672], [7, 640], [7, 640], [7, 480], [7, 480], [7, 960], [1, 1280]
    ]
    # real_latency = [0.128782, 0.0591809, 0.015116300000000001, 0.0602787, 0.0594359, 0.030281600000000002,
    #                 0.0294835, 0.0393665, 0.0397524, 0.0826915, 0.0845971, 0.0551774, 0.0550148, 0.0414161,
    #                 0.0412727, 0.08282500000000001, 0.0209465, 0.019829, 0.019747499999999998, 0.014869199999999999,
    #                 0.014901999999999999, 0.0295921, 0.000959823]
    # assert len(configs) == len(real_latency)

    for i, config in enumerate(configs):
    # for i, cin in enumerate(range(600, 681)):
        hwin, cin = config
        # hwin, cin = 14, cin
        config_in = {
            "HW": hwin,
            "CIN": cin
        }
        input_shape = [hwin, hwin, cin]
        model = HswishBlock(config_in).get_model()
        real = profile_model(model, input_shape)
        # real = real_latency[i]
        pred = predictor.predict([get_feature("hswish", config_in)])[0]
        open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_hswish.txt", "a").write(f'{hwin}, {cin}, {real}, {pred}\n')
        reals.append(real)
        preds.append(pred)
            
    rmse, rmspe, error, acc10, acc15, acc20 = latency_metrics(preds, reals)
    # for cin, res in zip(range(600, 681), reals):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_hswish.txt", "a").write(f"cin: {cin}; profiled results: {res}\n")
    # for item in zip(reals, preds):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_hswish.txt", "a").write(f'{item}\n')
    open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_hswish.txt", "a").write(f"[Hswish] rmse: {rmse}, rmspe: {rmspe}, error: {error}, acc10: {acc10}, acc15: {acc15}, acc20: {acc20}\n")

def test_profile_hswish():
    hwin, cin = 96, 1984
    config_in = {
        "HW": hwin,
        "CIN": cin
    }
    input_shape = [hwin, hwin, cin]
    model = HswishBlock(config_in).get_model()
    model(get_inputs_by_shapes([[*input_shape]]))
    tf.keras.models.save_model(model, output_name)

    res = backend.profile_model_file(output_name, output_path, input_shape=[[*input_shape]])
    print(res["latency"].avg)
 

def op_level_test_se(predictor_name):
    with open(predictor_name, "rb") as f:
        predictor = pickle.load(f)

    reals, preds = [], []
    configs = [
        [28, 72], [28, 160], [14, 320], [14, 672], [14, 448], [14, 336], 
        [7, 672], [7, 640], [7, 480], [112, 16], [28, 120], [14, 120], [14, 480], [14, 480], [14, 240], [14, 240], [14, 320],
        [14, 320], [14, 672], [14, 672], [14, 448], [14, 448], [14, 336], [14, 336], [14, 672],
        [7, 672], [7, 640], [7, 640], [7, 480], [7, 480], [7, 960]
    ]
    # real_latency = [0.105464, 0.142179, 0.083235, 0.186923, 0.119378, 0.0866421, 0.0801339, 0.0744534, 0.051884900000000005,
    #                 0.276539, 0.151357, 0.039004800000000006, 0.127612, 0.127489, 0.061883400000000005, 0.0606852, 0.0819179,
    #                 0.0816348, 0.18641999999999997, 0.18621100000000002, 0.118002, 0.117377, 0.08627889999999999, 0.0866098,
    #                 0.186018, 0.0807595, 0.0745344, 0.074871, 0.051839199999999995, 0.0515206, 0.13823
    # ]
    # assert len(configs) == len(real_latency)
    # for i, config in enumerate(configs):
    for cin in range(600, 681):
        # hwin, cin = config
        hwin, cin = 14, cin
        config_in = {
            "HW": hwin,
            "CIN": cin
        }
        input_shape = [hwin, hwin, cin]
        # model = SE_xudong(cin)
        model = SEBlock(config_in).get_model()
        real = profile_model(model, input_shape)
        # real = real_latency[i]
        pred = predictor.predict([get_feature("se", config_in)])[0]
        reals.append(real)
        preds.append(pred)
        open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_se.txt", "a").write(f"{cin}, {real}\n")

    rmse, rmspe, error, acc10, acc15, acc20 = latency_metrics(preds, reals)
    # for cin, res in zip(range(600, 681), reals):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_se.txt", "a").write(f"cin: {cin}; profiled results: {res}\n")
    # for item in zip(reals, preds):
    #     open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_se.txt", "a").write(f'{item}\n')
    open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_se.txt", "a").write(f"[SE] rmse: {rmse}, rmspe: {rmspe}, error: {error}, acc10: {acc10}, acc15: {acc15}, acc20: {acc20}\n")


def op_level_test_mobilenetv3_large():
    from tf_keras_mobilenetv3 import MobileNetV3Large
    
    # from tensorflow.keras.applications import MobileNetV3Large
    model = MobileNetV3Large(input_shape=(224, 224, 3), weights=None)
    input_shape = [224, 224, 3]
    real = profile_model(model, input_shape)
    print(real)
    open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_mobilenetv3large.txt", "a").write(f"{real}\n")

    # model = tf.keras.applications.MobilenetV3Large()
    

def op_level_test_cascade_mbv1():
    from op_code_tf import res_block, seq_block
    i = 3
    configs = [
        # 112x112x16->56x56x32
        ['112x112x16->56x56x32', 'sequential', 'ks{i}', [112, 16, 32, i, 1, 32, 32, i, 2]],
        ['112x112x16->56x56x32', 'sequential', 'ks{i}', [112, 16, 16, i, 1, 16, 32, i, 2]],
        ['112x112x16->56x56x32', 'sequential', 'ks{i}', [112, 16, 32, i, 2, 32, 32, i, 1]],
        ['112x112x16->56x56x32', 'sequential', 'ks{i}', [112, 16, 16, i, 2, 16, 32, i, 1]],

        # 56x56x32->56x56x32
        ['56x56x32->56x56x32', 'res_connected', 'ks{i}', [56, 32, 32, i, 1]],
        ['56x56x32->56x56x32', 'sequential', 'ks{i}', [56, 32, 32, i, 1, 32, 32, i, 1]],
        
        # 56x56x32->28x28x64
        ['56x56x32->28x28x64', 'sequential', 'ks{i}', [56, 32, 64, i, 1, 64, 64, i, 2]],
        ['56x56x32->28x28x64', 'sequential', 'ks{i}', [56, 32, 32, i, 1, 32, 64, i, 2]],
        ['56x56x32->28x28x64', 'sequential', 'ks{i}', [56, 32, 64, i, 2, 64, 64, i, 1]],
        ['56x56x32->28x28x64', 'sequential', 'ks{i}', [56, 32, 32, i, 2, 32, 64, i, 1]],

        # 28x28x64->28x28x64
        ['28x28x64->28x28x64', 'res_connected', 'ks{i}', [28, 64, 64, i, 1]],
        ['28x28x64->28x28x64', 'sequential', 'ks{i}', [28, 64, 64, i, 1, 64, 64, i, 1]],
        
        # 28x28x64->14x14x128
        ['28x28x64->14x14x128', 'sequential', 'ks{i}', [28, 64, 64, i, 1, 64, 128, i, 2]],
        ['28x28x64->14x14x128', 'sequential', 'ks{i}', [28, 64, 128, i, 1, 128, 128, i, 2]],
        ['28x28x64->14x14x128', 'sequential', 'ks{i}', [28, 64, 64, i, 2, 64, 128, i, 1]],
        ['28x28x64->14x14x128', 'sequential', 'ks{i}', [28, 64, 128, i, 2, 128, 128, i, 1]],

        # 14x14x128->14x14x128
        ['14x14x128->14x14x128', 'res_connected', 'ks{i}', [14, 128, 128, i, 1]],
        ['14x14x128->14x14x128', 'sequential', 'ks{i}', [14, 128, 128, i, 1, 128, 128, i, 1]],
        
        # 14x14x128->7x7x256
        ['14x14x128->7x7x256', 'sequential', 'ks{i}', [14, 128, 128, i, 1, 128, 256, i, 2]],
        ['14x14x128->7x7x256', 'sequential', 'ks{i}', [14, 128, 256, i, 1, 256, 256, i, 2]],
        ['14x14x128->7x7x256', 'sequential', 'ks{i}', [14, 128, 128, i, 2, 128, 256, i, 1]],
        ['14x14x128->7x7x256', 'sequential', 'ks{i}', [14, 128, 256, i, 2, 256, 256, i, 1]],

        # 7x7x256->7x7x256
        ['7x7x256->7x7x256', 'res_connected', 'ks{i}', [7, 256, 256, i, 1]],
        ['7x7x256->7x7x256', 'sequential', 'ks{i}', [7, 256, 256, i, 1, 256, 256, i, 1]],
        
    ]    
    
    for i, config in enumerate(configs):
        name, block, ks, param = config
        if block == 'res_connected':
            for ks_v in [3, 5]:
                hwin, cin, cout, ks, s = param
                input_shape = [hwin, hwin, cin]
                model = res_block(hwin, cin, cout, ks_v, s)
                real = profile_model(model, input_shape)
                open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_mbv1.txt", "a").write(f'{backend_name}, {name}, {block}, ks{ks_v}, cin_{cin}_cout_{cout}, {real}\n')
        else:
            for ks_v in [3, 5]:
                hwin, cin1, cout1, ks1, s1, cin2, cout2, ks2, s2 = param
                
                input_shape = [hwin, hwin, cin1]
                model = seq_block(hwin, cin1, cout1, ks_v, s1, cin2, cout2, ks_v, s2)
                real = profile_model(model, input_shape)
                open("/data/jiahang/working/nn-Meter/examples/test_quantize_latency_predictor/op_result_mbv1.txt", "a").write(f'{backend_name}, {name}, {block}, ks{ks_v}, cin1_{cin1}_cout1_{cout1}_s1_{s1}_cin2_{cin2}_cout2_{cout2}_s2_{s2}, {real}\n')
        # break
    
    
if __name__ == '__main__':
    
    # op_level_test_conv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/conv-bn-relu_original.pkl")
    # op_level_test_conv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/conv-bn-relu_ofa.pkl")
    # op_level_test_conv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/conv-bn-relu_ofa_only.pkl")
    # op_level_test_conv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/conv-bn-relu_ofa_filt8.pkl")
    
    # op_level_test_dwconv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/dwconv-bn-relu_original.pkl")
    # op_level_test_dwconv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/dwconv-bn-relu_ofa.pkl")
    # op_level_test_dwconv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/dwconv-bn-relu_ofa_only.pkl")
    # op_level_test_dwconv("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/dwconv-bn-relu_ofa_filt8.pkl")
    # op_level_test_dwconv('/data1/jiahang/working/pixel4_mobilenetv3_workspace/predictor/dwconv-bn-relu.pkl')
    
    # op_level_test_hswish("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/hswish_fg1_filt8.pkl")
    # test_profile_hswish()
    
    op_level_test_se("/data1/jiahang/working/pixel4_int8_workspace/predictor_build/results/predictors/se_ofa_filt8.pkl")
    
    # op_level_test_mobilenetv3_large()
    
    # op_level_test_cascade_mbv1()