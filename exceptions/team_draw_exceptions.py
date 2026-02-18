from discord.app_commands import AppCommandError

class BaseTeamDrawError(AppCommandError):
    """Base exception for Team Draw related errors."""
    pass

class TeamDrawError(BaseTeamDrawError):
    """Generic Team Draw error."""
    
    details: str = "An error occurred"
    message: str = "發生錯誤。"
    user_error: bool = True

    def __init__(self, *, user_error: bool | None = None, details: str | None = None, message: str | None = None):
        payload = {
            "user_error": user_error if user_error is not None else self.user_error,
            "details": details or self.details,
            "message": message or self.message,
        }
        super().__init__(payload)

class InvalidDrawTimeFormatException(TeamDrawError):
    details = "Invalid draw time format"
    message = "抽選時間格式無效。請使用 YYYY-MM-DDTHH:MM:SS+08:00 格式。"

class DrawTimeInPastException(TeamDrawError):
    details = "Draw time is in the past"
    message = "抽選時間必須是未來的時間。"

class InvalidChannelException(TeamDrawError):
    details = "Invalid channel"
    message = "指定的頻道無效或無法存取。"