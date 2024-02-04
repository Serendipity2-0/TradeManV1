from loguru import logger
import sys

logger.add("file_2.log",level="TRACE", rotation="00:00",enqueue=True,backtrace=True, diagnose=True)




def read_common_error_folder():
    pass

#Process the error and display

def process_error():
    pass

logger.debug("That's it, beautiful and simple logging!")
