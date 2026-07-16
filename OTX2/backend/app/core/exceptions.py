from fastapi import HTTPException, status


class OTXClientError(Exception):
    pass


class OTXInvalidApiKeyError(OTXClientError):
    pass


class OTXNotFoundError(OTXClientError):
    pass


class OTXBadRequestError(OTXClientError):
    pass


def to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, OTXInvalidApiKeyError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTX API key.",
        )
    if isinstance(error, OTXNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    if isinstance(error, OTXBadRequestError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Failed to fetch data from OTX.",
    )
