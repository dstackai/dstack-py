import typing as ty
from abc import ABC, abstractmethod
from uuid import uuid4


class ValidationError(ValueError):
    def __init__(self, error: Exception, id: str):
        self.error = error
        self.id = id

    def __str__(self):
        return str(self.error)


class UpdateError(RuntimeError):
    def __init__(self, error: Exception, id: str):
        self.error = error
        self.id = id

    def __str__(self):
        return str(self.error)


T = ty.TypeVar("T")


class Validator(ABC, ty.Generic[T]):
    def __init__(self):
        self._id: ty.Optional[str] = None

    def bind(self, control: 'Control'):
        self._id = control.get_id()

    @abstractmethod
    def validate(self, value: str) -> T:
        pass


class FunctionalValidator(Validator):
    def __init__(self, func: ty.Callable[[str], T]):
        super().__init__()
        self._func = func

    def validate(self, value: str) -> T:
        try:
            return self._func(value)
        except Exception as cause:
            raise ValidationError(cause, self._id)


class View(ABC):
    def __init__(self, id: str, enabled: bool, label: ty.Optional[str]):
        self.id = id
        self.enabled = enabled
        self.label = label

    def pack(self) -> ty.Dict:
        result = {"id": self.id, "enabled": self.enabled, "label": self.label, "type": self.__class__.__name__}
        result.update(self._pack())
        return result

    @abstractmethod
    def _pack(self) -> ty.Dict:
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"


V = ty.TypeVar("V", bound=View)


class Control(ABC, ty.Generic[V]):
    def __init__(self,
                 label: ty.Optional[str],
                 id: ty.Optional[str],
                 parents: ty.Optional[ty.Union[ty.List['Control'], 'Control']],
                 update_func: ty.Optional[ty.Callable[['Control', ty.List['Control']], None]]
                 ):
        self.label = label
        self.enabled = True

        self._id = id or str(uuid4())
        self._parents = parents or []
        self._children = []
        self._update_func = update_func
        self._pending_view: ty.Optional[V] = None
        self._dirty = True

        if not isinstance(self._parents, list):
            self._parents = [self._parents]

        for p in self._parents:
            p._children.append(self)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self._id})"

    def get_id(self):
        return self._id

    def _update(self):
        if self._pending_view:
            self._apply(self._pending_view)
            self._pending_view = None
            self._dirty = True

        if self._update_func:
            for p in self._parents:
                p._update()

            if self._dirty:
                try:
                    self._update_func(self, self._parents)
                    self._dirty = False
                except Exception as e:
                    raise UpdateError(e, self._id)

    def is_dependent(self) -> bool:
        return len(self._parents) > 0

    @abstractmethod
    def is_finite_state(self) -> bool:
        pass

    def view(self) -> V:
        self._update()
        return self._view()

    def apply(self, view: V):
        self._validate(view)
        self._pending_view = view

    def value(self) -> ty.Any:
        self._update()
        return self._value()

    def _validate(self, view: V):
        pass

    @abstractmethod
    def _view(self) -> V:
        pass

    @abstractmethod
    def _apply(self, view: V):
        pass

    @abstractmethod
    def _value(self) -> ty.Optional[ty.Any]:
        pass


class TextFieldView(View):
    def __init__(self, id: str, enabled: bool, label: ty.Optional[str], data: ty.Optional[str]):
        super().__init__(id, enabled, label)
        self.data = data

    def _pack(self) -> ty.Dict:
        return {"data": self.data}


