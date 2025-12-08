import enum


class MailingMethods(str, enum.Enum):
    EMAIL = 'email'
    SMS = 'sms'
