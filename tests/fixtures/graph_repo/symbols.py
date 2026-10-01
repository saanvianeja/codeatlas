"""Symbol extraction fixture."""


def module_fn(x, y):
    """A module-level function."""

    def nested_should_not_appear():
        return x + y

    return nested_should_not_appear()


async def module_async(name: str):
    """An async module-level function."""
    return name


class Greeter:
    """A class with methods."""

    def greet(self, who):
        """Instance method."""
        return f"hello {who}"

    async def agreet(self):
        return "async hello"


class Outer:
    class Inner:
        def inner_method(self):
            return 1
