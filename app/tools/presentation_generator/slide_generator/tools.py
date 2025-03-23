
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union
from app.services.logger import setup_logger
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import GoogleGenerativeAI
from fastapi import HTTPException
from app.tools.presentation_generator.slide_generator.imagen import ImageGenerator
from app.tools.presentation_generator.slide_generator.firebase import FirebaseManager
import os
logger = setup_logger(__name__)

def read_text_file(file_path):
    # Get the directory containing the script file
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Combine the script directory with the relative file path
    absolute_file_path = os.path.join(script_dir, file_path)

    with open(absolute_file_path, 'r') as file:
        return file.read()
    
class SlideContent(BaseModel):
    title: str = Field(..., description="The title of the slide")
    template: str = Field(..., description="The slide template type: sectionHeader, titleAndBody, titleAndBullets, twoColumn")
    content: Union[str, List[str], Dict[str, Any]] = Field(None, description="Content of the slide, structured based on template")
    needs_image: bool = Field(..., description="Whether the slide requires an image")
    visual_notes: str = Field(..., description="Suggested visual illustration for the slide. If none, enter 'None'")

class PresentationSchema(BaseModel):
    slides: List[SlideContent] = Field(description="List of slides with their content")

class OutputSlideSchema(BaseModel):
    title: str = Field(..., description="The title of the slide")
    template: str = Field(..., description="The slide template type: sectionHeader, titleAndBody, titleAndBullets, twoColumn")
    content: Union[str, List[str], Dict[str, Any]] = Field(None, description="Content of the slide, structured based on template")
    image_url: str | None = Field(default=None, description="URL of the generated image for the slide, if applicable")

class SlidesGenerator:
    def __init__(self, args=None, verbose=False):
        if not args or not hasattr(args, 'outline') or not hasattr(args, 'inputs'):
            raise ValueError("Missing required arguments: 'outline' and 'inputs' are mandatory.")
        self.args = args
        self.outline = args.outline
        self.inputs = args.inputs
        self.context_text = args.context_text if hasattr(args, 'context_text') else None
        self.verbose = verbose
        self.model = GoogleGenerativeAI(model="gemini-1.5-pro")
        self.parser = JsonOutputParser(pydantic_object=SlideContent)
        self.prompt = read_text_file("prompts/slide_generator_prompt.txt")
        self.image_generator = ImageGenerator()
        self.firebase = FirebaseManager()


    def generate_slide_image(self, slide_key, slide_data):
         """
        Create a RunnableLambda for processing a single slide image
        """
         
         def process_image_for_slide(_):
                if not slide_data.get("needs_image", False) or not slide_data.get("visual_notes"):
                    return None
                
                # Generate image using the provided visual notes
                image_data = self.image_generator.generate_image(
                    slide_key, 
                    slide_data
                )
                
                # Upload the image to Firebase
                image_url = self.firebase.upload_image(
                    image_data, 
                    f"slides/{self.args.inputs.get('topic', 'presentation').replace(' ', '_')}/{slide_key}.png"
                )
                
                # Return the image URL to be added to the slide data
                return {"slide_key": slide_key, "image_url": image_url}
        
         return RunnableLambda(process_image_for_slide)
    
    def compile(self) -> dict:
        try:
                        
            prompts = {}
    
            previous_transition=None
            prompt_template = PromptTemplate(
                template=self.prompt,
                input_variables=["outline" "description", "previous_transition", "grade_level", "context","slide_number"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
                )
            
            
            for i, slide in enumerate(self.args.outline["slides"]):
                
                prompts[f'slide_{i+1}'] = prompt_template.partial(
                    outline=slide["topic"],
                    description=slide["description"],
                    previous_transition=previous_transition,
                    grade_level=self.args.inputs["grade_level"],
                    context=self.context_text,
                    slide_number=i+1
                
                )
                previous_transition = slide.get("transition", previous_transition)

        
            # Create chains for processing slides
            chains = {
                key: prompt | self.model | self.parser  # Ensuring Pydantic model validation
                for key, prompt in prompts.items()
            }

            # Run chains in parallel
            parallel_pipeline = RunnableParallel(chains)
            slide_results = parallel_pipeline.invoke({})
            logger.info(f"Results: {slide_results}")
           
            #  Create image generation chains using RunnableParallel
            image_chains = {}
            for slide_key, slide_data in slide_results.items():
                if slide_data["needs_image"]:                         
                    image_chains[f"image_{slide_key}"] = self.generate_slide_image(slide_key, slide_data)
            
            # Only run image generation if there are images to generate
            if image_chains:
                #run  first 2 image chain(as per the quota requirement)
                image_chains_with2URLS = {k: v for i, (k, v) in enumerate(image_chains.items()) if i < 2}
                image_pipeline = RunnableParallel(image_chains_with2URLS)
                image_results = image_pipeline.invoke({})
                
                #  Add image URLs to the slide results
                for result in image_results.values():
                    if result and "slide_key" in result and "image_url" in result:
                        slide_results[result["slide_key"]]["image_url"] = result["image_url"]

            if self.verbose:
                logger.info(f"Generated {len(slide_results)} slides successfully")

            #convert the slide to OutputSlideSchema
            results =[
                OutputSlideSchema(
                    title=slide["title"],
                    template=slide["template"],
                    content=slide["content"],
                    image_url=slide.get("image_url", None)
                ) for slide in slide_results.values()
            ]
            return results

        except Exception as e:
            logger.error(f"Failed to generate slides: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate slides: {str(e)}")



