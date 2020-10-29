from dstack.app.controls import FunctionalValidator, Validator


def int_validator() -> Validator[int]:
    return FunctionalValidator(func=lambda x: int(x))
