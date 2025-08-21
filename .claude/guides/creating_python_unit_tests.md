## Testing Framework

Use pytest as the primary testing framework. All tests should be placed in the `tests/` directory with a structure that
mirrors the source code.

## Test File Naming

- Test files should be named `test_<module_name>.py`
- Test functions should be named `test_<what_is_being_tested>_<expected_outcome>`
- Tests should be organized in a way that reflects the structure of the codebase, using subdirectories as needed.
- Tests should be placed in the relevant subdirectory of the `tests/` directory, mirroring the structure of the source
  code.

## Core Testing Principles

### 1. Arrange-Act-Assert (AAA) Pattern

Structure each test with clear sections (don't use comments, just follow the pattern):

```python
def test_user_creation():
    # Arrange - Set up test data
    name = "John Doe"
    email = "john@example.com"

    # Act - Execute the code being tested
    user = User(name=name, email=email)

    # Assert - Verify the expected outcome
    assert user.name == name
    assert user.email == email
```

### 2. Test Independence

Each test must be independent and not rely on other tests or shared state.

### 3. Single Responsibility

Each test should verify one specific behavior or edge case.

## Essential Test Coverage

### 1. Happy Path Tests

Test the normal, expected behavior with valid inputs.

### 2. Edge Cases

- Empty inputs (empty strings, empty lists, None values)
- Boundary values (0, -1, maximum values)
- Special characters and Unicode
- Large inputs

### 3. Error Cases

- Invalid inputs that should raise exceptions
- Network failures and timeouts
- Database connection errors
- File system errors

### 4. Integration Points

- Mock external dependencies (APIs, databases, file systems)
- Test both successful and failed external calls

## Pytest Patterns

### 1. Fixtures

Use fixtures for common test setup:

```python
@pytest.fixture
def sample_user():
    return User(id="123", name="Test User", email="test@example.com")


@pytest.fixture
def mock_database(mocker):
    db = mocker.Mock()
    db.execute.return_value = []
    return db
```

### 2. Parametrized Tests

Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("input_value,expected", [
    (0, 0),
    (1, 1),
    (-1, 1),
    (100, 10000),
])
def test_square_function(input_value, expected):
    assert square(input_value) == expected
```

### 3. Exception Testing

```python
def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)


def test_invalid_user_id():
    with pytest.raises(UserNotFoundError, match="User .* not found"):
        get_user("invalid_id")
```

### 4. Mocking

Mock external dependencies to isolate the unit being tested. **Always use `with patch.object(foo, "bar"): ...` pattern**
for better refactoring support, type safety, and automatic cleanup:

```python
# Preferred - Using with patch.object() context manager
def test_send_email_with_context_manager():
    with patch.object(smtp, 'send') as mock_send:
        send_welcome_email("user@example.com")

        mock_send.assert_called_once_with(
            to="user@example.com",
            subject="Welcome!",
            body=ANY
        )


# For async methods
@pytest.mark.asyncio
async def test_async_operation():
    with patch.object(external_api, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"status": "success"}

        result = await process_data()

        assert result["processed"] == True
        mock_fetch.assert_called_once()


# Avoid - String-based patching (use only when patch.object isn't feasible)
def test_send_email_with_string_patch(mocker):
    mock_smtp = mocker.patch("email_service.smtp.send")

    send_welcome_email("user@example.com")

    mock_smtp.assert_called_once_with(
        to="user@example.com",
        subject="Welcome!",
        body=mocker.ANY
    )
```

**Benefits of `with patch.object()`:**

- Automatic cleanup when exiting the context
- Better IDE support and refactoring safety
- Clear scope of the mock
- Type checking support
- Less error-prone than string-based patching

## Async Testing

For async code, use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_user_creation():
    user = await create_user_async("John", "john@example.com")
    assert user.name == "John"
```

## Database Testing

Use transaction rollback for test isolation:

```python
@pytest.fixture
def db_session(database):
    connection = database.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

## Test Organization

### 1. Group Related Tests

```python
class TestUserAuthentication:
    def test_valid_login(self):
        pass

    def test_invalid_password(self):
        pass

    def test_locked_account(self):
        pass
```

### 2. Use Helper Functions

Extract common test logic:

```python
def create_test_order(items=None, user=None):
    if items is None:
        items = [Item("default", 10.00)]
    if user is None:
        user = UserFactory.create()
    return Order(user=user, items=items)
```

## Performance Considerations

- Keep tests fast (< 100ms per test when possible)
- Use mocks instead of real external services
- Consider marking slow tests with `@pytest.mark.slow`

## What to Test

- Public methods and functions
- Business logic and algorithms
- Data transformations
- Error handling
- Edge cases and boundaries
- Integration with external services (using mocks)

## What NOT to Test

- Private methods directly
- Third-party library internals
- Simple getters/setters
- Framework functionality
- Implementation details

## Example Test Structure

```python
import pytest
from datetime import datetime
from your_module import YourClass, YourError


@pytest.fixture
def instance(self):
    return YourClass()


def test_initialization(self):
    obj = YourClass(name="test")
    assert obj.name == "test"


def test_method_with_valid_input(self, instance):
    result = instance.process("valid")
    assert result == "expected"


def test_method_with_invalid_input(self, instance):
    with pytest.raises(YourError):
        instance.process(None)


@pytest.mark.parametrize("input_val,expected", [
    ("a", 1),
    ("b", 2),
    ("c", 3),
])
def test_mapping(self, instance, input_val, expected):
    assert instance.map_value(input_val) == expected
```
