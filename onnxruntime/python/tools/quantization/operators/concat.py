import onnx

from ..quant_utils import QuantizedValue, QuantizedValueType, attribute_to_kwarg, ms_domain
from .base_operator import QOperatorBase
from .qdq_base_operator import QDQOperatorBase


class QLinearConcat(QOperatorBase):
    def __init__(self, onnx_quantizer, onnx_node):
        super().__init__(onnx_quantizer, onnx_node)

    def do_quantization(self):
        node = self.node

        (
            data_found,
            output_scale_name,
            output_zp_name,
            _,
            _,
        ) = self.quantizer._get_quantization_params(node.output[0])
        (
            q_input_names,
            zero_point_names,
            scale_names,
            nodes,
        ) = self.quantizer.quantize_inputs(node, [*range(0, len(node.input))], initializer_use_weight_qType=False)
        if not data_found or q_input_names is None:
            return super().do_quantization()

        # Create an entry for output quantized value
        quantized_input_value = self.quantizer.quantized_value_map[node.input[0]]
        quantized_output_value = QuantizedValue(
            node.output[0],
            node.output[0] + "_quantized",
            output_scale_name,
            output_zp_name,
            quantized_input_value.value_type,
        )
        self.quantizer.quantized_value_map[node.output[0]] = quantized_output_value

        kwargs = {}
        for attribute in node.attribute:
            kwargs.update(attribute_to_kwarg(attribute))
        kwargs["domain"] = ms_domain
        qnode_name = node.name + "_quant" if node.name != "" else ""

        qlconcat_inputs = [output_scale_name, output_zp_name]
        for i in range(0, len(q_input_names)):
            qlconcat_inputs.extend([q_input_names[i], scale_names[i], zero_point_names[i]])
        qlconcat_node = onnx.helper.make_node(
            "QLinearConcat", qlconcat_inputs, [quantized_output_value.q_name], qnode_name, **kwargs
        )

        self.quantizer.new_nodes += nodes
        self.quantizer.new_nodes += [qlconcat_node]


class QDQConcat(QDQOperatorBase):
    def __init__(self, onnx_quantizer, onnx_node):
        super().__init__(onnx_quantizer, onnx_node)

    def do_quantization(self):
        super().do_quantization()
        self.quantizer.quantize_tensor(self.node.output[0])
