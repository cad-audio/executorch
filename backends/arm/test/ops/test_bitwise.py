# Copyright 2025 Arm Limited and/or its affiliates.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.


from typing import Tuple

import torch
from executorch.backends.arm.test import common
from executorch.backends.arm.test.tester.test_pipeline import (
    EthosU85PipelineBI,
    OpNotSupportedPipeline,
    TosaPipelineBI,
    TosaPipelineMI,
)


input_t2 = Tuple[torch.Tensor, torch.Tensor]  # Input x, y


class BitwiseBinary(torch.nn.Module):
    test_data: dict[input_t2] = {
        "zeros": lambda: (
            torch.zeros(1, 10, 10, 10, dtype=torch.int32),
            torch.zeros(1, 10, 10, 10, dtype=torch.int32),
        ),
        "ones": lambda: (
            torch.ones(10, 10, 10, dtype=torch.int8),
            torch.ones(10, 10, 10, dtype=torch.int8),
        ),
        "pattern_int8": lambda: (
            0xAA * torch.ones(1, 2, 2, 2, dtype=torch.int8),
            0xCC * torch.ones(1, 2, 2, 2, dtype=torch.int8),
        ),
        "pattern_int16": lambda: (
            0xAAAA * torch.ones(1, 2, 2, 2, dtype=torch.int16),
            0xCCCC * torch.ones(1, 2, 2, 2, dtype=torch.int16),
        ),
        "pattern_int32": lambda: (
            0xAAAAAAAA * torch.ones(1, 2, 2, 2, dtype=torch.int32),
            0xCCCCCCCC * torch.ones(1, 2, 2, 2, dtype=torch.int32),
        ),
        "pattern_bool": lambda: (
            torch.tensor([True, False, True], dtype=torch.bool),
            torch.tensor([True, True, False], dtype=torch.bool),
        ),
        "rand_rank2": lambda: (
            torch.randint(-128, 127, (10, 10), dtype=torch.int8),
            torch.randint(-128, 127, (10, 10), dtype=torch.int8),
        ),
        "rand_rank4": lambda: (
            torch.randint(-128, -127, (1, 10, 10, 10), dtype=torch.int8),
            torch.randint(-128, 127, (1, 10, 10, 10), dtype=torch.int8),
        ),
    }


class And(BitwiseBinary):
    aten_op = "torch.ops.aten.bitwise_and.Tensor"
    exir_op = "executorch_exir_dialects_edge__ops_aten_bitwise_and_Tensor"

    def forward(self, tensor1: torch.Tensor, tensor2: torch.Tensor):
        return tensor1.bitwise_and(tensor2)


class Xor(BitwiseBinary):
    aten_op = "torch.ops.aten.bitwise_xor.Tensor"
    exir_op = "executorch_exir_dialects_edge__ops_aten_bitwise_xor_Tensor"

    def forward(self, tensor1: torch.Tensor, tensor2: torch.Tensor):
        return tensor1.bitwise_xor(tensor2)


class Or(BitwiseBinary):
    aten_op = "torch.ops.aten.bitwise_or.Tensor"
    exir_op = "executorch_exir_dialects_edge__ops_aten_bitwise_or_Tensor"

    def forward(self, tensor1: torch.Tensor, tensor2: torch.Tensor):
        return tensor1.bitwise_or(tensor2)


