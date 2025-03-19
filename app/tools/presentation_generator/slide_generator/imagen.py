from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_vertexai.vision_models import VertexAIImageGeneratorChat
import base64
import io

from PIL import Image

class ImageGenerator:
    def __init__(self):
        self.generator = VertexAIImageGeneratorChat()
        self.prompts = []

    def generate_image(self, prompt):
        messages = [HumanMessage(content=[prompt])]
        response = self.generator.invoke(messages)
        generated_image = response.content[0]
        img_base64 = generated_image["image_url"]["url"].split(",")[-1]

        # Convert base64 string to Image
        img = Image.open(io.BytesIO(base64.decodebytes(bytes(img_base64, "utf-8"))))

    
            # Save Image
        img.save("generated_image1.png")

        print("Image saved as generated_image1.png. Open it manually to view.")

        return generated_image
