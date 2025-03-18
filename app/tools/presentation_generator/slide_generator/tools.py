
# from pydantic import BaseModel, Field
# from typing import List, Dict, Any
# from app.services.logger import setup_logger
# from langchain_core.prompts import PromptTemplate
# from langchain_core.runnables import RunnableParallel
# from langchain_core.output_parsers import JsonOutputParser
# from langchain_google_genai import GoogleGenerativeAI
# from fastapi import HTTPException

# logger = setup_logger(__name__)

# class SlidesGenerator:
#     def __init__(self, args=None ,verbose=False):
#         # Initialize LLM and parser for detailed slide content generation
#         self.outline = args.outline
#         self.inputs = args.inputs
#         self.context_text=args.context_text
#         self.verbose = verbose
#         self.model = GoogleGenerativeAI(model="gemini-1.5-pro")
#         self.parser = JsonOutputParser(pydantic_object=SlideContent)
        
        
#     def compile(self) -> dict:
#         try:
#             # Create base context from input args
#             base_context = (
#                 "Creating a presentation for:\n"
#                 f"Grade Level: {self.inputs['grade_level']}\n"
#                 f"Topic: {self.inputs['topic']}\n"
#                 f"Learning Objectives: {self.inputs['objectives']}\n"
#                 f"Language: {self.inputs['lang']}\n"
#                 f"if {self.context_text} is not None, use content in {self.context_text} if relevant\n\n"
#             )

#             prompts = {}
#             # template=(
#             #             f"{base_context}\n"
#             #             f"Generate content for Slide {idx + 1}:\n"
#             #             f"Topic: {slide['topic']}\n"
#             #             f"Description: {slide['description']}\n"
#             #             f"Transition: {slide['transition']}\n\n"
#             #             "Create engaging slide content that:\n"
#             #             "1. Is appropriate for the grade level\n"
#             #             "2. Uses clear and concise language\n"
#             #             "3. Includes key points and examples\n"
#             #             "4. Creates an appropriate segue as per the transition\n"
#             #             "5. Supports learning objectives\n\n"
#             #             "Return a JSON object with 'topic' and 'content' fields.\n"
#             #             "The slides can be any of 5 formats. "
#             #             "1) Title Slide: Large title and optional subtitle (e.g., 'The iPhone Evolution: A History of Innovation') ,\n"
#             #             "2) Title and Body Slide:Title with a paragraph of detailed text (e.g., 'Understanding the Science' with a paragraph)"
#             #             "3) Title and Bullets Slide: 3-5 concise bullet points (e.g., 'Key Inventions: Engines of Change' with 'Steam Engine,' 'Spinning Jenny,' 'Power Loom')."
#             #             "4) Two-Column Slide: Title with two columns of paragraphs or bullets (e.g., 'Social Impact' with one column for 'Rise of Cities' and another for 'New Classes')"
#             #             "5) Section Header Slide: Large title (centered, bold) and optional subtitle (e.g., 'The Biggest Culprits' as a section divider)"
#             #             "Ensure the JSON is valid and complete.\n\n"
#             #             "{format_instructions}"
#             #         )
#             for idx, slide in enumerate(self.outline["slides"]):
#                 prompt = PromptTemplate(
#                     template = (
#                             f"{base_context}\n"
#                             f"Generate structured content for Slide {idx + 1}.\n\n"
#                             f"Topic: {slide['topic']}\n"
#                             f"Description: {slide['description']}\n"
#                             f"Transition: {slide['transition']}\n\n"
                            
#                             "### Instructions:\n"
#                             "1. Ensure the content aligns with the grade level.\n"
#                             "2. Use clear, concise, and engaging language.\n"
#                             "3. Include key points and relevant examples.\n"
#                             "4. Maintain logical flow and adhere to the transition provided.\n"
#                             "5. Support learning objectives effectively.\n\n"

#                             "### Slide Format Types (Select One):\n"
#                             "1) **Title Slide**: Large title and optional subtitle \n"
#                             "   - Example: {\"title\": \"The iPhone Evolution\", \"subtitle\": \"A History of Innovation\"}\n"
#                             "2) **Title and Body Slide**: Title with a paragraph of detailed text \n"
#                             "   - Example: {\"title\": \"Understanding the Science\", \"body\": \"Detailed explanation...\"}\n"
#                             "3) **Title and Bullets Slide**: Title with 3-5 concise bullet points \n"
#                             "   - Example: {\"title\": \"Key Inventions\", \"bullets\": [\"Steam Engine\", \"Spinning Jenny\", \"Power Loom\"]}\n"
#                             "4) **Two-Column Slide**: Title with two columns of text or bullets \n"
#                             "   - Example: {\"title\": \"Social Impact\", \"column_1\": \"Rise of Cities\", \"column_2\": \"New Classes\"}\n"
#                             "5) **Section Header Slide**: Large centered title and optional subtitle \n"
#                             "   - Example: {\"title\": \"The Biggest Culprits\", \"subtitle\": \"A section divider\"}\n\n"

#                             "### Output Format:\n"
#                             "Return a **valid JSON object** structured as follows:\n"
#                             "{\n"
#                             "  \"topic\": \"" + slide['topic'] + "\",\n"
#                             "  \"format\": \"<One of the 5 slide types>\",\n"
#                             "  \"content\": { <Structured content based on format> }\n"
#                             "}\n\n"

#                             "### Constraints:\n"
#                             "- Ensure the JSON is syntactically correct.\n"
#                             "- Do **not** include extraneous text or explanations.\n"
#                             "- Follow the predefined slide formats strictly.\n\n"

#                             "{format_instruction}"),
#                     #"The 'content' field can contain any structured data you want.
#                     input_variables=[],
#                     partial_variables={"format_instructions": self.parser.get_format_instructions()}
#                 )
#                 prompts[f"slide_{idx + 1}"] = prompt

