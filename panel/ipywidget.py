"""Functionality to enable easily interacting with ipywidgets via familiar APIs like pn.bind,
@pn.depends and pn.rx"""

from typing import TYPE_CHECKING, Iterable

import param

from param import Parameterized
from param.reactive import bind

from .pane import IPyWidget
from .viewable import Layoutable, Viewer

if TYPE_CHECKING:
    try:
        from traitlets import HasTraits
    except ModuleNotFoundError:

        class HasTraits:  # type: ignore
            """Mock class"""

else:

    class HasTraits:  # type: ignore
        """Mock class"""


def _is_custom_trait(name):
    if name.startswith("_"):
        return False
    if name in {"comm", "tabbable", "keys", "log", "layout"}:
        return False
    return True


def _get_parameter_names(widget):
    return [name for name in widget.traits() if _is_custom_trait(name)]


def sync_parameterized(
    widget: HasTraits, parameters: Iterable, parameterized: Parameterized
):
    for parameter in parameters:
        # Observe widget parameters
        def _handle_widget_change(_, widget=widget, parameter=parameter):
            setattr(parameterized, parameter, getattr(widget, parameter))

        widget.observe(_handle_widget_change, names=parameter)

        # Bind to parameterized parameters
        def _handle_observer_change(_, widget=widget, parameter=parameter):
            setattr(widget, parameter, getattr(parameterized, parameter))

        bind(_handle_observer_change, parameterized.param[parameter], watch=True)


class IpyWidgetParameterized(Parameterized):
    _widget = param.Parameter(allow_None=False)
    _parameters = param.List(allow_None=False)

    def __init__(self, **params):
        super().__init__(**params)
        parameters = self._parameters
        widget = self._widget
        if not parameters:
            parameters = _get_parameter_names(widget)

        # Add parameters
        with param.edit_constant(self):
            for parameter in parameters:
                if parameter not in self.param:
                    self.param.add_parameter(parameter, param.Parameter())
                setattr(self, parameter, getattr(widget, parameter))

            sync_parameterized(widget, parameters, self)


_ipywidget_classes = {}


def to_parameterized(
    widget: HasTraits,
    parameters: Iterable | None = None,
    bases: Parameterized | None = None,
    **kwargs,
) -> Parameterized:
    """Returns a Parameterized object with parameters synced to the ipywidget widget parameters

    Args:
        widget (HasTraits): The ipywidget to create the Viewer from.
        parameters (Iterable | None): The parameters to add to the Parameterized and to sync.
            If no parameters are specified all public parameters on the widget will be added
            and synced.
    """
    if not parameters:
        parameters = _get_parameter_names(widget)
    if bases:
        bases = (
            bases,
            IpyWidgetParameterized,
        )
    else:
        bases = (IpyWidgetParameterized,)
    name = type(widget).__name__
    key = (name, tuple(parameters), bases)
    if name in _ipywidget_classes:
        parameterized = _ipywidget_classes[key]
    else:
        existing_params = set(IpyWidgetParameterized.param)
        params = {
            name: param.Parameterized()
            for name in parameters
            if name not in existing_params
        }
        parameterized = param.parameterized_class(name, params=params, bases=bases)
    _ipywidget_classes[key] = parameterized
    return parameterized(_widget=widget, _parameters=parameters, **kwargs)


class IpyWidgetViewer(Layoutable, Viewer):

    def __init__(self, **params):
        super().__init__(**params)

        widget = self._widget
        widget.height = "100%"
        widget.width = "100%"
        layout_params = {name: self.param[name] for name in Layoutable.param}

        self._layout = IPyWidget(widget, **layout_params)

    def __panel__(self):
        return self._layout


def to_viewer(
    widget: HasTraits,
    parameters: Iterable | None = None,
    bases: Parameterized | None = None,
    **kwargs,
) -> Viewer:
    """Returns a Parameterized object with parameters synced to the ipywidget widget parameters

    Args:
        widget (HasTraits): The ipywidget to create the Viewer from.
        parameters (Iterable | None): The parameters to add to the Parameterized and to sync.
            If no parameters are specified all public parameters on the widget will be added
            and synced.
    """
    return to_parameterized(
        widget, parameters=parameters, bases=IpyWidgetViewer, **kwargs
    )


def sync_rx(element: HasTraits, name: str, target: param.rx):
    """Syncs the ipywidget element.name to the reactive target.rx.value"""
    target.rx.value = getattr(element, name)

    def set_value(event, target=target):
        target.rx.value = event["new"]

    element.observe(set_value, names=name)

    def set_name(value, element=element, name=name):
        setattr(element, name, value)

    target.rx.watch(set_name)


def to_rx(widget: HasTraits, parameters: Iterable) -> tuple[param.rx]:
    """Returns a tuple of `rx` parameters. Each one synced to a parameter of the ipywidget widget.

    Args:
        widget (HasTraits): The ipywidget to create the `rx` parameters from.
        parameters (Iterable): The parameters to create `rx` parameters from and to sync.
            If no parameters are specified all parameters on the widget will be added
            and synced.
    """
    rx_values = []
    for name in parameters:
        rx = param.rx()
        sync_rx(widget, name, rx)
        rx_values.append(rx)
    return tuple(rx_values)
