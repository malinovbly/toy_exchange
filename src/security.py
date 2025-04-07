from fastapi.security.api_key import APIKeyHeader


# Схема безопасности — для кнопки "Authorize"
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)
