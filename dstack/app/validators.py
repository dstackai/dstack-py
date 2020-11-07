from dstack.app.controls import FunctionalValidator, Validator


def int_validator() -> Validator[int]:
    return FunctionalValidator(func=lambda x: int(x), tpe="int")


def float_validator() -> Validator[float]:
    return FunctionalValidator(func=lambda x: float(x), tpe="float")
