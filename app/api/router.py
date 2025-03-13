import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from typing import Union
from app.assistants.utils.assistants_utilities import execute_assistant
from app.services.schemas import GenericAssistantRequest, ToolRequest, ChatRequest, Message, ChatResponse, ToolResponse
from app.utils.auth import key_check
from app.services.logger import setup_logger
from app.api.error_utilities import InputValidationError, ErrorResponse
from app.tools.utils.tool_utilities import load_tool_metadata, execute_tool, finalize_inputs

import uuid
from fastapi import FastAPI
from fastapi import Request
import json
from app.services.cache_service import CacheInterface
from app.tools.presentation_generator.slide_generator.core import executor

logger = setup_logger(__name__)
router = APIRouter()
app = FastAPI()

# Initialize presentation contexts in app state if not exists
if not hasattr(app.state, "presentation_contexts"):
    app.state.presentation_contexts = {}


# Dependency injection
async def get_cache_service(request: Request) -> CacheInterface:
    return request.app.state.cache_service

@router.get("/")
def read_root():
    return {"Hello": "World"}

# Handles two-step presentation generation:
# 1. Generate outline with initial inputs
# 2. Generate slides using stored outline and inputs
@router.post("/generate-outline", response_model=Union[ToolResponse, ErrorResponse])
async def generate_outline(
    data: ToolRequest, 
    cache: CacheInterface = Depends(get_cache_service),
    _ = Depends(key_check)
):
    try:
        # Potential Bottleneck: execute tool can be a blocking operation
        # Solution: Use Redis Queue or Celery for background tasks
        # Execute outline generation and store context for slides generation
        request_data = data.tool_data

        requested_tool = load_tool_metadata(request_data.tool_id)

        request_inputs_dict = finalize_inputs(request_data.inputs, requested_tool['inputs'])

        result = execute_tool(request_data.tool_id, request_inputs_dict)
        logger.info(f"requested_input_dict:{request_inputs_dict}")
        logger.info(result)
        
        # Store in app cache, to use as context for slides generation
        presentation_id = str(uuid.uuid4())
        #,"context":result["context"]
        await cache.set(
            f"presentation:{presentation_id}",
            json.dumps({"outline": result["outline"], "inputs": request_inputs_dict,"context":result["context"]})
        )
        
        return ToolResponse(data={
            "outline": result["outline"],
            "presentation_id": presentation_id
        })
    
    except InputValidationError as e:
        logger.error(f"InputValidationError: {e}")
        return JSONResponse(
            status_code=400,
            content=jsonable_encoder(ErrorResponse(status=400, message=e.message))
        )
    
    except HTTPException as e:
        logger.error(f"HTTPException: {e}")
        return JSONResponse(
            status_code=e.status_code,
            content=jsonable_encoder(ErrorResponse(status=e.status_code, message=e.detail))
        )


        
@router.post("/generate-slides/{presentation_id}", response_model=Union[ToolResponse, ErrorResponse])
async def generate_slides(
    #data:ToolRequest,
    presentation_id:str,
    cache: CacheInterface = Depends(get_cache_service),
    
    _ = Depends(key_check)
):
    try:
       
        
       #requested_tool = load_tool_metadata("slide-generator")
        
        #request_inputs_dict = finalize_inputs(request_data.inputs, requested_tool['inputs'])
       tool_id="slide-generator" 
       input_dict={"presentation_id":presentation_id,"cache":cache}
       result = await execute_tool(tool_id,input_dict )
     #  result=await executor(presentation_id=presentation_id)
       return result

        
    except InputValidationError as e:
        logger.error(f"InputValidationError: {e}")
        logger.info(f'From Input Validation Error in router.py')
        return JSONResponse(
            status_code=400,
            content=jsonable_encoder(ErrorResponse(status=400, message=e.message))
        )

    except HTTPException as e:
        logger.error(f"HTTPException: {e}")
        logger.info(f'From HTTP Exception Error in router.py')
        return JSONResponse(
            status_code=e.status_code,
            content=jsonable_encoder(ErrorResponse(status=e.status_code, message=e.detail))
        )

@router.post("/submit-tool", response_model=Union[ToolResponse, ErrorResponse])
async def submit_tool( data: ToolRequest, _ = Depends(key_check)):     
    try: 
        # Unpack GenericRequest for tool data
        request_data = data.tool_data
        
        requested_tool = load_tool_metadata(request_data.tool_id)
        
        request_inputs_dict = finalize_inputs(request_data.inputs, requested_tool['inputs'])

        result = execute_tool(request_data.tool_id, request_inputs_dict)
        
        return ToolResponse(data=result)
    
    except InputValidationError as e:
        logger.error(f"InputValidationError: {e}")

        return JSONResponse(
            status_code=400,
            content=jsonable_encoder(ErrorResponse(status=400, message=e.message))
        )
    
    except HTTPException as e:
        logger.error(f"HTTPException: {e}")
        return JSONResponse(
            status_code=e.status_code,
            content=jsonable_encoder(ErrorResponse(status=e.status_code, message=e.detail))
        )

@router.post("/assistant-chat", response_model=ChatResponse)
async def assistants( request: GenericAssistantRequest, _ = Depends(key_check) ):
    
    assistant_group = request.assistant_inputs.assistant_group
    assistant_name = request.assistant_inputs.assistant_name
    user_info = request.assistant_inputs.user_info
    messages = request.assistant_inputs.messages

    result = execute_assistant(assistant_group, assistant_name, user_info, messages)

    formatted_response = Message(
        role="ai",
        type="text",
        payload={"text": result}
    )
    
    return ChatResponse(data=[formatted_response])