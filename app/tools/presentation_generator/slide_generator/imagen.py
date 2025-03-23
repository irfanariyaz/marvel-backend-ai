from langchain_core.messages import AIMessage, HumanMessage
#from langchain_google_vertexai.vision_models import VertexAIImageGeneratorChat, ImageGenerationModel
from vertexai.preview.vision_models import ImageGenerationModel
from PIL import Image
from app.services.logger import setup_logger

logger = setup_logger(__name__)
class ImageGenerator:
    def __init__(self):
        self.generator  = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        self.prompts = []

    def generate_image(self, slide_number, slide):
        logger.info(f"Generating image for slide {slide} with prompt: {slide['visual_notes']}")
        model = self.generator
        response = model.generate_images(
            prompt=slide['visual_notes'],
            # Optional:
            number_of_images=1,
            aspect_ratio="16:9" if slide["template"] == "titleBody" or slide["template"] == "sectionHeader" else "4:3",
            seed=1,
            add_watermark=False,
        )
       
        if response.images:
            generated_image = response.images[0]
            logger.info(f"Generated image for slide {slide}")
            return generated_image
     
        else:
            logger.error("No images were generated.")
        return None


       