from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_vertexai.vision_models import VertexAIImageGeneratorChat
import base64
import io

from PIL import Image
from app.services.logger import setup_logger

logger = setup_logger(__name__)
class ImageGenerator:
    def __init__(self):
        self.generator = VertexAIImageGeneratorChat()
        self.prompts = []

    def generate_image(self, slide, prompt):
        messages = [HumanMessage(content=[prompt])]
        response = self.generator.invoke(messages)
        generated_image = response.content[0]
        img_base64 = generated_image["image_url"]["url"].split(",")[-1]

        # Convert base64 string to Image
        #img = Image.open(io.BytesIO(base64.decodebytes(bytes(img_base64, "utf-8"))))

        img_data = base64.b64decode(img_base64)
            # Save Image
        #img.save(slide + ".png")

        print("Image saved as generated_image1.png. Open it manually to view.")

        return img_data

    async def generate_image_async(self, slide_key, prompt):
        """
        Async version of generate_image to support parallel processing
        Returns the raw image data for further processing
        """
        try:
            # Improve the prompt for better image generation
            enhanced_prompt = f"Create a high-quality educational illustration for a presentation slide about: {prompt}. Make it visually appealing and suitable for educational content."
            
            messages = [HumanMessage(content=[enhanced_prompt])]
            
            # Run the image generation in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.generator.invoke(messages)
            )
            
            generated_image = response.content[0]
            img_base64 = generated_image["image_url"]["url"].split(",")[-1]
            
            # Convert base64 string to Image
            img_data = base64.b64decode(img_base64)
            
            # Open and save a copy for inspection if needed
            img = Image.open(io.BytesIO(img_data))
            img.save(f"{slide_key}.png")
            
            logger.info(f"Image for {slide_key} generated successfully")
            
            # Return the raw image data for Firebase upload
            return img_data
        except Exception as e:
            logger.error(f"Image generation failed for {slide_key}: {str(e)}")
            return None