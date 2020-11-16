import typing as ty
from unittest import TestCase

import dstack.application.controls as ctrl
from dstack import Application
from dstack.application.validators import int_validator


class TestControls(TestCase):
    @staticmethod
    def get_by_id(id: str, views: ty.List[ctrl.View]) -> ty.Optional[ctrl.View]:
        for view in views:
            if view.id == id:
                return view

        return None

    @staticmethod
    def get_apply(views: ty.List[ctrl.View]) -> ty.Optional[ctrl.View]:
        for view in views:
            if isinstance(view, ctrl.ApplyView):
                return view

        return None

    def test_simple_update(self):
        def update(control: ctrl.Control, text_field: ctrl.TextField):
            control.data = str(int(text_field.data) * 2)

        c1 = ctrl.TextField("10", id="c1")
        c2 = ctrl.TextField(id="c2", depends=c1, data=update)
        controller = ctrl.Controller([c1, c2])
        views = controller.list()
        self.assertEqual(3, len(views))  # Apply will appear here
        ids = [v.id for v in views]
        self.assertIn(c1.get_id(), ids)
        self.assertIn(c2.get_id(), ids)

        v1 = self.get_by_id(c1.get_id(), views)
        v2 = self.get_by_id(c2.get_id(), views)

        if isinstance(v1, ctrl.TextFieldView):
            self.assertEqual("10", v1.data)
        else:
            self.fail()

        if isinstance(v2, ctrl.TextFieldView):
            self.assertEqual("20", v2.data)
        else:
            self.fail()

        views = controller.list(views)
        v1 = self.get_by_id(c1.get_id(), views)
        v2 = self.get_by_id(c2.get_id(), views)

        if isinstance(v1, ctrl.TextFieldView):
            self.assertEqual("10", v1.data)
        else:
            self.fail()

        if isinstance(v2, ctrl.TextFieldView):
            self.assertEqual("20", v2.data)

    def test_validator(self):
        c = ctrl.TextField(id="c", validator=int_validator())
        c.apply(ctrl.TextFieldView(id=c.get_id(), enabled=True, data="10", label=None))

        try:
            c.apply(ctrl.TextFieldView(id=c.get_id(), enabled=True, data="ttt", label=None))
            self.fail()
        except ctrl.ValidationError as e:
            self.assertEqual(c.get_id(), e.id)

    def test_update_error(self):
        def update(control: ctrl.Control, text_area: ctrl.TextField):
            raise ValueError()

        c1 = ctrl.TextField("10", id="c1")
        c2 = ctrl.TextField(id="c2", depends=c1, data=update)

        controller = ctrl.Controller([c1, c2])

        try:
            controller.list(controller.list())
            self.fail()
        except ctrl.UpdateError as e:
            self.assertEqual(c2.get_id(), e.id)

    def test_update_func_called_only_once(self):
        count = 0

        def update_c2(control: ctrl.Control, text_area: ctrl.TextField):
            nonlocal count
            if count == 0:
                count += 1
            else:
                print(count)
                raise RuntimeError()

            control.data = str(int(text_area.data) * 2)

        def update_c3_c4(control: ctrl.Control, text_area: ctrl.TextField):
            control.data = str(int(text_area.data) * 2)

        c1 = ctrl.TextField("10", id="c1")
        c2 = ctrl.TextField(id="c2", depends=c1, data=update_c2)
        c3 = ctrl.TextField(id="c3", depends=c2, data=update_c3_c4)
        c4 = ctrl.TextField(id="c4", depends=c2, data=update_c3_c4)

        controller = ctrl.Controller([c1, c2, c3, c4])
        views = controller.list()
        self.assertEqual(1, count)
        v2 = ty.cast(ctrl.TextFieldView, self.get_by_id(c2.get_id(), views))
        v3 = ty.cast(ctrl.TextFieldView, self.get_by_id(c3.get_id(), views))
        v4 = ty.cast(ctrl.TextFieldView, self.get_by_id(c4.get_id(), views))

        self.assertEqual("20", v2.data)
        self.assertEqual("40", v3.data)
        self.assertEqual("40", v4.data)

    def test_combo_box(self):
        def update(control: ctrl.ComboBox, parent: ctrl.ComboBox):
            selected = parent.data[parent.selected]
            control.data = [f"{selected} 1", f"{selected} 2"]

        cb = ctrl.ComboBox(["Hello", "World"], id="cb")
        self.assertTrue(isinstance(cb._derive_model(), ctrl.DefaultListModel))

        c1 = ctrl.ComboBox(data=update, depends=cb, id="c1")
        controller = ctrl.Controller([c1, cb])
        views = controller.list()
        v = ty.cast(ctrl.ComboBoxView, self.get_by_id(cb.get_id(), views))
        v1 = ty.cast(ctrl.ComboBoxView, self.get_by_id(c1.get_id(), views))

        self.assertEqual(0, v.selected)
        self.assertEqual(["Hello 1", "Hello 2"], v1.titles)

        v.selected = 1
        print(views)
        views = controller.list(views)
        print(views)
        v = ty.cast(ctrl.ComboBoxView, self.get_by_id(cb.get_id(), views))
        v1 = ty.cast(ctrl.ComboBoxView, self.get_by_id(c1.get_id(), views))

        self.assertEqual(1, v.selected)
        self.assertEqual(["World 1", "World 2"], v1.titles)

    def test_combo_box_callable_model(self):
        class City:
            def __init__(self, id, title):
                self.id = id
                self.title = title

            def __repr__(self):
                return self.title

        class Country:
            def __init__(self, code, title):
                self.code = code
                self.title = title

            def __repr__(self):
                return self.title

        data = {"US": [City(0, "New York"), City(1, "San Francisco"), City(2, "Boston")],
                "DE": [City(10, "Munich"), City(11, "Berlin"), City(12, "Hamburg")]}

        def list_cities_from_db_by_code(country: Country) -> ty.List[City]:
            return data[country.code]

        def list_countries_from_db() -> ty.List[Country]:
            return [Country("US", "United States"), Country("DE", "German")]

        def update_cities(control: ctrl.ComboBox, parent: ctrl.ComboBox):
            country = ty.cast(Country, parent.get_model().element(parent.selected))
            control.data = list_cities_from_db_by_code(country)

        countries = ctrl.ComboBox(list_countries_from_db, id="countries")
        self.assertTrue(isinstance(countries._derive_model(), ctrl.CallableListModel))

        cities = ctrl.ComboBox(data=update_cities, id="cities", depends=countries)
        controller = ctrl.Controller([countries, cities])
        views = controller.list()
        v1 = ty.cast(ctrl.ComboBoxView, self.get_by_id(countries.get_id(), views))
        v2 = ty.cast(ctrl.ComboBoxView, self.get_by_id(cities.get_id(), views))

        self.assertEqual(["United States", "German"], v1.titles)
        self.assertEqual(0, v1.selected)
        self.assertEqual(["New York", "San Francisco", "Boston"], v2.titles)

        v1.selected = 1
        views = controller.list(views)

        v1 = ty.cast(ctrl.ComboBoxView, self.get_by_id(countries.get_id(), views))
        v2 = ty.cast(ctrl.ComboBoxView, self.get_by_id(cities.get_id(), views))
        self.assertEqual(1, v1.selected)
        self.assertEqual(["Munich", "Berlin", "Hamburg"], v2.titles)

    def test_apply_button_enabled(self):
        c1 = ctrl.TextField(None, id="c1")
        controller = ctrl.Controller([c1])
        self.assertEqual(2, len(controller.list()))
        apply_view = self.get_apply(controller.list())
        self.assertIsNotNone(apply_view)
        self.assertFalse(apply_view.enabled)

        c1.apply(ctrl.TextFieldView(c1.get_id(), data="10", enabled=True))
        apply_view = self.get_apply(controller.list())
        self.assertTrue(apply_view.enabled)

    def test_controller_apply(self):
        def update(control, text_field):
            control.data = str(int(text_field.data) * 2)

        def test(x: ctrl.Control, y: ctrl.Control):
            return int(x.value()) + int(y.value())

        c1 = ctrl.TextField("10", id="c1", validator=int_validator())
        c2 = ctrl.TextField(id="c2", depends=c1, data=update, validator=int_validator())
        controller = ctrl.Controller([c1, c2])
        views = controller.list()
        # print(views)
        app = Application(test, x=c1, y=c2, project=True)
        self.assertEqual(30, controller.apply(app.function, views))

    def test_title_override(self):
        class Item:
            def __init__(self, id, title):
                self.id = id
                self.title = title

            def __repr__(self):
                return self.title

        items = ctrl.ComboBox([Item(1, "hello"), Item(2, "world")], title=lambda x: x.title.upper())
        controller = ctrl.Controller([items])
        views = controller.list()
        items_view = ty.cast(ctrl.ComboBoxView, views[0])
        self.assertEqual(["HELLO", "WORLD"], items_view.titles)

    def test_optional(self):
        c1 = ctrl.TextField(None, id="c1", optional=True)
        controller = ctrl.Controller([c1])
        self.assertEqual(2, len(controller.list()))
        apply_view = self.get_apply(controller.list())
        c1_view = self.get_by_id("c1", controller.list())
        self.assertIsNotNone(apply_view)
        self.assertTrue(apply_view.enabled)
        self.assertFalse(apply_view.optional)
        self.assertTrue(c1_view.optional)

    def test_pack(self):
        c1 = ctrl.TextField(None, id="c1", label="my text", optional=True)
        v1 = c1.view()
        p1 = v1.pack()

        self.assertEqual("c1", p1["id"])
        self.assertEqual(None, p1["data"])
        self.assertTrue(p1["enabled"])
        self.assertTrue(p1["optional"])
        self.assertEqual("my text", p1["label"])
        self.assertEqual(v1.__class__.__name__, p1["type"])

        c2 = ctrl.TextField("10", id="c1")
        p2 = c2.view().pack()
        self.assertFalse(p2["optional"])
        self.assertEqual("10", p2["data"])

        c3 = ctrl.ComboBox(["Hello", "World"], id="c3")
        p3 = c3.view().pack()
        self.assertEqual(0, p3["selected"])
        self.assertFalse(p3["optional"])
        self.assertEqual(["Hello", "World"], p3["titles"])

        c4 = ctrl.FileUpload(is_text=True, id="c4")
        p4 = c4.view().pack()
        self.assertTrue(p4["is_text"])

        c5 = ctrl.Slider(range(0, 10), id="c5", selected=3)
        p5 = c5.view().pack()
        self.assertEqual(list(range(0, 10)), p5["data"])
        self.assertEqual(3, p5["selected"])