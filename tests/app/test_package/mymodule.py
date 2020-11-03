from dstack.app import depends


def bar():
    print("Here is bar!")


def foo():
    bar()
    print("Here is foo!")


@depends(requirements="tests/app/test_requirements.txt")
@depends("deprecation", "PyYAML==5.3.1")
@depends("tests.app.test_package")
def test_app(x: int, y: int):
    foo()
    print(f"My app: x={x} y={y}")
