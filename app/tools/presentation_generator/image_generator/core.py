from fastapi import HTTPException
from app.services.logger import setup_logger
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.api.error_utilities import ErrorResponse
from app.services.cache_service import CacheInterface
from fastapi import Depends
from app.utils.auth import key_check

logger=setup_logger()
#presentation_id:str,cache:CacheInterface,_=Depends(key_check)
def executor(data:dict):
    try:
        # if not isinstance(cache, CacheInterface):
        #     raise HTTPException(status_code=500, detail="Cache service not available")
        logger.info(f"from image_generator:{data}")
    except HTTPException as e:
        logger.error(f"HTTP Exception:{e}")
        return JSONResponse(
            status_code=e.status_code,
            content=jsonable_encoder(ErrorResponse(status=e.status_code,message=e.detail))
        )
    except Exception as e:
        logger.error(f"Unexpected Error:{e}")
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(ErrorResponse(status=500,message="Internal Server Error"))
        )

