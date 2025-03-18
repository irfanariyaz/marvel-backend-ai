# from app.utils.document_loaders import get_docs
# from app.tools.presentation_generator.outline_generator.tools import OutlineGenerator
# from app.services.schemas import PresentationGeneratorArgs
# from app.services.logger import setup_logger
# from app.api.error_utilities import LoaderError, ToolExecutorError
# from app.services.cache_service import CacheInterface
# from fastapi import APIRouter, Depends, HTTPException
# from fastapi import Request
# import uuid
# import json


# logger = setup_logger()
# async def get_cache_service(request: Request) -> CacheInterface:
#     return request.app.state.cache_service

# async def executor(grade_level: str,
#              n_slides: int,
#              topic: str,
#              objectives: str,
#              file_url: str,
#              file_type: str,
#              lang: str, 
#              verbose=False,
#              cache: CacheInterface = Depends(get_cache_service)):

#     try:
#         docs = None

#         def fetch_docs(file_url, file_type):
#             return get_docs(file_url, file_type, True) if file_url and file_type else None
#         if file_url:
#             docs = fetch_docs(file_type=file_type, file_url=file_url)   

#         presentation_generator_args = PresentationGeneratorArgs(
#             grade_level=grade_level,
#             n_slides=n_slides,
#             topic=topic,
#             objectives=objectives,
#             file_type=file_type,
#             file_url=file_url,
#             lang=lang
#         )

#         output = OutlineGenerator(args=presentation_generator_args, verbose=verbose).compile(docs)
#         presentation_id = str(uuid.uuid4())
#         #,"context":result["context"]
#         request_input_dict = {
#             "grade_level": grade_level,
#             "n_slides": n_slides,
#             "topic": topic,
#             "objectives": objectives,
#             "lang": lang
#                     }

#         await cache.set(
#             f"presentation:{presentation_id}",
#             json.dumps({"outline": output["outline"], "inputs": request_input_dict,"context":output["context"]})
#         )

#         logger.info(f"Presentation generated successfully")

#     except LoaderError as e:
#         error_message = e
#         logger.error(f"Error in Presentation Generator Pipeline -> {error_message}")
#         raise ToolExecutorError(error_message)

#     except Exception as e:
#         error_message = f"Error in executor: {e}"
#         logger.error(error_message)
#         raise ValueError(error_message)

#     return output
from fastapi import Request, Depends
import uuid
import json
from app.utils.document_loaders import get_docs
from app.tools.presentation_generator.outline_generator.tools import OutlineGenerator
from app.services.schemas import PresentationGeneratorArgs
from app.services.logger import setup_logger
from app.api.error_utilities import LoaderError, ToolExecutorError
from app.services.cache_service import CacheInterface

logger = setup_logger()

# Function to get Redis cache service from FastAPI app state
async def get_cache_service(request: Request) -> CacheInterface:
    return request.app.state.cache_service

# Executor function with Redis caching
async def executor(
    grade_level: str,
    n_slides: int,
    topic: str,
    objectives: str,
    file_url: str,
    file_type: str,
    lang: str, 
    cache:CacheInterface, # Inject cache service
    verbose: bool = False
):
    try:
        docs = None

        # Function to fetch documents if file_url and file_type are provided
        def fetch_docs(file_url, file_type):
            return get_docs(file_url, file_type, True) if file_url and file_type else None

        if file_url:
            docs = fetch_docs(file_url=file_url, file_type=file_type)   

        # Prepare arguments for presentation generator
        presentation_generator_args = PresentationGeneratorArgs(
            grade_level=grade_level,
            n_slides=n_slides,
            topic=topic,
            objectives=objectives,
            file_type=file_type,
            file_url=file_url,
            lang=lang
        )

        # Generate outline
        output = OutlineGenerator(args=presentation_generator_args, verbose=verbose).compile(docs)

        # Generate a unique presentation ID
        presentation_id = str(uuid.uuid4())

        # Prepare request input dictionary
        request_input_dict = {
            "grade_level": grade_level,
            "n_slides": n_slides,
            "topic": topic,
            "objectives": objectives,
            "lang": lang
        }

        # Store data in Redis cache
        await cache.set(
            f"presentation:{presentation_id}",
            json.dumps({"outline": output["outline"], "inputs": request_input_dict, "context": output.get("context", [])})
        )
        # data={
        #     "outline": output,
        #     "presentation_id": presentation_id
        # }
        output["presentation_id"]=presentation_id
        logger.info("Presentation generated successfully")

    except LoaderError as e:
        error_message = f"LoaderError: {str(e)}"
        logger.error(f"Error in Presentation Generator Pipeline -> {error_message}")
        raise ToolExecutorError(error_message)

    except Exception as e:
        error_message = f"Error in executor: {str(e)}"
        logger.error(error_message)
        raise ValueError(error_message)

    return output
