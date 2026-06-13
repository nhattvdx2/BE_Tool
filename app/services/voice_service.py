from fastapi import HTTPException, status

from app.models.user import User
from app.services.auth_service import has_screen_access


def get_number_limit(user: User, screenid: str) -> int:
    if not has_screen_access(user, screenid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this screen",
        )

    screen = screenid.strip().lower()
    if screen in {"clone_voice", "voice_clone"}:
        return user.voice_clone.number_limit
    return user.voice_design.number_limit
