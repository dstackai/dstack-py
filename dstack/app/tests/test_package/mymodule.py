from dstack.app import depends


@depends(requirements="dstack/app/tests/test_requirements.txt")
@depends("pandas", "PyYAML==5.3.1")
# @depends("dstack.app.tests.test_package")
# @depends("dstack.app.tests.test_package.test_subpackage1")
# @depends("dstack.app.tests.test_package.test_subpackage2")
def test_app(x: int, y: int):
    pass