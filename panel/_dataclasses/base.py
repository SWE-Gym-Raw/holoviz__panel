"""
Shared base classes and utilities for working with dataclasses like
models including ipywidgets and Pydantic.
"""
from inspect import isclass
from typing import Any, Iterable

import param

from param import Parameterized, bind


def _to_tuple(
    bases: None | Parameterized | Iterable[Parameterized],
) -> tuple[Parameterized]:
    if not bases:
        bases = ()
    if isclass(bases) and issubclass(bases, Parameterized):
        bases = (bases,)
    return tuple(bases)


class ModelUtils:
    """An abstract base class"""
    can_observe_field: bool = False

    supports_constant_fields = True

    _model_cache: dict[Any, Parameterized] = {}

    @classmethod
    def get_public_and_relevant_field_names(cls, model) -> tuple[str]:
        return tuple(
            name
            for name in cls.get_field_names(model)
            if cls.is_relevant_field_name(name)
        )

    @classmethod
    def ensure_dict(cls, names: Iterable[str] | dict[str, str] = ()) -> dict[str, str]:
        if isinstance(names, dict):
            return names
        return dict(zip(names, names))

    @classmethod
    def ensure_names_exists(
        cls, model, parameterized, names: dict[str, str]
    ) -> dict[str, str]:
        return {
            field: parameter
            for field, parameter in names.items()
            if field in cls.get_field_names(model) and parameter in parameterized.param
        }

    @classmethod
    def clean_names(
        cls, model, parameterized, names: Iterable[str] | dict[str, str]
    ) -> dict[str, str]:
        if isinstance(names, str):
            names=(names,)
        if not names:
            names = cls.get_public_and_relevant_field_names(model)
        names = cls.ensure_dict(names)
        return cls.ensure_names_exists(model, parameterized, names)

    @classmethod
    def get_field_names(cls, model) -> Iterable[str]:
        raise NotImplementedError()

    @classmethod
    def is_relevant_field_name(cls, name: str):
        if name.startswith("_"):
            return False
        return True

    @classmethod
    def sync_from_field_to_parameter(
        cls,
        model,
        field: str,
        parameterized: Parameterized,
        parameter: str,
    ):
        pass

    @classmethod
    def observe_field(
        cls,
        model,
        field: str,
        handle_change,
    ):
        raise NotImplementedError()

    @classmethod
    def create_parameterized(
        cls,
        model,
        names,
        bases,
    ):
        if not names:
            names = cls.get_public_and_relevant_field_names(model)
        names = cls.ensure_dict(names)

        bases = _to_tuple(bases)
        if not any(issubclass(base, Parameterized) for base in bases):
            bases += (Parameterized,)
        name = type(model).__name__
        key = (name, tuple(names.items()), bases)
        if name in cls._model_cache:
            parameterized = cls._model_cache[key]
        else:
            existing_params = ()
            for base in bases:
                if issubclass(base, Parameterized):
                    existing_params += tuple(base.param)
            params = {
                name: param.Parameter()
                for name in names.values()
                if name not in existing_params
            }
            parameterized = param.parameterized_class(name, params=params, bases=bases)
            parameterized._model__initialized = True
            cls._model_cache[key] = parameterized
        return parameterized

    @classmethod
    def sync_with_parameterized(
        cls,
        model,
        parameterized: Parameterized,
        names: Iterable[str] | dict[str, str] = (),
    ):
        names = cls.clean_names(model, parameterized, names)

        for field, parameter in names.items():
            model_field = getattr(model, field)
            parameterized_value = getattr(parameterized, parameter)
            if parameter != "name" and parameterized_value is not None:
                try:
                    setattr(model, field, parameterized_value)
                except Exception:
                    with param.edit_constant(parameterized):
                        setattr(parameterized, parameter, model_field)
            else:
                with param.edit_constant(parameterized):
                    setattr(parameterized, parameter, model_field)

            def _handle_field_change(
            _,
                model=model,
                field=field,
                parameterized=parameterized,
                parameter=parameter,
            ):
                with param.edit_constant(parameterized):
                    setattr(parameterized, parameter, getattr(model, field))
            cls.observe_field(model, field, _handle_field_change)

            read_only_fields: set[str] = set()

            def _handle_parameter_change(
                _,
                model=model,
                field=field,
                parameter=parameter,
                read_only_fields=read_only_fields,
            ):
                if field not in read_only_fields:
                    try:
                        setattr(model, field, getattr(parameterized, parameter))
                    except Exception:
                        read_only_fields.add(field)


            bind(_handle_parameter_change, parameterized.param[parameter], watch=True)

    @classmethod
    def get_layout(cls, model, self, layout_params):
        raise NotImplementedError()

    @classmethod
    def adjust_sizing(cls, self):
        pass
