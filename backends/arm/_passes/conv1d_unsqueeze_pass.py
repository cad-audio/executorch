# Copyright (c) Meta Platforms, Inc. and affiliates.
# Copyright 2024 Arm Limited and/or its affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# pyre-unsafe


import torch
from executorch.backends.arm._passes.arm_pass_utils import (
    create_node,
    get_param_tensor,
    is_param_node,
)
from executorch.exir import ExportedProgram
from executorch.exir.dialects._ops import ops as exir_ops
from executorch.exir.pass_base import ExportPass, PassResult


class Conv1dUnsqueezePass(ExportPass):
    """
    This pass is used to change conv1d ops into conv2d since TOSA only
    supports 2d and 3d convolution. This is done by modifying the graph to do the
    following:
    1) unsqueeze the convolution's input from 3d to 4d
    2) perform a conv2d (with a modified version of the original conv1d args)
    3) squeeze the output back down to 3d.
    """

    def __init__(self, exported_program: ExportedProgram) -> None:
        super().__init__()
        self.exported_program = exported_program

    def unsqueeze_kernel_weights(self, kernel_node):
        """
        Unsqueezes the weights of a conv1d to make it 4 dimensional.

        Args:
            kernel_node: the weights of conv1d node to be unsqueezed
        """
        kernel_param_3d = get_param_tensor(self.exported_program, kernel_node)
        if kernel_param_3d is None:
            raise AssertionError("Expected param tensor for the kernel node")

        kernel_param_4d = torch.nn.Parameter(
            data=kernel_param_3d.data.contiguous().unsqueeze(dim=-1),
            requires_grad=False,
        )

        if torch._export.utils.is_param(self.exported_program, kernel_node):
            parameter_name = self.exported_program.graph_signature.inputs_to_parameters[
                kernel_node.name
            ]
            self.exported_program.state_dict[parameter_name] = kernel_param_4d
            kernel_node.meta["val"] = kernel_node.meta["val"].data.unsqueeze(dim=-1)
        elif torch._export.utils.is_buffer(self.exported_program, kernel_node):
            buffer_name = self.exported_program.graph_signature.inputs_to_buffers[
                kernel_node.name
            ]
            self.exported_program.state_dict[buffer_name] = kernel_param_4d
            kernel_node.meta["val"] = kernel_node.meta["val"].data.unsqueeze(dim=-1)
        elif torch._export.utils.is_lifted_tensor_constant(
            self.exported_program, kernel_node
        ):
            buffer_name = (
                self.exported_program.graph_signature.inputs_to_lifted_tensor_constants[
                    kernel_node.name
                ]
            )
            self.exported_program.constants[buffer_name] = kernel_param_4d
            kernel_node.meta["val"] = kernel_node.meta["val"].data.unsqueeze(dim=-1)
        else:
            setattr(
                kernel_node.graph.owning_module,
                kernel_node.target,
                kernel_param_4d,
            )

    def call(self, graph_module: torch.fx.GraphModule):
        graph = graph_module.graph
        node_list = list(graph.nodes)
        for node in node_list:
            if node.op == "call_function":
                if node.target == exir_ops.edge.aten.convolution.default:
                    stride = list(node.args[3])
                    if len(stride) != 1:
                        # skip conv if it is not 1d
                        continue

                    kernel_node = node.args[1]

                    if not is_param_node(self.exported_program, kernel_node):
                        raise AssertionError(
                            "Expected op for convolution weight node to be a get_attr node or a parameter"
                        )

                    # Modify graph such that the conv changes from 1d to 2d
                    self.unsqueeze_kernel_weights(kernel_node)

                    # (b) Extend stride, padding, and dilation for extra dim
                    node.args = (
                        node.args[0],
                        node.args[1],
                        node.args[2],
                        node.args[3] + [1],  # stride
                        node.args[4] + [0],  # padding
                        node.args[5] + [1],  # dilation
                        node.args[6],
                        node.args[7] + [0],
                        node.args[8],
                    )

                    # c. Add unsqueeze to input (3d -> 4d) and squeeze to output (4d -> 3d)
                    # unsqueeze -> conv2d -> squeeze
                    with graph.inserting_before(node):
                        input_node = node.args[0]
                        unsqueeze_before = create_node(
                            graph, exir_ops.edge.aten.unsqueeze_copy.default
                        )
                        unsqueeze_before.args = (
                            input_node,  # Input is node's original input
                            -1,  # Last Dimension
                        )
                        node.replace_input_with(input_node, unsqueeze_before)

                    with graph.inserting_after(node):
                        squeeze_after = create_node(
                            graph,
                            exir_ops.edge.aten.squeeze_copy.dims,
                        )
                        squeeze_after.args = (
                            node,  # Input is the conv node
                            [-1],  # Last dimension
                        )
                        original_users = [
                            user for user in node.users if user != squeeze_after
                        ]
                        for user in original_users:
                            user.replace_input_with(node, squeeze_after)

        graph_module.recompile()
        # Since we are overriding "call", we need to call the parent's "call"
        # to retrace the graph and regenerate metadata
        graph_module = super().call(graph_module).graph_module

        return PassResult(graph_module, True)
