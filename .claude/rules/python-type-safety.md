---
paths:
  - "**/*.py"
---

# Python Type Safety Rules

## Import Rules

- **Prefer regular imports over `TYPE_CHECKING`**: Unless there is a circular import issue, use regular imports instead of `if TYPE_CHECKING:` blocks. This keeps the code simpler and more straightforward.

## Avoid Dynamic Attribute Access

When type information is available, avoid dynamic attribute checking:

### Prohibited Patterns

- **`hasattr(obj, "attr")`** - Use static type checking instead
- **`getattr(obj, "attr", default)`** - Access attributes directly

### Why Avoid These

1. They bypass static type checking
2. They hide potential bugs that type checkers would catch
3. If type hints define an attribute, it should always exist

### Correct Patterns

```python
# ❌ WRONG - dynamic check
if hasattr(self, "_cache"):
    self._cache.clear()

# ✅ CORRECT - attribute is defined in type hints
self._cache.clear()

# ❌ WRONG - getattr with default
value = getattr(self._config, "timeout", 3.0)

# ✅ CORRECT - direct access
value = self._config.timeout
```

### When Dynamic Access is Acceptable

- Working with truly dynamic data (e.g., parsing unknown JSON)
- Interacting with untyped third-party libraries
- In such cases, add a comment: `# dynamic access required: <reason>`

## Avoid Unsafe Types

The following types that lose type information should NOT be used:

### Prohibited Types

- **`Any`** - Completely bypasses type checking
- **`object`** - Too broad, loses specific type information
- **`Dict` without type parameters** - Use `Dict[KeyType, ValueType]`
- **`List` without type parameters** - Use `List[ElementType]`
- **`Tuple` without type parameters** - Use `Tuple[Type1, Type2, ...]`
- **`Set` without type parameters** - Use `Set[ElementType]`
- **`Callable` without signature** - Use `Callable[[ArgTypes], ReturnType]`

### Alternatives to `Any`

Instead of using `Any`, consider these alternatives:

1. **Generic type variables**: Use `TypeVar` for flexible but type-safe code
   ```python
   T = TypeVar("T")
   def process(item: T) -> T:
       return item
   ```

2. **Union types**: When a value can be one of several known types
   ```python
   def handle(value: str | int | None) -> str:
       ...
   ```

3. **Protocol**: For structural typing (duck typing with type safety)
   ```python
   class Renderable(Protocol):
       def render(self) -> str: ...
   ```

4. **Specific base classes**: Use the most specific common ancestor

### When `Any` is Unavoidable

If `Any` is absolutely necessary (e.g., third-party library compatibility):

1. Add a comment explaining why: `# Any required: <reason>`
2. Isolate the `Any` usage to a small scope
3. Cast to a specific type as soon as possible

### Type Checking

- Run `basedpyright`, `flake8`, and `ruff` before committing
- Target: 0 type errors
