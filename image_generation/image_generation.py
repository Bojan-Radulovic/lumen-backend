import torch
from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from safetensors.torch import load_file
from faststream import FastStream
from faststream.rabbit import RabbitBroker
import base64
import io

broker = RabbitBroker("amqp://guest:guest@localhost:5672/", timeout=2000.0)
app = FastStream(broker)

base = "stabilityai/stable-diffusion-xl-base-1.0"
ckpt = "models/sdxl_lightning_2step_unet.safetensors"

unet = UNet2DConditionModel.from_config(base, subfolder="unet").to("cuda", torch.float16)
unet.load_state_dict(load_file(ckpt, device="cuda"))

pipe = StableDiffusionXLPipeline.from_pretrained(
    base,
    unet=unet,
    torch_dtype=torch.float16,
    variant="fp16"
).to("cuda")

pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")

@broker.subscriber("to_image")
async def callback(msg):
    try:
        print("I recived: ", msg)
        prompt = str(msg['text'])
        image = pipe(prompt, num_inference_steps=2, guidance_scale=0).images[0]
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_bytes = base64.b64encode(buffer.getvalue()).decode('utf-8')
        torch.cuda.empty_cache()
        print("Sending image...")
        return {"image_bytes": image_bytes}
    except Exception as e:
        print(f"Error generating image: {e}")
        return {"error": "Error generating image."}

@app.after_startup
async def start():
    print("Waiting...")