#             chains = {
#                 key: prompt | self.model | self.parser
#                 for key, prompt in prompts.items()
#             }

#             parallel_pipeline = RunnableParallel(branches=chains)
            
#             results = parallel_pipeline.invoke({})

#             if self.verbose:
#                 logger.info(f"Generated {len(results['branches'])} slides successfully")

#             # Compile final presentation structure
#             presentation = PresentationSchema(
#                 slides=[results["branches"][f"slide_{i+1}"] for i in range(len(self.outline["slides"]))]
#             )

#             return dict(presentation)

#         except Exception as e:
#             logger.error(f"Failed to generate slides: {str(e)}")
#             logger.debug(f"Results:{results}")
#             raise HTTPException(status_code=500, detail=f"Failed to generate slides: {str(e)}")

# # Defines expected structure for each slide in the presentation
# class SlideContent(BaseModel):    
#     title: str = Field(..., description="The title of the slide")    
#     template: str = Field(..., description="The slide template type: sectionHeader, titleAndBody, titleAndBullets, twoColumn")    
#         #content: Optional[Union[str, list, dict, Any]] = Field(None, description="Content of the slide, can be string, list, dict, or any type")    
#     content: str | list | dict |Any = Field(None, description="Content of the slide, can be string, list, dict, or any type")    
#     needs_image: bool = Field(..., description="Whether the slide requires an image")    
#     visual_notes:str = Field(..., description="Suggested visuals based on content of the slide.If no visuals are suggested, enter 'None'")

# # Defines expected structure for the entire presentation
# class PresentationSchema(BaseModel):
#     slides: List[SlideContent] = Field(description="List of slides with their content")

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union
from app.services.logger import setup_logger
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import GoogleGenerativeAI
from fastapi import HTTPException

logger = setup_logger(__name__)

class SlideContent(BaseModel):
    title: str = Field(..., description="The title of the slide")
    template: str = Field(..., description="The slide template type: sectionHeader, titleAndBody, titleAndBullets, twoColumn")
    content: Union[str, List[str], Dict[str, Any]] = Field(None, description="Content of the slide, structured based on template")
    needs_image: bool = Field(..., description="Whether the slide requires an image")
    visual_notes: str = Field(..., description="Suggested visuals for the slide. If none, enter 'None'")

class PresentationSchema(BaseModel):
    slides: List[SlideContent] = Field(description="List of slides with their content")

class SlidesGenerator:
    def __init__(self, args=None, verbose=False):
        if not args or not hasattr(args, 'outline') or not hasattr(args, 'inputs'):
            raise ValueError("Missing required arguments: 'outline' and 'inputs' are mandatory.")
        
        self.outline = args.outline
        self.inputs = args.inputs
        self.context_text = args.context_text if hasattr(args, 'context_text') else None
        self.verbose = verbose
        self.model = GoogleGenerativeAI(model="gemini-1.5-pro")
        self.parser = JsonOutputParser(pydantic_object=SlideContent)
    
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

            prompts = {}
            prev_transition=None
            for idx, slide in enumerate(self.outline["slides"]):

                prompt = PromptTemplate(
                    template=(
                        f"{base_context}\n"
                        f"Generate structured content for Slide {idx + 1}.\n\n"
                        f"Topic: {slide['topic']}\n"
                        f"Description: {slide['description']}\n"
                        f"Transition: {prev_transition}\n\n"
                        "### Instructions:\n"
                        "1. Ensure the content aligns with the grade level.\n"
                        "2. Use clear, concise, and engaging language.\n"
                        "3. Include key points and relevant examples.\n"
                        "4. Maintain logical flow and adhere to the transition provided.\n"
                        "5. Support learning objectives effectively.\n"
                        "6. Assign an appropriate slide format to each slide based on its content. \n"
                        "Select one appropriate format from  below formats for the current slide and generate content accordingly\n"
                        "1) **Title Slide**: Large title and optional subtitle.\n"
                        "2) **Title and Body Slide**: Title with a paragraph of detailed text.\n"
                        "3) **Title and Bullets Slide**: list of 3-5 concise bullet points.\n"
                        "4) **Two-Column Slide**: Title with two columns of text or bullets.\n"
                        "5) **Section Header Slide**: Large centered title and optional subtitle.\n\n"
                        "### Output Format:\n"
                        "Return a **valid JSON object** structured as follows:\n"
                        "{{\n"
                        "  \"title\": \"{{slide['topic']}}\",\n"
                        "  \"template\": \"<One of the 5 slide types>\",\n"
                        "  \"content\": {{<Structured content based on format> }},\n"
                        "  \"needs_image\": <true/false>,\n"
                        "  \"visual_notes\": \"Suggested visuals or 'None'\"\n"
                        "}}\n\n"
                        "### Constraints:\n"
                        "- Ensure the JSON is syntactically correct.\n"
                        "- Follow the predefined slide formats strictly.\n\n"
                        "{format_instructions}"
                    ),
                    input_variables=[],
                    partial_variables={"format_instructions": self.parser.get_format_instructions()}
                )
                prev_transition=slide['transition']
                prompts[f"slide_{idx + 1}"] = prompt

            chains = {key: prompt | self.model | self.parser for key, prompt in prompts.items()}
            parallel_pipeline = RunnableParallel(branches=chains)
            results = parallel_pipeline.invoke({})

            if self.verbose:
                logger.info(f"Generated {len(results['branches'])} slides successfully")

            presentation = PresentationSchema(
                    slides=[results["branches"][f"slide_{i+1}"] for i in range(len(self.outline["slides"]))]
                )
            return dict(presentation)

        except Exception as e:
            logger.error(f"Failed to generate slides: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate slides: {str(e)}")
