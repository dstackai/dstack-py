from dstack.controls import *
from deprecation import deprecated
import typing as ty


@deprecated(details="Use dstack.controls.unpack_view instead")
def unpack_view(source: ty.Dict) -> View:
    type = source["type"]
    if type == "TextFieldView":
        return TextFieldView(source["id"], source.get("data"), source.get("enabled"), source.get("label"),
                             source.get("optional"))
    elif type == "ApplyView":
        return ApplyView(source["id"], source.get("enabled"), source.get("label"), source.get("optional"))
    elif type == "ComboBoxView":
        return ComboBoxView(source["id"], source.get("selected"), source.get("titles"), source.get("enabled"),
                            source.get("label"), source.get("optional"))
    elif type == "SliderView":
        return SliderView(source["id"], source.get("selected"), source.get("data"), source.get("enabled"),
                          source.get("label"))
    else:
        # TODO: Support FileUploadView
        raise AttributeError("Unsupported view: " + str(source))
