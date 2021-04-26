from typing import Callable


def _dynamic_getter(key: str):
	def getter(self):
		return self[key]

	return getter

def _dynamic_setter(key: str):
	def setter(self, value):
		self[key] = value
	
	return setter

def _dynamic_deleter(key: str):
	def deleter(self):
		del self[key]
	
	return deleter

class _JsonProperty(property):
	def __init__(self, key: str, init: Callable, getter: Callable, setter: Callable, deleter: Callable):
		super().__init__(getter, setter, deleter)
		self.key = key
		self.init = init

def json_basic(key: str, init: Callable) -> property:
	return _JsonProperty(key, init, _dynamic_getter(key), _dynamic_setter(key), _dynamic_deleter(key))

def json_list(key: str, init: Callable) -> property:
	list_init = lambda list_val: [init(v) for v in list_val]

	return _JsonProperty(key, list_init, _dynamic_getter(key), _dynamic_setter(key), _dynamic_deleter(key))

def json_dict(key: str, init: Callable) -> property:
	dict_init = lambda dict_val: { k: init(v) for k, v in dict_val.items() }

	return _JsonProperty(key, dict_init, _dynamic_getter(key), _dynamic_setter(key), _dynamic_deleter(key))