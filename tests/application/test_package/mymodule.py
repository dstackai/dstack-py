import dstack.controls as ctrl
import dstack as ds


def bar():
    print("Here is bar!")


def foo():
    bar()
    print("Here is foo!")


def test_app(x: ctrl.TextField, y: ctrl.TextField):
    foo()
    print(f"My app: x={x.value()} y={y.value()}")
