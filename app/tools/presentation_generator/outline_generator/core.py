from app.utils.document_loaders import get_docs
from app.tools.presentation_generator.outline_generator.tools import OutlineGenerator
from app.services.schemas import PresentationGeneratorArgs
from app.services.logger import setup_logger
from app.api.error_utilities import LoaderError, ToolExecutorError

logger = setup_logger()

def executor(grade_level: str,
             n_slides: int,
             topic: str,
             objectives: str,
             file_url: str,
             file_type: str,
             lang: str, 
             verbose=False):

    try:
        docs = None

        def fetch_docs(file_url, file_type):
            return get_docs(file_url, file_type, True) if file_url and file_type else None
        if file_url:
            docs = fetch_docs(file_type=file_type, file_url=file_url)   

        presentation_generator_args = PresentationGeneratorArgs(
            grade_level=grade_level,
            n_slides=n_slides,
            topic=topic,
            objectives=objectives,
            file_type=file_type,
            file_url=file_url,
            lang=lang
        )

        output = OutlineGenerator(args=presentation_generator_args, verbose=verbose).compile(docs)

        logger.info(f"Presentation generated successfully")

    except LoaderError as e:
        error_message = e
        logger.error(f"Error in Presentation Generator Pipeline -> {error_message}")
        raise ToolExecutorError(error_message)

    except Exception as e:
        error_message = f"Error in executor: {e}"
        logger.error(error_message)
        raise ValueError(error_message)

    return output