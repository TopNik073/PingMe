import enum


class AuthProvidersEnum(str, enum.Enum):
    MANUAL = "manual"
    GOOGLE = "google"
