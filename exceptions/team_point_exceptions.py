from discord.app_commands import AppCommandError

class BaseTeamPointError(AppCommandError):
    """Base exception for Team Point related errors."""
    pass

class TeamPointError(BaseTeamPointError):
    """Generic Team Point error."""
    
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

class SameChannelException(TeamPointError):
    details = "The specified channel is the same as the current one"
    message = "指定的頻道與目前設定的頻道相同，請選擇不同的頻道。"

class MessageForbiddenException(TeamPointError):
    details = "Message forbidden in the specified channel"
    message = "無法在指定的頻道發送或編輯訊息。請確認機器人是否具有適當的權限。"

class MessageNotFoundException(TeamPointError):
    details = "Team point message not found"
    message = "找不到團隊積分訊息。請確認訊息是否已被刪除，或重新設定團隊積分訊息的位置。"

class NoTeamPointMessageSetException(TeamPointError):
    details = "No team point message has been set"
    message = "尚未設定團隊積分訊息的位置。請使用 /設定團隊積分訊息 指令來設定。"

class ChannelNotFoundException(TeamPointError):
    details = "Specified channel not found"
    message = "找不到指定的頻道。請確認頻道ID是否正確，或該頻道是否存在。"