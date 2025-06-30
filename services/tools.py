from faststream.rabbit import RabbitBroker
from langchain.tools import tool
from typing import Annotated
import ast
import asyncio
import concurrent.futures
import uuid
import base64
import os
from constants import OUTPUT_DIR
from dependencies import mailjet
from langchain_core.tools import Tool
from langchain_experimental.utilities import PythonREPL


@tool
def image_generation_tool(
    prompt: Annotated[str, "Just a string for the image you want to generate. Keep it short and simple."],
):
    """Generate an image."""
    id = uuid.uuid4()
    def run_image_generation():
        """Run the image generation synchronously in a separate thread."""
        try:
            print(f"Sending prompt to image generator: {prompt}")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def generate_image():
                message = {
                    'text': prompt,
                }
                
                img_broker = RabbitBroker(
                    "amqp://guest:guest@localhost:5672/?heartbeat=2000",
                    timeout=2000.0,
                )
                await img_broker.connect()
                try:
                    print("Publishing message to image queue...")
                    response = await img_broker.publish(
                        message,
                        queue="to_image",
                        rpc=True,
                        timeout=2000.0,
                        rpc_timeout= 2000.0,
                        raise_timeout= True,
                    )
                    print(f"Received response from image generator.")
                    return response
                finally:
                    await img_broker.close()
            
            try:
                response = loop.run_until_complete(generate_image())
                
                if response is None:
                    return "Error: No response received from image generator."
                
                if isinstance(response, dict) and "error" in response:
                    return f"Error generating image: {response['error']}."
                
                if isinstance(response, dict) and "image_bytes" in response:
                    image_data = base64.b64decode(response["image_bytes"])
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    file_path = os.path.join(OUTPUT_DIR, f'{id}.png')
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    return f"Image generated successfully! ID:{id}"
                else:
                    return "Error: Invalid response format from image generator."
                
            finally:
                loop.close()
                
        except asyncio.TimeoutError:
            return "Error: Image generation timed out."
        except Exception as e:
            print(f"Error in image generation: {e}")
            return f"Error generating image: {str(e)}."
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_image_generation)
        try:
            result = future.result(timeout=2000.0)
            return result
        except concurrent.futures.TimeoutError:
            return "Error: Image generation process timed out. Please try again."
        except Exception as e:
            return f"Error: {str(e)}. Please try again."
        
@tool
def think_tool(
    thought: Annotated[str, "Something you want to think about."],
) -> str:
    """Think about a thought."""
    return thought

@tool
def send_email_tool(
    email_info: Annotated[str, "Tuple: 'Email address to which the email will be sent', 'The subject (title) of the email', 'Content of the email (make it short, not more then a few short sentences)'"],
) -> str:
    """Send an email. Only use when explicitly told. Always include this when using tool: Action: send_email_tool Action Input: email_info tuple. Always end chat after using this tool by telling the user if the email was sent or not."""
    email_info = email_info.replace("'''", "").replace('"""', '').strip()
    email_info = email_info.replace("'s", "'s")
    email_info_tuple = ast.literal_eval(email_info)

    to_email = email_info_tuple[0]
    subject = email_info_tuple[1]
    html_content = email_info_tuple[2]

    data = {
        'Messages': [
            {
                "From": {
                    "Email": "lumen@bojan-radulovic.xyz",
                    "Name": "Lumen"
                },
                "To": [
                    {
                        "Email": to_email,
                        "Name": "Recipient"
                    }
                ],
                "Subject": subject,
                "HTMLPart": html_content + "<p><strong>This email was sent using the Lumen AI agent.</strong></p>"
            }
        ]
    }
    try:
        result = mailjet.send.create(data=data)
        if result.status_code == 200:
            return f"Email sent! Status Code: {result.status_code}."
        else:
            return f"Failed to send email. Status Code: {result.status_code}."
    except Exception as e:
        return f"Error: {e}."
    
python_repl = PythonREPL()
repl_tool = Tool(
    name="python_repl",
    description="A Python shell. Use this to execute python commands. Use the tool sparingly, for example for calculations, generating numbers, when asked to run python code etc. Input should be a valid python command. End the command by printing the value you want with `print(...)`.",
    func=python_repl.run,
)