import dstack.controls as ctrl
import dstack as ds


def bar():
    print("Here is bar!")


def foo():
    bar()
    print("Here is foo!")


def update(control: ctrl.TextField, text_field: ctrl.TextField):
    control.data = str(int(text_field.data) * 2)


c1 = ctrl.TextField("10", id="c1")
c2 = ctrl.TextField(id="c2", depends=c1, data=update)


@ds.app(x=c1, y=c2, requirements="tests/application/test_requirements.txt",
        depends=["deprecation", "PyYAML==5.3.1", "tests.application.test_package"])
def test_app(x: ctrl.TextField, y: ctrl.TextField):
    foo()
    print(f"My app: x={x.value()} y={y.value()}")
