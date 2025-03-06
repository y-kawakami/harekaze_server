import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Basic認証のためのユーティリティ関数
    """
    correct_username = secrets.compare_digest(
        credentials.username, os.getenv("SWAGGER_USERNAME", "harekaze"))
    correct_password = secrets.compare_digest(
        credentials.password, os.getenv("SWAGGER_PASSWORD", "hrkz2025"))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
