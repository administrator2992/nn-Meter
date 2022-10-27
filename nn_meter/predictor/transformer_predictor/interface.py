# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import os, json

class BlockLatencyPredictor:
    def __init__(self, predictor_name = "pixel6_lut", layer_norm = True):
        self.predictor_name = predictor_name
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, "lut", f"{predictor_name}_ln_v2.json"), 'r') as fp:
            self.predictor = json.load(fp)
        self.layer_norm = layer_norm

    def get_latency(self, block_config):
        '''
        arch = (
            224, # 0 input res
            (16, 24, 40, 64, 112, 192, 320), # 1 channels
            (1, 3, 4, 2, 3, 4, 5), # 2 depths
            (1, 5, 5, 5, 6, 6, 6, 6), # 3 conv expansion ratio
            (3, 5, 5, 5, 5, 5, 5, 5), # 4 conv kr size
            (4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3), # 5 trans mlp ratio
            (4, 4, 7, 7, 7, 12, 12, 12, 12, 20, 20, 20, 20, 20), # 6 trans num heads
            (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), # 7 windows size
            (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), # 8 qk scale
            (2, 2, 2, 2, 2, 2, 2, 2, 2, 4, 4, 4, 4, 4) # 9 v scale
        )
        '''
        py = 0
        act = "hard_swish"
        strides = (1, 2, 2, 2, 2, 1, 2) # didn't contain the first conv3x3
        use_se = (False, False, True)

        # first_block
        hw = block_config[0]
        py += self.predictor[f"firstconv_{hw}_3_{block_config[1][0]}_2_3"]
        print(f"firstconv_{hw}_3_{block_config[1][0]}_2_3")
        hw = hw // 2
        stage_cout = 16

        # layer_choice blocks
        conv_count, trans_count = 0, 0
        for stage_idx, channel in enumerate(block_config[1]):
            name = "conv" if stage_idx <= 2 else "transformer"
            stage_stride = strides[stage_idx]
            stage_hwin = hw
            # stage_hwout = hw // stage_stride if hw % stage_stride == 0 else hw // stage_stride + 1
            stage_hwout = hw // stage_stride
            hw = stage_hwout
            stage_cin = stage_cout
            stage_cout = channel
            if name == "conv":
                for i in range(block_config[2][stage_idx]):
                    s = stage_stride if i == 0 else 1
                    layer_hw = stage_hwin if i == 0 else stage_hwout
                    cin = stage_cin if i == 0 else stage_cout
                    cout = stage_cout
                    exp = block_config[3][conv_count]
                    ks = block_config[4][conv_count]
                    se = use_se[stage_idx]
                    conv_count += 1

                    # predict by lut
                    py += self.predictor[f"{name}_{layer_hw}_{cin}_{cout}_{exp}_{s}_{act}_{ks}_{'se' if se else 'nose'}"]
                    print(f"{name}_{layer_hw}_{cin}_{cout}_{exp}_{s}_{act}_{ks}_{'se' if se else 'nose'}")

            elif name == "transformer":
                for i in range(block_config[2][stage_idx]):
                    s = stage_stride if i == 0 else 1
                    ds = "ds" if i == 0 else "nods"
                    layer_hw = stage_hwin if i == 0 else stage_hwout
                    cin = stage_cin if i == 0 else stage_cout
                    cout = stage_cout
                    exp = block_config[5][trans_count]
                    v = block_config[9][trans_count]
                    trans_count += 1

                    # predict by lut
                    if i == 0:
                        py += self.predictor[f"{name}_{layer_hw}_{cin}_{cout}_{exp}_{s}_{act}_{v}_{ds}_6_{'ln' if self.layer_norm else 'bn'}"]
                        print(f"{name}_{layer_hw}_{cin}_{cout}_{exp}_{s}_{act}_{v}_{ds}_6_{'ln' if self.layer_norm else 'bn'}")
                    else:
                        py += self.predictor[f"{name}_{layer_hw}_{cin}_{cout}_{exp}_{s}_{act}_{v}_{ds}_{'ln' if self.layer_norm else 'bn'}"]
                        print(f"{name}_{layer_hw}_{cin}_{cout}_{exp}_{s}_{act}_{v}_{ds}_{'ln' if self.layer_norm else 'bn'}")
        # MBPool block
        py += self.predictor[f"mbpool_{layer_hw}_{block_config[1][-1]}_1984_6_{act}"]
        print(f"mbpool_{layer_hw}_{block_config[1][-1]}_1984_6_{act}")

        assert conv_count == len(block_config[4])
        assert trans_count == len(block_config[5])

        return py


    def get_single_block_arch(self, name, hw, cin, cout, kernel_size, expand_ratio, 
                    stride, activation):
        raise NotImplementedError # does not support latency predictor now
        block_type = self.get_type(name, cin, cout, stride, activation)
        dicts = get_block_arch_by_name(block_type, hw, cin, cout, kernel_size, expand_ratio, stride)
        return dicts


    def get_latency_by_predictor(self, block_list):
        raise NotImplementedError # does not support latency predictor now
        from nn_meter.predictor.prediction.utils import get_kernel_name

        # merge dicts
        ops_config = {k: [] for k in self.ops}
        for args in block_list:
            single_block = self.get_single_block_arch(**args)
            for k, v in single_block.items():
                ops_config[k].extend(v)

        py = 0
        for kernel in ops_config:
            if ops_config[kernel] == []:
                continue
            kernelname = get_kernel_name(kernel)
            if kernelname in self.predictor.kernel_predictors:
                pred = self.predictor.kernel_predictors[kernelname]
                pys = pred.predict(ops_config[kernel]) # in unit of ms
                if len(pys) != 0:
                    py += sum(pys)
        return py