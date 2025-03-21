
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
import firebase_admin
from firebase_admin import credentials, storage
import uuid
import asyncio
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
                    slide_data["visual_notes"]
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
            context_info = f"Relevant Context: {self.context_text}" if self.context_text else "No additional context."
            base_context = (
                f"Creating a presentation for:\n"
                f"Grade Level: {self.inputs['grade_level']}\n"
                f"Topic: {self.inputs['topic']}\n"
                f"Learning Objectives: {self.inputs['objectives']}\n"
                f"Language: {self.inputs['lang']}\n"
                f"{context_info}\n\n"
            )

            # prompts = {}
            
            # for idx, slide in enumerate(self.outline["slides"]):

                # prompt = PromptTemplate(
                #     template=(
                #         f"{base_context}\n"
                #         f"Generate structured content for Slide {idx + 1}.\n\n"
                #         f"Topic: {slide['topic']}\n"
                #         f"Description: {slide['description']}\n"
                #         f"Transition: {prev_transition}\n\n"
                #         "### Instructions:\n"
                #         "1. Ensure the content aligns with the grade level.\n"
                #         "2. Use clear, concise, and engaging language.\n"
                #         "3. Include key points and relevant examples.\n"
                #         "4. Maintain logical flow and adhere to the transition provided.\n"
                #         "5. Support learning objectives effectively.\n"
                #         "6. Assign an appropriate slide format to each slide based on its content. \n"
                #         "Select one appropriate format from  below formats for the current slide and generate content accordingly\n"
                #         "1) **Title Slide**:  optional subtitle.\n"
                #         "2) **Title and Body Slide**:  a paragraph of detailed text.\n"
                #         "3) **Title and Bullets Slide**: list of 3-5 concise bullet points.\n"
                #         "4) **Two-Column Slide**:  two columns of text or bullets.\n"
                #         "5) **Section Header Slide**: Large centered title and optional subtitle.\n\n"
                #         "### Output Format:\n"
                #         "Return a **valid JSON object** structured as follows:\n"
                #         "{{\n"
                #         "  \"title\": \"{{slide['topic']}}\",\n"
                #         "  \"template\": \"<One of the 5 slide types>\",\n"
                #         "  \"content\": {{<Structured content based on format> }},\n"
                #         "  \"needs_image\": <true/false>,\n"
                #         "  \"visual_notes\": \"Suggested visuals or 'None'\"\n"
                #         "}}\n\n"
                #         "### Constraints:\n"
                #         "- Ensure the JSON is syntactically correct.\n"
                #         "- Follow the predefined slide formats strictly.\n\n"
                #         "{format_instructions}"
                #     ),
                #     input_variables=[],
                #     partial_variables={"format_instructions": self.parser.get_format_instructions()}
                # )
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

            # prompts[f"slide_{idx + 1}"] = prompt_template
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
                image_pipeline = RunnableParallel(image_chains)
                image_results = image_pipeline.invoke({})
                
                # Step 3: Add image URLs to the slide results
                for result in image_results.values():
                    if result and "slide_key" in result and "image_url" in result:
                        slide_results[result["slide_key"]]["image_url"] = result["image_url"]

            # chains = {key: prompt | self.model | self.parser for key, prompt in prompts.items()}
            # parallel_pipeline = RunnableParallel(branches=chains)
            # results = parallel_pipeline.invoke({})

            if self.verbose:
                logger.info(f"Generated {len(slide_results)} slides successfully")

            # presentation = PresentationSchema(
            #         slides=[results["branches"][f"slide_{i+1}"] for i in range(len(self.outline["slides"]))]
            #     )
          
           # image_generator = ImageGenerator().generate_image("a cat playing with a red ball on a table")
            
            return dict(slide_results)

        except Exception as e:
            logger.error(f"Failed to generate slides: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate slides: {str(e)}")



