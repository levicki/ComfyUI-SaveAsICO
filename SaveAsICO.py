import os
import numpy as np
import torch
from PIL import Image
from folder_paths import get_directory_by_type, get_save_image_path
from comfy_api.latest import ComfyExtension, IO, UI
from typing_extensions import override

class SaveAsICO(IO.ComfyNode):
	output_dir = get_directory_by_type("output")
	ico_options = {
		"Application (64, 128, 256)": [256, 128, 64],
		"Favicon (16, 32, 48)": [48, 32, 16],
		"Windows (16, 24, 32, 48, 64, 128, 256)": [256, 128, 64, 48, 32, 24, 16],
	}

	@classmethod
	def define_schema(cls):
		return IO.Schema(
			node_id="SaveAsICO",
			display_name="Save As ICO",
			category="image",
			inputs=[
				IO.Image.Input("images", tooltip="The images to save."),
				IO.String.Input("filename_prefix", default="ICON", tooltip=("The prefix for the file to save. May include formatting tokens such as %width%, %height%, %year%, %month%, %day%, %hour%, %minute%, %second%.")),
				IO.Combo.Input("size_preset", options=list(cls.ico_options.keys()), default="Windows (16, 24, 32, 48, 64, 128, 256)"),
			],
			is_output_node=True,
			outputs=[IO.Image.Output(display_name="images")]
		)

	@classmethod
	def execute(cls, images, filename_prefix, size_preset) -> IO.NodeOutput:
		target_sizes = cls.ico_options[size_preset]

		ui_results = []

		full_output_folder, filename, counter, subfolder, filename_prefix = get_save_image_path(filename_prefix, cls.output_dir, images[0].shape[1], images[0].shape[0])

		os.makedirs(full_output_folder, exist_ok=True)

		for (batch_number, image) in enumerate(images):
			# image_array = (255. * image.cpu().numpy()).astype(np.uint8)
			image_array = np.clip(np.rint(255. * image.cpu().numpy()), 0, 255).astype(np.uint8)
			
			if image_array.shape[-1] != 4:
				raise ValueError(f"SaveAsICO Error: Input image must contain an alpha channel (RGBA). Received shape: {image_array.shape}.")

			base_image = Image.fromarray(image_array, mode="RGBA")

			if base_image.width != 256 or base_image.height != 256:
				raise ValueError(f"SaveAsICO Error: Source image must be 256 x 256 pixels. Received dimensions: {base_image.width}x{base_image.height}.")

			filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
			file_ico = f"{filename_with_batch_num}_{counter:05}.ico"
			file_png = f"{filename_with_batch_num}_{counter:05}.png"
			file_path_ico = os.path.join(full_output_folder, file_ico)
			file_path_png = os.path.join(full_output_folder, file_png)

			try:
				ico_frames = []
				for s in target_sizes:
					if base_image.width == s and base_image.height == s:
						ico_frames.append(base_image.copy())
					else:
						# resized_frame = base_image.copy()
						# resized_frame.thumbnail((s, s), Image.LANCZOS)
						# ico_frames.append(resized_frame)
						ico_frames.append(base_image.resize((s, s), Image.LANCZOS))

				ico_frames[0].save(file_path_ico, format="ICO", append_images=ico_frames[1:], sizes=[(f.width, f.height) for f in ico_frames])

				base_image.save(file_path_png, format="PNG")

				ui_results.append({"filename": file_png, "subfolder": subfolder, "type": "output"})

				counter += 1

			except Exception as ErrorException:
				raise RuntimeError(f"SaveAsICO Error: Failed to save ICO image '{file_path_ico}'. Details: {str(ErrorException)}")

		return IO.NodeOutput(images, ui={"images": ui_results})

class SaveAsICOExtension(ComfyExtension):
	@override
	async def get_node_list(self) -> list[type[IO.ComfyNode]]:
		return [SaveAsICO]

async def comfy_entrypoint() -> SaveAsICOExtension:
	return SaveAsICOExtension()
