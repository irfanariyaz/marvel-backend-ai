# #from app.utils.document_loaders import get_docs
# from app.tools.presentation_generator.slide_generator.tools import SlidesGenerator
# # from app.services.schemas import PresentationGeneratorArgs
# from app.services.logger import setup_logger
# # from app.api.error_utilities import LoaderError, ToolExecutorError
# from app.services.cache_service import CacheInterface
# from fastapi import APIRouter, Depends, HTTPException
from app.utils.auth import key_check
from fastapi import Request
# import json
# from fastapi.responses import JSONResponse
# from fastapi.encoders import jsonable_encoder
# from app.api.error_utilities import InputValidationError, ErrorResponse
# from app.services.schemas import GenericAssistantRequest, ToolRequest, ChatRequest, Message, ChatResponse, ToolResponse

# logger = setup_logger()
# async def get_cache_service(request: Request) -> CacheInterface:
#     return request.app.state.cache_service

# async def executor(presentation_id: str,
#     cache:CacheInterface=Depends(get_cache_service),
#     _ = Depends(key_check),verbose=False):

#     logger.info(presentation_id)
#     try:
        
#         context_str = await cache.get(f"presentation:{presentation_id}")
#         if not context_str:
#             raise HTTPException(status_code=404, detail="Presentation context not found")

#         context = json.loads(context_str)

#         logger.info(context)
        
#         # Extract context text
        

#         slides = SlidesGenerator(
#             outline=context["outline"],
#             inputs=context["inputs"],
#             context_text=context["context"] # Pass context to generator
#         ).compile()
#         if slides is None:
#             raise HTTPException(status_code=500, detail="Slide generation failed")

#         return ToolResponse(data=slides)
        
#     except HTTPException as e:
#         logger.error(f"HTTPException: {e}")
#         logger.info(f'From HTTP Exception in core.py')
#         return JSONResponse(
#             status_code=e.status_code,
#             content=jsonable_encoder(ErrorResponse(status=e.status_code, message=e.detail))
#         )
from fastapi import APIRouter, Depends, HTTPException
from app.services.cache_service import CacheInterface
from app.tools.presentation_generator.slide_generator.tools import SlidesGenerator
from app.services.logger import setup_logger
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.api.error_utilities import ErrorResponse
from app.services.schemas import ToolResponse
import json


logger = setup_logger()



async def executor(presentation_id: str,
                   cache: CacheInterface,
                   _ = Depends(key_check), verbose=False):

    logger.info(presentation_id)
    try:
        # Ensure that cache is a valid CacheInterface instance
        if not isinstance(cache, CacheInterface):
            raise HTTPException(status_code=500, detail="Cache service not available")

        # Retrieve cached data
        context_str = await cache.get(f"presentation:{presentation_id}")
        if not context_str:
            raise HTTPException(status_code=404, detail="Presentation context not found")

        # Load the JSON context
        context = json.loads(context_str)
        logger.info(context)

        # Generate slides
        slides = SlidesGenerator(
            outline=context["outline"],
            inputs=context["inputs"],
            context_text=context["context"]  # Pass context to generator
        ).compile()

        if slides is None:
            raise HTTPException(status_code=500, detail="Slide generation failed")

        return ToolResponse(data=slides)

    except HTTPException as e:
        logger.error(f"HTTPException: {e}")
        logger.info(f'From HTTP Exception in core.py')
        return JSONResponse(
            status_code=e.status_code,
            content=jsonable_encoder(ErrorResponse(status=e.status_code, message=e.detail))
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(ErrorResponse(status=500, message="Internal Server Error"))
        )
