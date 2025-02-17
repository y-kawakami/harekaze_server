ANONYMOUS_LABEL = 'Anonymous'
ANONYMOUS_DISPLAY_NAME = '匿名'


def filter_anonymous(nickname: str) -> str:
    return ANONYMOUS_DISPLAY_NAME if nickname == ANONYMOUS_LABEL else nickname
