# Copyright (c) Qualcomm Innovation Center, Inc.
# All rights reserved
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict

import executorch.backends.qualcomm.python.PyQnnWrapperAdaptor as PyQnnWrapper

import numpy as np
import torch
from executorch.backends.qualcomm.utils.constants import QCOM_DATA

from .node_visitor import NodeVisitor
from .node_visitor_manager import register_node_visitor
from .qnn_constants import OpDepthToSpace, QNN_OP_PACKAGE_NAME_QTI_AISW


@register_node_visitor
class DepthToSpaceVisitor(NodeVisitor):
    target = ["aten.pixel_shuffle.default"]

    def __init__(self, *args) -> None:
        super().__init__(*args)

    def define_node(
        self,
        node: torch.fx.Node,
        nodes_to_wrappers: Dict[torch.fx.Node, PyQnnWrapper.TensorWrapper],
    ) -> PyQnnWrapper.PyQnnOpWrapper:
        input_node = self.get_node(node.args[0])
        input_tensor = self.get_tensor(input_node, node)
        input_tensor_wrapper = self.define_tensor(
            input_node,
            node,
            input_tensor,
            PyQnnWrapper.Qnn_TensorType_t.QNN_TENSOR_TYPE_NATIVE,
            nodes_to_wrappers,
        )

        output_tensor = self.get_tensor(node, node)
        output_tensor_wrapper = self.define_tensor(
            node,
            node,
            output_tensor,
            PyQnnWrapper.Qnn_TensorType_t.QNN_TENSOR_TYPE_NATIVE,
            nodes_to_wrappers,
        )

        block_size = []
        for index in range(1, 3):
            block_size.append(output_tensor.shape[index] / input_tensor.shape[index])
        block_size = np.array(block_size, dtype=np.uint32)
        block_size_shape = [2]

        depth_to_space_op = PyQnnWrapper.PyQnnOpWrapper(
            node.name,
            QNN_OP_PACKAGE_NAME_QTI_AISW,
            OpDepthToSpace.op_name,
        )
        depth_to_space_op.AddInputTensors([input_tensor_wrapper])
        depth_to_space_op.AddOutputTensors([output_tensor_wrapper])
        depth_to_space_op.AddTensorParam(
            OpDepthToSpace.param_block_size,
            PyQnnWrapper.Qnn_DataType_t.QNN_DATATYPE_UINT_32,
            len(block_size.shape),
            block_size_shape,
            block_size,
            True,
        )
        depth_to_space_op.AddScalarParam(
            OpDepthToSpace.param_mode,
            PyQnnWrapper.Qnn_DataType_t.QNN_DATATYPE_UINT_32,
            {QCOM_DATA: np.uint32(OpDepthToSpace.Mode.CRD)},
        )

        return depth_to_space_op
