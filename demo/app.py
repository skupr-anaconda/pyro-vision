# Copyright (C) 2022, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import argparse
import json

import gradio as gr
import numpy as np
import onnxruntime
from huggingface_hub import hf_hub_download
from PIL import Image


def main(args):

    # Download model config & checkpoint
    with open(hf_hub_download(args.repo, filename="config.json"), "rb") as f:
        cfg = json.load(f)

    ort_session = onnxruntime.InferenceSession(hf_hub_download(args.repo, filename="model.onnx"))

    def preprocess_image(pil_img: Image.Image) -> np.ndarray:
        """Preprocess an image for inference

        Args:
            pil_img: a valid pillow image

        Returns:
            the resized and normalized image of shape (1, C, H, W)
        """

        # Resizing
        img = pil_img.resize(cfg["input_shape"][-2:], Image.BILINEAR)
        # (H, W, C) --> (C, H, W)
        img = np.asarray(img).transpose((2, 0, 1)).astype(np.float32) / 255
        # Normalization
        img -= np.array(cfg["mean"])[:, None, None]
        img /= np.array(cfg["std"])[:, None, None]

        return img[None, ...]

    def predict(image):
        # Preprocessing
        np_img = preprocess_image(image)
        ort_input = {ort_session.get_inputs()[0].name: np_img}

        # Inference
        ort_out = ort_session.run(None, ort_input)
        # Post-processing
        probs = 1 / (1 + np.exp(-ort_out[0][0]))

        return {class_name: float(conf) for class_name, conf in zip(cfg["classes"], probs)}

    img = gr.inputs.Image(type="pil")
    outputs = gr.outputs.Label(num_top_classes=1)

    interface = gr.Interface(
        fn=predict,
        inputs=[img],
        outputs=outputs,
        title="PyroVision: image classification demo",
        article=(
            "<p style='text-align: center'><a href='https://github.com/pyronear/pyro-vision'>"
            "Github Repo</a> | "
            "<a href='https://pyronear.org/pyro-vision/'>Documentation</a></p>"
        ),
        live=True,
    )

    interface.launch(server_port=args.port, show_error=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PyroVision image classification demo", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--repo", type=str, default="pyronear/rexnet1_0x", help="HF Hub repo to use")
    parser.add_argument("--port", type=int, default=8001, help="Port on which the webserver will be run")
    args = parser.parse_args()

    main(args)