@common.parametrize("test_data", And().test_data)
def test_bitwise_and_tensor_tosa_MI(test_data: input_t2):
    pipeline = TosaPipelineMI[input_t2](
        And(),
        test_data(),
        And().aten_op,
        And().exir_op,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.run()


@common.parametrize("test_data", And().test_data)
def test_bitwise_and_tensor_tosa_BI(test_data: input_t2):
    pipeline = TosaPipelineBI[input_t2](
        And(),
        test_data(),
        And().aten_op,
        And().exir_op,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.pop_stage("quantize")
    pipeline.pop_stage("check.quant_nodes")
    pipeline.run()


@common.parametrize("test_data", And().test_data)
def test_bitwise_and_tensor_u55_BI(test_data: input_t2):
    # Tests that we don't delegate these ops since they are not supported on U55.
    pipeline = OpNotSupportedPipeline[input_t2](
        And(),
        test_data(),
        {And().exir_op: 1},
        quantize=True,
        u55_subset=True,
    )
    pipeline.run()


@common.parametrize("test_data", And().test_data)
@common.XfailIfNoCorstone320
def test_bitwise_and_tensor_u85_BI(test_data: input_t2):
    pipeline = EthosU85PipelineBI[input_t2](
        And(),
        test_data(),
        And().aten_op,
        And().exir_op,
        run_on_fvp=True,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.pop_stage("quantize")
    pipeline.pop_stage("check.quant_nodes")
    pipeline.run()


@common.parametrize("test_data", Xor().test_data)
def test_bitwise_xor_tensor_tosa_MI(test_data: input_t2):
    pipeline = TosaPipelineMI[input_t2](
        Xor(),
        test_data(),
        Xor().aten_op,
        Xor().exir_op,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.run()


@common.parametrize("test_data", Xor().test_data)
def test_bitwise_xor_tensor_tosa_BI(test_data: input_t2):
    pipeline = TosaPipelineBI[input_t2](
        Xor(),
        test_data(),
        Xor().aten_op,
        Xor().exir_op,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.pop_stage("quantize")
    pipeline.pop_stage("check.quant_nodes")
    pipeline.run()


@common.parametrize("test_data", Xor().test_data)
def test_bitwise_xor_tensor_u55_BI(test_data: input_t2):
    # Tests that we don't delegate these ops since they are not supported on U55.
    pipeline = OpNotSupportedPipeline[input_t2](
        Xor(),
        test_data(),
        {Xor().exir_op: 1},
        quantize=True,
        u55_subset=True,
    )
    pipeline.run()


@common.parametrize("test_data", Xor().test_data)
@common.XfailIfNoCorstone320
def test_bitwise_xor_tensor_u85_BI(test_data: input_t2):
    pipeline = EthosU85PipelineBI[input_t2](
        Xor(),
        test_data(),
        Xor().aten_op,
        Xor().exir_op,
        run_on_fvp=True,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.pop_stage("quantize")
    pipeline.pop_stage("check.quant_nodes")
    pipeline.run()


@common.parametrize("test_data", Or().test_data)
def test_bitwise_or_tensor_tosa_MI(test_data: input_t2):
    pipeline = TosaPipelineMI[input_t2](
        Or(),
        test_data(),
        Or().aten_op,
        Or().exir_op,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.run()


@common.parametrize("test_data", Or().test_data)
def test_bitwise_or_tensor_tosa_BI(test_data: input_t2):
    pipeline = TosaPipelineBI[input_t2](
        Or(),
        test_data(),
        Or().aten_op,
        Or().exir_op,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.pop_stage("quantize")
    pipeline.pop_stage("check.quant_nodes")
    pipeline.run()


@common.parametrize("test_data", Or().test_data)
def test_bitwise_or_tensor_u55_BI(test_data: input_t2):
    # Tests that we don't delegate these ops since they are not supported on U55.
    pipeline = OpNotSupportedPipeline[input_t2](
        Or(),
        test_data(),
        {Or().exir_op: 1},
        quantize=True,
        u55_subset=True,
    )
    pipeline.run()


@common.parametrize("test_data", Or().test_data)
@common.XfailIfNoCorstone320
def test_bitwise_or_tensor_u85_BI(test_data: input_t2):
    pipeline = EthosU85PipelineBI[input_t2](
        Or(),
        test_data(),
        Or().aten_op,
        Or().exir_op,
        run_on_fvp=True,
        atol=0,
        rtol=0,
        qtol=0,
    )
    pipeline.pop_stage("quantize")
    pipeline.pop_stage("check.quant_nodes")
    pipeline.run()
