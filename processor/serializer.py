from typing import Any
from dataclasses import fields


class Serializer:
    def __init__(self) -> None:
        pass
    
    def _convert_nested_attr(
        self, 
        value: Any, 
        visited: set
    ) -> Any:
        """_convert_nested_attr Converts attributes of a class/dataclass

        This is a ridiculous method to convert every attribute of a class
        or dataclass into a JSON-serializable type, usually string or dictionary.
        
        This is primarily used by the benchmarking features as this requires
        the state of a class to be captured and saved in a file.

        Args:
            value (Any): Class / Dataclass instance
            visited (set): Set of visited values

        Returns:
            Any: Could be a string, list or dictionary
        """
        if id(value) in visited:
            return "<circular reference detected>"
        visited.add(id(value))
        
        if hasattr(value, "__dataclass_fields__"):
            return self.dataclass_to_dict(value, visited)
        elif hasattr(value, "__dict__"):
            return self.class_to_dict(value, visited)
        elif isinstance(value, list):
            return [self._convert_nested_attr(v, visited) for v in value]
        elif isinstance(value, dict):
            return {k: self._convert_nested_attr(v, visited) for k, v in value.items()}
        else:
            return str(value)
    
    def dataclass_to_dict(
        self, 
        instance: Any, 
        visited: set
    ) -> dict:
        """dataclass_to_dict Converts a dataclass

        This uses recursive methods to convert a dataclass
        into a dictionary which is able to be JSON-serialized

        Args:
            instance (Any): Dataclass instance
            visited (set): Set of visited values (classes, types etc.)

        Returns:
            dict: Dictionary containing variables and their values (variable_name: value)
        """
        obj = {}
        
        for field in fields(instance):
            attr = field.name
            value = getattr(instance, attr)
            obj[attr] = self._convert_nested_attr(value, visited)
        return obj
    
    def class_to_dict(
        self, 
        instance: Any, 
        visited: set
    ) -> dict:
        """class_to_dict Converts a class

        This uses recursive methods to convert a regular class
        into a dictionary which is able to be JSON-serialized

        Args:
            instance (Any): Class instance
            visited (set): Set of visited values (classes, types etc.)

        Returns:
            dict: Dictionary containing variables and their values (variable_name: value)
        """
        obj = {}
        
        for attr, value in instance.__dict__.items():
            obj[attr] = self._convert_nested_attr(value, visited)
        return obj
    
    def type_to_dict(
        self, 
        instance: Any
    ) -> Any:
        """type_to_dict Converts an instance

        This function converts a class/dataclass instance
        into a JSON-serializable object.
        
        For more info, check the individual methods.

        Args:
            instance (Any): (Data)class instance

        Returns:
            Any: JSON-serializable object (e.g. dictionary)
        """
        return self._convert_nested_attr(instance, visited=set())