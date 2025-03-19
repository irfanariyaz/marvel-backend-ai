
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union
from app.services.logger import setup_logger
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import GoogleGenerativeAI
from fastapi import HTTPException
from app.tools.presentation_generator.slide_generator.imagen import ImageGenerator
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
            results = parallel_pipeline.invoke({})


            # chains = {key: prompt | self.model | self.parser for key, prompt in prompts.items()}
            # parallel_pipeline = RunnableParallel(branches=chains)
            # results = parallel_pipeline.invoke({})

            if self.verbose:
                logger.info(f"Generated {len(results)} slides successfully")

            # presentation = PresentationSchema(
            #         slides=[results["branches"][f"slide_{i+1}"] for i in range(len(self.outline["slides"]))]
            #     )
          
            image_generator = ImageGenerator().generate_image("a cat playing with a red ball on a table")
            
            return dict(results)

        except Exception as e:
            logger.error(f"Failed to generate slides: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate slides: {str(e)}")