class TextField(Control[TextFieldView], ty.Generic[T]):
    def __init__(self,
                 data: ty.Optional[str] = None,
                 label: ty.Optional[str] = None,
                 id: ty.Optional[str] = None,
                 parents: ty.Optional[ty.Union[ty.List[Control], Control]] = None,
                 update_func: ty.Optional[ty.Callable[[Control, ty.List[Control]], None]] = None,
                 validator: ty.Optional[Validator[T]] = None
                 ):
        super().__init__(label, id, parents, update_func)
        self.data = data
        self._validator = validator
        self._validated_value = None

        if self._validator:
            self._validator.bind(self)

    def is_finite_state(self) -> bool:
        return False

    def _view(self) -> TextFieldView:
        return TextFieldView(self._id, self.enabled, self.label, self.data)

    def _apply(self, view: TextFieldView):
        assert isinstance(view, TextFieldView)
        assert self._id == view.id
        self.data = view.data

    def _validate(self, view: TextFieldView):
        if self._validator:
            self._validated_value = self._validator.validate(view.data)

    def _value(self) -> ty.Optional[ty.Any]:
        return self._validated_value or self.data


class ListModel(ABC, ty.Generic[T]):
    @abstractmethod
    def apply(self, data: T):
        pass

    @abstractmethod
    def size(self) -> int:
        pass

    @abstractmethod
    def element(self, index: int) -> ty.Any:
        pass

    @abstractmethod
    def title(self, index: int) -> str:
        pass

    def titles(self) -> ty.List[str]:
        result = []

        for i in range(0, self.size()):
            result.append(self.title(i))

        return result


class DefaultListModel(ListModel[ty.List[ty.Any]]):
    def __init__(self):
        self.data: ty.Optional[ty.List[ty.Any]] = None

    def apply(self, data: ty.List[ty.Any]):
        self.data = data

    def size(self) -> int:
        return len(self.data)

    def element(self, index: int) -> ty.Any:
        return self.data[index]

    def title(self, index: int) -> str:
        return str(self.data[index])


class CallableListModel(ListModel[ty.Callable[[], ty.List[ty.Any]]]):
    def __init__(self):
        self.data: ty.Optional[ty.List[ty.Any]] = None

    def apply(self, data: ty.Callable[[], ty.List[ty.Any]]):
        self.data = data()

    def size(self) -> int:
        return len(self.data)

    def element(self, index: int) -> ty.Any:
        return self.data[index]

    def title(self, index: int) -> str:
        return str(self.data[index])


class ComboBoxView(View):
    def __init__(self, id: str, enabled: bool, label: ty.Optional[str],
                 selected: int, titles: ty.Optional[ty.List[str]] = None):
        super().__init__(id, enabled, label)
        self.titles = titles
        self.selected = selected

    def _pack(self) -> ty.Dict:
        return {"titles": self.titles, "selected": self.selected}


class ComboBox(Control[ComboBoxView], ty.Generic[T]):
    def __init__(self,
                 data: ty.Optional[T] = None,
                 model: ty.Optional[ListModel[T]] = None,
                 selected: int = 0,
                 label: ty.Optional[str] = None,
                 id: ty.Optional[str] = None,
                 parents: ty.Optional[ty.Union[ty.List[Control], Control]] = None,
                 update_func: ty.Optional[ty.Callable[[Control, ty.List[Control]], None]] = None
                 ):
        super().__init__(label, id, parents, update_func)
        self.data = data
        self._model = model
        self.selected = selected

    def is_finite_state(self) -> bool:
        return True

    @staticmethod
    def _derive_model(data: ty.Any) -> ListModel[ty.Any]:
        if isinstance(data, list):
            return DefaultListModel()
        elif isinstance(data, ty.Callable):
            return CallableListModel()
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    def get_model(self) -> ListModel[T]:
        model = self._model or self._derive_model(self.data)
        model.apply(self.data)
        return model

    def _view(self) -> ComboBoxView:
        model = self.get_model()
        return ComboBoxView(self._id, self.enabled, self.label, self.selected, model.titles())

    def _apply(self, view: ComboBoxView):
        assert isinstance(view, ComboBoxView)
        assert self._id == view.id
        self.selected = view.selected

    def _value(self) -> ty.Optional[ty.Any]:
        model = self.get_model()
        return model.element(self.selected) if self.selected >= 0 else None


