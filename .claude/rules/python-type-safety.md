# Python Type Safety Rules

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

- Run `basedpyright` before committing
- Use `/check-types` command to verify type annotations
- Target: 0 type errors
