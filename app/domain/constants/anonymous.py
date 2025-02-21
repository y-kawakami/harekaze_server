from typing import Optional

ANONYMOUS_LABEL = 'Anonymous'
# ANONYMOUS_DISPLAY_NAME = '匿名'
ANONYMOUS_DISPLAY_NAME = None


def filter_anonymous(nickname: str) -> Optional[str]:
    return ANONYMOUS_DISPLAY_NAME if nickname == ANONYMOUS_LABEL else nickname