class SliderView(View):
    def __init__(self, id: str, enabled: bool, label: ty.Optional[str],
                 selected: int = 0, data: ty.Optional[ty.List[float]] = None):
        super().__init__(id, enabled, label)
        self.data = data
        self.selected = selected

    def _pack(self) -> ty.Dict:
        return {"data": self.data, "selected": self.selected}


class Slider(Control[SliderView]):
    def __init__(self,
                 data: ty.Iterable[float],
                 selected: int = 0,
                 label: ty.Optional[str] = None,
                 id: ty.Optional[str] = None,
                 parents: ty.Optional[ty.Union[ty.List[Control], Control]] = None,
                 update_func: ty.Optional[ty.Callable[[Control, ty.List[Control]], None]] = None
                 ):
        super().__init__(label, id, parents, update_func)
        self.data = list(data)
        self.selected = selected

    def is_finite_state(self) -> bool:
        return True

    def _view(self) -> SliderView:
        return SliderView(self.get_id(), self.enabled, self.label, self.selected, self.data)

    def _apply(self, view: SliderView):
        assert isinstance(view, SliderView)
        assert self._id == view.id
        self.selected = view.selected

    def _value(self) -> ty.Any:
        return self.data[self.selected]


class FileUploadView(View):
    def __init__(self, id: str, enabled: bool, label: ty.Optional[str], is_text: bool, stream: ty.Optional[ty.IO]):
        super().__init__(id, enabled, label)
        self.is_text = is_text
        self.stream = stream

    def _pack(self) -> ty.Dict:
        return {"is_text": self.is_text}


class FileUpload(Control[FileUploadView]):
    def __init__(self,
                 is_text: bool = True,
                 label: ty.Optional[str] = None,
                 id: ty.Optional[str] = None,
                 parents: ty.Optional[ty.Union[ty.List[Control], Control]] = None,
                 update_func: ty.Optional[ty.Callable[[Control, ty.List[Control]], None]] = None
                 ):
        super().__init__(label, id, parents, update_func)
        self.is_text = is_text
        self.stream: ty.Optional[ty.IO] = None

    def is_finite_state(self) -> bool:
        return False

    def _view(self) -> FileUploadView:
        return FileUploadView(self.get_id(), self.enabled, self.label, self.is_text, None)

    def _apply(self, view: FileUploadView):
        assert isinstance(view, FileUploadView)
        assert self._id == view.id
        self.is_text = view.is_text
        self.stream = view.stream

    def _value(self) -> ty.Optional[ty.Any]:
        return self.stream


class ApplyView(View):
    def _pack(self) -> ty.Dict:
        return {}


class Apply(Control[ApplyView]):
    def __init__(self, label: ty.Optional[str] = None, id: ty.Optional[str] = None):
        super().__init__(label, id, None, None)
        self.controller: ty.Optional[Controller] = None

    def is_finite_state(self) -> bool:
        return True

    def _view(self) -> ApplyView:
        enabled = True

        for control in self.controller.map.values():
            if control._id != self.get_id() and control.value() is None:
                enabled = False
                break

        return ApplyView(self.get_id(), enabled, self.label)

    def _apply(self, view: ApplyView):
        assert isinstance(view, ApplyView)
        assert self._id == view.id

    def _value(self) -> ty.Optional[ty.Any]:
        return None


class Controller(object):
    def __init__(self, controls: ty.List[Control]):
        self.map: ty.Dict[str, Control] = {}

        require_apply = False
        has_apply = False

        for control in controls:
            if control.is_dependent() or not control.is_finite_state():
                require_apply = True

            if isinstance(control, Apply):
                if not has_apply:
                    has_apply = True
                    control.controller = self
                else:
                    raise ValueError("Apply must appear only once")

            self.map[control.get_id()] = control

        if require_apply and not has_apply:
            apply = Apply()
            apply.controller = self
            self.map[apply.get_id()] = apply

    def list(self, views: ty.Optional[ty.List[View]] = None) -> ty.List[View]:
        views = views or []

        for view in views:
            self.map[view.id].apply(view)

        return [c.view() for c in self.map.values()]
